from __future__ import annotations

import os
import sys
import pickle
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import base64

from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from data import PRODUCTS
from embedder import Embedder
from image_embedder import ImageEmbedder
from qdrant import (
    DEFAULT_COLLECTION_NAME,
    build_product_text,
    ensure_collection,
    get_collection_count,
    get_qdrant_client,
    map_qdrant_product,
    search_products,
    upsert_products,
)


load_dotenv()  # Loads .env locally for development

# Exchange rates to Tunisian Dinar (TND) - override via env: USD_TO_TND, EUR_TO_TND, GBP_TO_TND
CURRENCY_RATES_TO_TND = {
    "USD": float(os.getenv("USD_TO_TND", "3.15")),
    "$": float(os.getenv("USD_TO_TND", "3.15")),
    "EUR": float(os.getenv("EUR_TO_TND", "3.4")),
    "€": float(os.getenv("EUR_TO_TND", "3.4")),
    "GBP": float(os.getenv("GBP_TO_TND", "4.0")),
    "TND": 1.0,
    "DT": 1.0,
}


def convert_to_tnd(amount: float, currency: str | None) -> float:
    """Convert a price from source currency to Tunisian Dinars (TND)."""
    if amount is None or (isinstance(amount, (int, float)) and (amount != amount)):  # NaN
        return 0.0
    try:
        amt = float(amount)
    except (TypeError, ValueError):
        return 0.0
    if amt <= 0:
        return 0.0
    cur = (currency or "").strip().upper() or "$"
    if cur in ("$", "USD", "US"):
        cur = "USD"
    elif cur in ("€", "EUR"):
        cur = "EUR"
    elif cur in ("TND", "DT", "TD"):
        return amt
    rate = CURRENCY_RATES_TO_TND.get(cur) or CURRENCY_RATES_TO_TND.get("USD") or 3.15
    return round(amt * rate, 2)


def product_prices_to_tnd(p: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of product with price_numeric and price_display in TND (DT)."""
    out = dict(p)
    currency = (p.get("currency") or "$").strip() or "$"
    price_raw = p.get("price_numeric") if p.get("price_numeric") is not None else p.get("price")
    initial_raw = p.get("initial_price")
    try:
        price_val = float(price_raw) if price_raw is not None else 0.0
    except (TypeError, ValueError):
        price_val = 0.0
    try:
        initial_val = float(initial_raw) if initial_raw is not None else 0.0
    except (TypeError, ValueError):
        initial_val = 0.0
    price_tnd = convert_to_tnd(price_val, currency)
    initial_tnd = convert_to_tnd(initial_val, currency) if initial_val > 0 else 0.0
    out["price_numeric"] = price_tnd
    out["price_display"] = f"{price_tnd:,.2f} DT"
    out["currency"] = "DT"
    out["price"] = price_tnd
    if initial_tnd > 0:
        out["initial_price"] = initial_tnd
    return out


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging

    logger = logging.getLogger("uvicorn")
    logger.info(f"🚀 Starting up... Loading {len(PRODUCTS)} products")

    # Django: required for /api/cart and /api/cart/favorites (wishlist & cart pages)
    try:
        _setup_django_for_cart()
        _ensure_django_users_for_cart()
        logger.info("✅ Django configured (cart & favorites ready)")
    except Exception as e:
        logger.warning("⚠️ Django not loaded (cart/favorites may 500): %s", e)

    # Initialize dependencies
    collection_name = os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION_NAME)
    logger.info("📦 Loading SentenceTransformer model...")
    embedder = Embedder(model_name="all-MiniLM-L6-v2")
    
    logger.info("🔌 Connecting to Qdrant Cloud...")
    client = get_qdrant_client()

    # Ensure collection exists
    logger.info(f"📊 Ensuring collection '{collection_name}' exists...")
    # Default to 'text_dense' for text search if using named vectors
    ensure_collection(
        client=client, 
        collection_name=collection_name, 
        vector_size=embedder.vector_size,
        vector_name="text_dense"
    )

    # Check if data is already in Qdrant
    existing_count = get_collection_count(client, collection_name)
    expected_count = len(PRODUCTS)
    
    if existing_count >= expected_count:
        logger.info(
            f"✅ Collection already has {existing_count} products. "
            f"Skipping embedding and upload (fast startup!)"
        )
    else:
        logger.info(
            f"📥 Collection has {existing_count} products, need to add {expected_count - existing_count}. "
            f"Starting embedding process..."
        )
        
        # Try to load pre-computed embeddings from Kaggle
        embeddings_file = os.path.join(os.path.dirname(__file__), "product_embeddings.pkl")
        vectors = None
        products_to_upload = PRODUCTS
        
        if os.path.exists(embeddings_file):
            logger.info(f"📂 Found pre-computed embeddings file: {embeddings_file}")
            logger.info("📥 Loading embeddings from file (fast!)...")
            try:
                with open(embeddings_file, "rb") as f:
                    saved_data = pickle.load(f)
                    vectors = saved_data.get("embeddings")
                    saved_products = saved_data.get("products")
                    
                    # Verify the products match
                    if saved_products and len(saved_products) == len(PRODUCTS):
                        logger.info("✅ Using pre-computed embeddings from Kaggle!")
                        products_to_upload = saved_products
                    else:
                        logger.warning(
                            f"⚠️  Product count mismatch. Saved: {len(saved_products) if saved_products else 0}, "
                            f"Current: {len(PRODUCTS)}. Will regenerate embeddings."
                        )
                        vectors = None
            except Exception as e:
                logger.warning(f"⚠️  Failed to load embeddings file: {e}. Will generate new embeddings.")
                vectors = None
        
        # Generate embeddings if not loaded from file
        if vectors is None:
            logger.info("🔄 Building product texts...")
            texts = [build_product_text(p) for p in PRODUCTS]
            
            logger.info(
                f"🧮 Generating embeddings for {len(texts)} products "
                f"(this may take a few minutes, only done once)..."
            )
            vectors = embedder.embed_texts(texts)
        
        logger.info(f"📤 Uploading {len(products_to_upload)} products to Qdrant Cloud...")
        upsert_products(
            client=client, 
            collection_name=collection_name, 
            products=products_to_upload, 
            vectors=vectors,
            vector_name="text_dense"
        )
        logger.info("✅ Products uploaded successfully!")
    
    logger.info("✅ Startup complete! API is ready.")

    # Initialize image embedder for multimodal search
    logger.info("🖼️  Loading CLIP model for image search...")
    try:
        image_embedder = ImageEmbedder()
        image_vector_size = image_embedder.vector_size
        text_vector_size = embedder.vector_size
        
        logger.info(f"✅ CLIP model loaded. Image vector size: {image_vector_size}")
        
        # Check compatibility
        if image_vector_size != text_vector_size:
            logger.warning(
                f"⚠️  Vector size mismatch: CLIP={image_vector_size}D, Text={text_vector_size}D. "
                f"Image search may not work. Consider re-encoding products with CLIP using reload_qdrant_clip.py"
            )
        else:
            logger.info("✅ Vector sizes match! Image search is ready.")
    except Exception as e:
        logger.warning(f"⚠️  Failed to load CLIP model: {e}. Image search will be disabled.")
        image_embedder = None

    # Store in app state
    app.state.qdrant_client = client
    app.state.embedder = embedder
    app.state.image_embedder = image_embedder
    app.state.collection_name = collection_name

    yield


app = FastAPI(
    title="Smart Semantic Search API",
    version="1.0.0",
    description="Semantic (vector) search over products using Qdrant Cloud and SentenceTransformers.",
    lifespan=lifespan,
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Auth + Django: must exist before mounting cart/favorites routers (import needs Django)
DEMO_USERS = {
    "admin@finfit.com": {"password": "admin123", "name": "Admin User", "role": "super_admin", "email": "admin@finfit.com"},
    "user@finfit.com": {"password": "user123", "name": "Regular User", "role": "user", "email": "user@finfit.com"},
    "test@example.com": {"password": "test123", "name": "Test User", "role": "user", "email": "test@example.com"},
}


def _setup_django_for_cart():
    """Configure Django so /api/cart and /api/cart/favorites work when running app.py."""
    import django
    from django.conf import settings as dj_settings
    if getattr(dj_settings, "configured", False):
        return
    _parent = os.path.dirname(os.path.abspath(__file__))
    dj_settings.configure(
        DEBUG=True,
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.path.join(_parent, "rag_app.db")}},
        INSTALLED_APPS=["django.contrib.auth", "django.contrib.contenttypes", "rag_app"],
        SECRET_KEY="django-insecure-rag-app-cart-favorites",
        USE_TZ=True,
    )
    django.setup()
    try:
        from django.core.management import call_command
        call_command("migrate", "--run-syncdb", verbosity=0)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            "Django migrate failed (auth_user may be missing). Run: python run_django_migrate.py — %s", e
        )


def _ensure_django_users_for_cart():
    """Create Django User for each DEMO_USERS so cart/favorites can link."""
    from django.contrib.auth.models import User
    for u in DEMO_USERS.values():
        email = u["email"]
        if not User.objects.filter(email=email).exists():
            user = User.objects.create_user(username=email, email=email, password="demo-no-login")
            user.set_unusable_password()
            user.save()


# Mount RAG + cart/favorites API (Django must be set up first so rag_app.api.cart imports)
_rag_api_mounted = False
try:
    _root = os.path.dirname(os.path.abspath(__file__))
    if _root not in sys.path:
        sys.path.insert(0, _root)
    _setup_django_for_cart()
    _ensure_django_users_for_cart()
    from rag_app.api import routes as rag_routes
    app.include_router(rag_routes.router, prefix="/api")
    from rag_app.api import cart, recommendations, user_tracking
    app.include_router(cart.router, prefix="/api")
    app.include_router(recommendations.router, prefix="/api")
    app.include_router(user_tracking.router)
    _rag_api_mounted = True
except Exception as e:
    import logging
    logging.getLogger("uvicorn").warning("RAG API not mounted (run: uvicorn rag_app.main:app --reload for full API): %s", e)


# Fallback when RAG router is not mounted (recommendations + search)
if not _rag_api_mounted:

    @app.get("/api/recommendations/by-seed")
    def api_recommendations_by_seed_fallback(
        product_ids: str | None = Query(None),
        cart_ids: str | None = Query(None),
        wishlist_ids: str | None = Query(None),
        history_ids: str | None = Query(None),
        search_query: str | None = Query(None),
        limit: int = Query(12, ge=1, le=24),
    ):
        """Recommendations by seed; cart and wishlist weighted more for a real mix."""
        raw_ids = [x.strip() for x in (product_ids or "").split(",") if x.strip()]
        cart_set = set(x.strip() for x in (cart_ids or "").split(",") if x.strip())
        wishlist_set = set(x.strip() for x in (wishlist_ids or "").split(",") if x.strip())
        history_list = [x.strip() for x in (history_ids or "").split(",") if x.strip()]
        if not raw_ids and not (search_query and search_query.strip()):
            return {"success": True, "count": 0, "recommendations": [], "strategy": "by-seed", "message": "Provide product_ids and/or search_query"}
        client = app.state.qdrant_client
        collection_name = app.state.collection_name
        vector_name = "text_dense"

        def _pid(s: str):
            s = str(s).strip()
            if s.isdigit():
                return int(s)
            return abs(hash(s)) % (10**18)

        weighted_vectors = []
        seed_ids_set = set()
        for pid_str in raw_ids[:50]:
            try:
                pid = _pid(pid_str)
                points = client.retrieve(
                    collection_name=collection_name,
                    ids=[pid],
                    with_vectors=True,
                    with_payload=True,
                )
                if not points:
                    continue
                p = points[0]
                v = p.vector.get(vector_name) if isinstance(p.vector, dict) else p.vector
                if v:
                    w = 2.0 if pid_str in cart_set else (1.5 if pid_str in wishlist_set else 1.0)
                    weighted_vectors.append((v, w))
                    seed_ids_set.add(pid)
                    seed_ids_set.add(pid_str)
            except Exception:
                pass
        if search_query and search_query.strip():
            try:
                qv = app.state.embedder.embed_text(search_query.strip())
                weighted_vectors.append((qv, 1.5))
            except Exception:
                pass
        if not weighted_vectors:
            return {"success": True, "count": 0, "recommendations": [], "strategy": "by-seed", "message": "No vectors from seed."}
        import numpy as np
        vectors = [x[0] for x in weighted_vectors]
        weights = [x[1] for x in weighted_vectors]
        total_w = sum(weights)
        avg_vector = (np.average(vectors, axis=0, weights=weights) if total_w > 0 else np.mean(vectors, axis=0)).astype(float).tolist()
        items = search_products(
            client=client,
            collection_name=collection_name,
            query_vector=avg_vector,
            limit=limit + len(raw_ids) + 5,
            vector_name=vector_name,
        )
        seed_str = {str(x) for x in seed_ids_set}
        seen = set()
        out = []
        for r in items:
            rid = r.get("id")
            if rid is None:
                continue
            if str(rid) in seed_str or rid in seen:
                continue
            seen.add(rid)
            r["explanation"] = "Similaire à vos favoris / panier / recherche"
            r["sources"] = ["by-seed"]
            out.append(r)
            if len(out) >= limit:
                break
        return {"success": True, "count": len(out), "recommendations": [product_prices_to_tnd(x) for x in out], "strategy": "by-seed", "message": f"Found {len(out)} recommendations."}

    @app.get("/api/recommendations")
    def api_recommendations_fallback(
        user_email: str = Query(...),
        limit: int = Query(12, ge=1, le=24),
        product_ids: str | None = Query(None),
        cart_ids: str | None = Query(None),
        wishlist_ids: str | None = Query(None),
        history_ids: str | None = Query(None),
        search_query: str | None = Query(None),
    ):
        """Recommendations with query params (delegate to by-seed when product_ids provided)."""
        raw_ids = [x.strip() for x in (product_ids or "").split(",") if x.strip()]
        if raw_ids or (search_query and search_query.strip()):
            return api_recommendations_by_seed_fallback(
                product_ids=product_ids, cart_ids=cart_ids, wishlist_ids=wishlist_ids,
                history_ids=history_ids, search_query=search_query, limit=limit,
            )
        return {"success": True, "count": 0, "recommendations": [], "strategy": "none", "message": "Add product_ids or search_query."}

    class ApiSearchRequest(BaseModel):
        user_query: str | None = None
        image_base64: str | None = None
        limit: int = 15

    @app.post("/api/search")
    def api_search_fallback(request: ApiSearchRequest):
        """Semantic search - text and/or image. Same format as home page (answer, products, results, count)."""
        query = (request.user_query or "").strip()
        image_b64 = (request.image_base64 or "").strip() or None
        if not query and not image_b64:
            return {
                "answer": "Enter a search query or upload a photo.",
                "products": [],
                "results": [],
                "count": 0,
            }
        limit = max(1, min(100, request.limit or 50))
        client = app.state.qdrant_client
        collection_name = app.state.collection_name
        query_vector = None
        vector_name = "text_dense"
        image_embedder = getattr(app.state, "image_embedder", None)

        # Multimodal: combine image + text when both provided (same CLIP space)
        vectors_to_avg = []
        if image_b64 and image_embedder:
            try:
                import base64
                import numpy as np
                img_data = image_b64
                if "," in img_data:
                    img_data = img_data.split(",", 1)[1]
                image_bytes = base64.b64decode(img_data)
                img_vec = image_embedder.embed_image_from_bytes(image_bytes)
                vectors_to_avg.append(np.array(img_vec))
            except Exception as e:
                if not query:
                    return {
                        "answer": f"Image search failed: {e}. Try a text search.",
                        "products": [],
                        "results": [],
                        "count": 0,
                    }
        if query and image_embedder:
            try:
                import numpy as np
                text_vec = image_embedder.embed_text(query)
                vectors_to_avg.append(np.array(text_vec))
            except Exception:
                pass
        if vectors_to_avg:
            import numpy as np
            if len(vectors_to_avg) > 1:
                query_vector = np.mean(vectors_to_avg, axis=0)
                query_vector = (query_vector / np.linalg.norm(query_vector)).tolist()
            else:
                query_vector = vectors_to_avg[0].tolist()
            vector_name = "image_dense"
        if query_vector is None and query:
            embedder: Embedder = app.state.embedder
            query_vector = embedder.embed_text(query)
            vector_name = "text_dense"

        if query_vector is None:
            return {"answer": "No valid query.", "products": [], "results": [], "count": 0}

        try:
            items = search_products(
                client=client,
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=0.25,
                use_mmr=False,
                vector_name=vector_name,
            )
        except Exception as e:
            if vector_name == "image_dense" and query:
                query_vector = app.state.embedder.embed_text(query)
                items = search_products(
                    client=client,
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=0.25,
                    use_mmr=False,
                    vector_name="text_dense",
                )
            else:
                return {
                    "answer": f"Search failed: {e}. Try text search.",
                    "products": [],
                    "results": [],
                    "count": 0,
                }
        items_tnd = [product_prices_to_tnd(it) for it in items]
        return {
            "answer": f"Found {len(items_tnd)} product(s).",
            "products": items_tnd,
            "results": items_tnd,
            "count": len(items_tnd),
        }

    @app.get("/api/product-details")
    def api_product_details_fallback(id: str | None = Query(None), asin: str | None = Query(None)):
        """Get one product by id or asin when RAG router is not mounted. Same shape as rag_app product-details."""
        if not id and not asin:
            return {"ok": False, "product": {}}
        client = app.state.qdrant_client
        collection_name = app.state.collection_name
        offset = None
        while True:
            results, next_offset = client.scroll(
                collection_name=collection_name,
                offset=offset,
                limit=256,
                with_payload=True,
                with_vectors=False,
            )
            for point in results:
                payload = point.payload or {}
                if id is not None and str(payload.get("id") or payload.get("row_id") or point.id) == str(id):
                    product = map_qdrant_product(point)
                    return {"ok": True, "product": product_prices_to_tnd(product)}
                if asin is not None and payload.get("asin") == asin:
                    product = map_qdrant_product(point)
                    return {"ok": True, "product": product_prices_to_tnd(product)}
            if next_offset is None:
                break
            offset = next_offset
        return {"ok": False, "product": {}}

    def _find_point_with_vector(client, collection_name: str, *, id: str | None, asin: str | None):
        """Scroll to find a point by payload id or asin; return it with vectors for similarity search."""
        offset = None
        while True:
            batch, next_offset = client.scroll(
                collection_name=collection_name,
                offset=offset,
                limit=256,
                with_payload=True,
                with_vectors=True,
            )
            for point in batch:
                payload = point.payload or {}
                if id is not None and str(payload.get("id") or payload.get("row_id") or point.id) == str(id):
                    return point
                if asin is not None and payload.get("asin") == asin:
                    return point
            if next_offset is None:
                return None
            offset = next_offset

    @app.get("/api/similar-products")
    def api_similar_products_fallback(
        id: str | None = Query(None),
        asin: str | None = Query(None),
        limit: int = Query(5, ge=1, le=20),
    ):
        """Return products most similar to the given product (vector search). Same shape as rag_app similar-products."""
        client = app.state.qdrant_client
        collection_name = app.state.collection_name
        if not id and not asin:
            return {"ok": True, "results": []}
        target_point = _find_point_with_vector(client, collection_name, id=id, asin=asin)
        if not target_point:
            return {"ok": True, "results": []}
        target_id = target_point.id
        target_payload_id = str((target_point.payload or {}).get("id") or (target_point.payload or {}).get("row_id") or target_id)
        vector = None
        if target_point.vector:
            if isinstance(target_point.vector, dict):
                vector = target_point.vector.get("text_dense")
            elif isinstance(target_point.vector, (list, tuple)):
                vector = list(target_point.vector)
        if vector and len(vector) > 0:
            try:
                similar = client.query_points(
                    collection_name=collection_name,
                    query=vector,
                    using="text_dense",
                    limit=limit + 1,
                    with_payload=True,
                )
                results = []
                for point in (similar.points if hasattr(similar, "points") else similar):
                    pid = str((point.payload or {}).get("id") or (point.payload or {}).get("row_id") or point.id)
                    if pid == target_payload_id or (target_id is not None and point.id == target_id):
                        continue
                    product = map_qdrant_product(point)
                    results.append(product_prices_to_tnd(product))
                    if len(results) >= limit:
                        break
                return {"ok": True, "results": results[:limit]}
            except Exception:
                pass
        results = []
        offset = None
        exclude_id = str(id) if id else None
        while True:
            batch, next_offset = client.scroll(
                collection_name=collection_name,
                offset=offset,
                limit=256,
                with_payload=True,
                with_vectors=False,
            )
            for point in batch:
                payload = point.payload or {}
                pid = str(payload.get("id") or payload.get("row_id") or point.id)
                if exclude_id and pid == exclude_id:
                    continue
                if asin and payload.get("asin") == asin:
                    continue
                product = map_qdrant_product(point)
                results.append(product_prices_to_tnd(product))
                if len(results) >= limit:
                    break
            if len(results) >= limit or next_offset is None:
                break
            offset = next_offset
        return {"ok": True, "results": results[:limit]}

    @app.get("/api/discounted-products")
    def api_discounted_products_fallback(
        min_discount: float = Query(30, ge=0),
        limit: int = Query(10, ge=1, le=50),
    ):
        """Return products with discount >= min_discount when RAG router is not mounted."""
        import re
        client = app.state.qdrant_client
        collection_name = app.state.collection_name
        results = []
        offset = None
        while True:
            batch, next_offset = client.scroll(
                collection_name=collection_name,
                offset=offset,
                limit=256,
                with_payload=True,
                with_vectors=False,
            )
            for point in batch:
                payload = point.payload or {}
                disc_raw = payload.get("discount")
                disc_num = None
                if disc_raw is not None:
                    if isinstance(disc_raw, (int, float)):
                        disc_num = abs(float(disc_raw))
                    else:
                        m = re.search(r"-?(\d+(?:\.\d+)?)\s*%?", str(disc_raw))
                        if m:
                            disc_num = abs(float(m.group(1)))
                if disc_num is None or disc_num < min_discount:
                    continue
                product = map_qdrant_product(point)
                product["discount"] = disc_num
                results.append(product_prices_to_tnd(product))
                if len(results) >= limit:
                    break
            if len(results) >= limit or next_offset is None:
                break
            offset = next_offset
        return {"ok": True, "results": results[:limit]}

    class ShortenTitlesRequest(BaseModel):
        titles: List[str] = []
        max_chars: int = 35

    @app.post("/api/shorten-titles")
    def api_shorten_titles_fallback(request: ShortenTitlesRequest):
        """Truncate titles when RAG router is not mounted. Same shape as rag_app shorten-titles."""
        max_c = max(1, min(200, request.max_chars or 35))
        short = []
        for t in request.titles or []:
            s = (t or "").strip()
            if len(s) <= max_c:
                short.append(s)
            else:
                short.append(s[: max_c - 1] + "…" if max_c > 1 else s[:max_c])
        return {"ok": True, "short_titles": short}

    class ChatRequest(BaseModel):
        message: str = ""
        image_base64: str | None = None
        currency: str | None = None

    @app.post("/api/chat")
    def api_chat_fallback(request: ChatRequest):
        """Chat when RAG router is not mounted: same shape as RAG (answer, products) using semantic search."""
        msg = (request.message or "").strip()
        image_b64 = (request.image_base64 or "").strip() or None
        if not msg and not image_b64:
            return {
                "answer": "Please type a question about our products or upload a photo.",
                "products": [],
                "results": [],
                "count": 0,
            }
        # Reuse search fallback logic so chat returns real product results
        search_req = ApiSearchRequest(user_query=msg or None, image_base64=image_b64, limit=15)
        result = api_search_fallback(search_req)
        # Ensure RAG-compatible keys (answer, products, results, count)
        return {
            "answer": result.get("answer", "I found some products for you."),
            "products": result.get("products", []),
            "results": result.get("results", result.get("products", [])),
            "count": result.get("count", 0),
        }


class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str | None = None
    phone: str | None = None

def _get_django_user_by_email(email: str):
    """Return Django User by email if exists (for login/register)."""
    try:
        _setup_django_for_cart()
        from django.contrib.auth.models import User
        u = User.objects.filter(email=email.strip()).first()
        if u:
            return u
        u = User.objects.filter(username=email.strip()).first()
        return u
    except Exception:
        return None

@app.post("/api/login")
def api_login(request: LoginRequest):
    """Login: demo users first, then users from database (Django)."""
    import hashlib
    user = DEMO_USERS.get(request.email)
    if user and user["password"] == request.password:
        token = hashlib.sha256(f"{request.email}{user['role']}".encode()).hexdigest()[:32]
        return {
            "success": True,
            "message": "Login successful",
            "access_token": token,
            "token_type": "bearer",
            "user": {"email": user["email"], "name": user["name"], "role": user["role"]},
        }
    django_user = _get_django_user_by_email(request.email)
    if django_user and django_user.check_password(request.password):
        if not getattr(django_user, "is_active", True):
            raise HTTPException(status_code=403, detail="Account disabled")
        token = hashlib.sha256(f"{request.email}user".encode()).hexdigest()[:32]
        name = (django_user.first_name or django_user.email or request.email).strip() or request.email
        return {
            "success": True,
            "message": "Login successful",
            "access_token": token,
            "token_type": "bearer",
            "user": {"email": django_user.email, "name": name, "role": "user"},
        }
    raise HTTPException(status_code=401, detail="Invalid email or password")

@app.post("/api/register")
def api_register(request: RegisterRequest):
    """Register new user and save to database (Django)."""
    email = (request.email or "").strip()
    password = request.password or ""
    name = (request.name or email or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    try:
        _setup_django_for_cart()
        from django.contrib.auth.models import User
        if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
            raise HTTPException(status_code=400, detail="Email already registered")
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name or email,
        )
        user.save()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    import hashlib
    token = hashlib.sha256(f"{email}user".encode()).hexdigest()[:32]
    return {
        "success": True,
        "message": "Account created successfully",
        "access_token": token,
        "token_type": "bearer",
        "user": {"email": email, "name": name or email, "role": "user"},
    }

@app.get("/", response_class=HTMLResponse)
def home():
    """Redirect to search interface"""
    return FileResponse("static/index.html")


@app.get("/status/image-search")
def image_search_status():
    """Check if image search is available (CLIP model loaded and vectors compatible)"""
    if not app.state.image_embedder:
        return {
            "available": False,
            "reason": "CLIP model not loaded",
            "solution": "Restart the server to load CLIP model"
        }
    
    # Check vector size compatibility
    client = app.state.qdrant_client
    collection_name = app.state.collection_name
    
    try:
        collection_info = client.get_collection(collection_name)
        vectors_config = collection_info.config.params.vectors
        
        # Handle both named vectors (dict) and single vector configurations
        if isinstance(vectors_config, dict):
            # Try to get the specific vector size from 'image_dense' or fall back
            sample_vector = vectors_config.get("image_dense") or vectors_config.get("text_dense") or list(vectors_config.values())[0]
            collection_vector_size = sample_vector.size
        else:
            collection_vector_size = vectors_config.size
            
        image_vector_size = app.state.image_embedder.vector_size
        
        if image_vector_size != collection_vector_size:
            return {
                "available": False,
                "reason": f"Vector size mismatch: CLIP={image_vector_size}D, Collection={collection_vector_size}D",
                "solution": "Run: python reload_qdrant_clip.py",
                "image_vector_size": image_vector_size,
                "collection_vector_size": collection_vector_size
            }
        
        return {
            "available": True,
            "image_vector_size": image_vector_size,
            "collection_vector_size": collection_vector_size
        }
    except Exception as e:
        return {
            "available": False,
            "reason": str(e),
            "solution": "Check Qdrant connection"
        }


@app.get("/products")
def list_products(
    limit: int = Query(12, ge=1, le=100, description="Number of products per page"),
    category: str = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    min_price: float = Query(None, description="Minimum price (TND)"),
    max_price: float = Query(None, description="Maximum price (TND)"),
    sort: str = Query(None, description="Sort: price_asc | price_desc"),
):
    """Get products from Qdrant with pagination and filters. Returns shape expected by shop.html."""
    client = app.state.qdrant_client
    collection_name = app.state.collection_name

    def _normalize_product(p: Dict[str, Any]) -> Dict[str, Any]:
        """Convert prices to TND and ensure price_numeric, discount_percent, price_display (DT)."""
        out = product_prices_to_tnd(p)
        price_num = out.get("price_numeric")
        if price_num is not None:
            try:
                n = float(price_num)
                out["price_display"] = f"{n:,.2f} DT"
            except (TypeError, ValueError):
                out["price_display"] = str(out.get("price", "")) or "— DT"
        else:
            out["price_display"] = str(out.get("price", "")) or "— DT"
        discount_raw = out.get("discount")
        initial = out.get("initial_price")
        price_val = out.get("price_numeric") or out.get("price")
        try:
            price_f = float(price_val) if price_val is not None else 0.0
        except (TypeError, ValueError):
            price_f = 0.0
        discount_percent = None
        if discount_raw is not None and str(discount_raw).strip():
            import re
            m = re.search(r"(\d+)", str(discount_raw))
            if m:
                discount_percent = int(m.group(1))
        if discount_percent is None and initial is not None:
            try:
                init_f = float(initial)
                if init_f > 0 and price_f < init_f:
                    discount_percent = min(99, round((init_f - price_f) / init_f * 100))
            except (TypeError, ValueError):
                pass
        out["discount_percent"] = discount_percent if discount_percent is not None else 0
        return out

    try:
        from qdrant import map_qdrant_product

        scroll_limit = 3000
        offset = None
        all_results = []
        while True:
            results, next_offset = client.scroll(
                collection_name=collection_name,
                limit=min(1000, scroll_limit - len(all_results)),
                offset=offset,
                with_payload=True,
            )
            if not results:
                break
            all_results.extend(results)
            if next_offset is None or len(all_results) >= scroll_limit:
                break
            offset = next_offset

        products = [_normalize_product(map_qdrant_product(p)) for p in all_results]

        category_lower = (category or "").strip().lower()
        if category_lower and category_lower not in ("all", "all types", "all products"):
            products = [
                p for p in products
                if category_lower in (p.get("category") or "").lower()
                or (p.get("category") or "").lower() == category_lower
            ]

        price_num = lambda p: p.get("price_numeric") is None and 0.0 or (p.get("price_numeric") or 0.0)
        if min_price is not None:
            products = [p for p in products if price_num(p) >= min_price]
        if max_price is not None:
            products = [p for p in products if price_num(p) <= max_price]

        if sort == "price_asc":
            products = sorted(products, key=lambda p: (price_num(p) is None, price_num(p) or 0))
        elif sort == "price_desc":
            products = sorted(products, key=lambda p: (price_num(p) is None, -(price_num(p) or 0)))

        total_products = len(products)
        total_pages = max(1, (total_products + limit - 1) // limit)
        page = max(1, min(page, total_pages))
        start = (page - 1) * limit
        page_products = products[start : start + limit]

        return {
            "success": True,
            "products": page_products,
            "current_page": page,
            "total_pages": total_pages,
            "total_products": total_products,
        }
    except Exception as e:
        # Fallback to CSV data if Qdrant fails
        filtered = list(PRODUCTS)
        if category and (category or "").strip().lower() not in ("all", "all types", "all products"):
            cat_lower = (category or "").lower()
            filtered = [p for p in filtered if cat_lower in (p.get("category") or "").lower()]
        total = len(filtered)
        total_pages = max(1, (total + limit - 1) // limit)
        page = max(1, min(page, total_pages))
        start = (page - 1) * limit
        page_products = [_normalize_product(dict(p)) for p in filtered[start : start + limit]]
        return {
            "success": True,
            "products": page_products,
            "current_page": page,
            "total_pages": total_pages,
            "total_products": total,
        }


@app.get("/products/price-range")
def get_products_price_range():
    """Return min and max price from Qdrant products (for price filter in shop)."""
    client = app.state.qdrant_client
    collection_name = app.state.collection_name
    try:
        from qdrant import map_qdrant_product
        min_p, max_p = None, None
        offset = None
        for _ in range(20):
            results, next_offset = client.scroll(
                collection_name=collection_name,
                limit=500,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not results:
                break
            for point in results:
                product = map_qdrant_product(point)
                try:
                    price = product.get("price_numeric")
                    if price is None:
                        price = float(product.get("price") or 0)
                except (TypeError, ValueError):
                    continue
                if price is not None and price >= 0:
                    price_tnd = convert_to_tnd(price, product.get("currency"))
                    min_p = min(min_p, price_tnd) if min_p is not None else price_tnd
                    max_p = max(max_p, price_tnd) if max_p is not None else price_tnd
            if next_offset is None:
                break
            offset = next_offset
        min_price = float(min_p) if min_p is not None else 0.0
        max_price = float(max_p) if max_p is not None else 2000.0
        if max_price <= min_price:
            max_price = min_price + 100
        return {"success": True, "min_price": min_price, "max_price": max_price}
    except Exception as e:
        return {"success": False, "min_price": 0.0, "max_price": 2000.0}


@app.get("/products/facets")
def get_products_facets():
    """Return unique categories from Qdrant (for scrollable PRODUCT TYPE filter)."""
    client = app.state.qdrant_client
    collection_name = app.state.collection_name
    try:
        from qdrant import map_qdrant_product
        category_counts: Dict[str, int] = {}
        offset = None
        for _ in range(30):
            results, next_offset = client.scroll(
                collection_name=collection_name,
                limit=500,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not results:
                break
            for point in results:
                product = map_qdrant_product(point)
                cat = (product.get("category") or "").strip()
                if cat and cat.lower() not in ("n/a", ""):
                    category_counts[cat] = category_counts.get(cat, 0) + 1
            if next_offset is None:
                break
            offset = next_offset
        categories_sorted = sorted(
            category_counts.keys(),
            key=lambda k: (-category_counts[k], k.lower()),
        )[:80]
        return {"success": True, "categories": categories_sorted}
    except Exception as e:
        filtered = []
        try:
            for p in PRODUCTS:
                c = (p.get("category") or "").strip()
                if c and c.lower() not in ("", "n/a"):
                    filtered.append(c)
            categories_sorted = sorted(set(filtered))[:80]
        except Exception:
            categories_sorted = []
        return {"success": True, "categories": categories_sorted}


@app.get("/search")
def search(
    q: str = Query(..., min_length=1, description="Natural language query"),
    limit: int = Query(30, ge=1, le=50, description="Number of results"),
    threshold: float = Query(0.3, ge=0.0, le=1.0, description="Minimum similarity score (0.0-1.0)"),
    mmr: bool = Query(False, description="Enable MMR for diverse results"),
):
    """
    Semantic search with optional MMR (Maximal Marginal Relevance).
    
    - **q**: Search query in any language
    - **limit**: Max number of results (1-20)
    - **threshold**: Minimum similarity score (e.g., 0.5 = 50% match)
    - **mmr**: Enable diversity mode (reduces similar results)
    
    Examples:
    - `/search?q=headphones` - Basic search
    - `/search?q=headphones&threshold=0.5` - Only results > 50% match
    - `/search?q=headphones&limit=10&threshold=0.6` - Top 10, min 60%
    - `/search?q=headphones&mmr=true` - Diverse results
    """
    embedder: Embedder = app.state.embedder
    client = app.state.qdrant_client
    
    # Use the unified collection for both text and image
    # containing 'text_dense' and 'image_dense' vectors
    collection_name = app.state.collection_name
    
    query_vector = embedder.embed_text(q)
    
    items = search_products(
        client=client,
        collection_name=collection_name,
        query_vector=query_vector,
        limit=limit,
        score_threshold=threshold,
        use_mmr=mmr,
        vector_name="text_dense", # Use explicit text vector
    )
    items_tnd = [product_prices_to_tnd(it) for it in items]
    return {
        "query": q,
        "results": items_tnd,
        "mmr_enabled": mmr,
        "threshold": threshold,
        "count": len(items_tnd),
    }


class ImageSearchRequest(BaseModel):
    """Request model for image search using base64."""
    image_base64: str  # Base64 encoded image
    limit: int = 30
    threshold: float = 0.3
    mmr: bool = False


@app.post("/search/image")
async def search_by_image(request: ImageSearchRequest):
    """
    Multimodal search: find products similar to an uploaded image.
    Uses 'nexus-multivector_3k_f' collection with 'image_dense' vector.
    """
    if not app.state.image_embedder:
        raise HTTPException(
            status_code=503,
            detail="Image search not available. CLIP model not loaded. Check server logs."
        )
    
    # Decode base64 image
    try:
        # Remove data URL prefix if present
        image_data = request.image_base64
        if "," in image_data:
            image_data = image_data.split(",")[1]
        image_bytes = base64.b64decode(image_data)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to decode image: {str(e)}"
        )
    
    # Encode image with CLIP
    image_embedder: ImageEmbedder = app.state.image_embedder
    try:
        query_vector = image_embedder.embed_image_from_bytes(image_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process image: {str(e)}"
        )
    
    client = app.state.qdrant_client
    # Use the unified collection
    collection_name = app.state.collection_name
    
    # Check vector size compatibility (optional log, but good for debug)
    # image_vector_size = len(query_vector) # Should be 512
    
    # Search with image vector in the unified collection
    items = search_products(
        client=client,
        collection_name=collection_name,
        query_vector=query_vector,
        limit=request.limit,
        score_threshold=request.threshold,
        use_mmr=request.mmr,
        vector_name="image_dense", # Use 'image_dense' vector for image search
    )
    
    items_tnd = [product_prices_to_tnd(it) for it in items]
    return {
        "query": "Image search",
        "results": items_tnd,
        "mmr_enabled": request.mmr,
        "threshold": request.threshold,
        "count": len(items_tnd),
        "search_type": "image",
    }


@app.get("/{path:path}", response_class=HTMLResponse)
def serve_html_pages(path: str):
    """
    Serve HTML pages from static/ so /signin.html, /shop.html, /cart.html, etc. work.
    Avoids {"detail": "Not Found"} when opening these URLs directly.
    """
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    base = os.path.dirname(os.path.abspath(__file__))
    # Try exact path under static/
    file_path = os.path.join(base, "static", path)
    if os.path.isfile(file_path):
        return FileResponse(file_path, media_type="text/html" if path.endswith(".html") else None)
    # Try adding .html
    if not path.endswith(".html"):
        file_path_html = os.path.join(base, "static", path + ".html")
        if os.path.isfile(file_path_html):
            return FileResponse(file_path_html, media_type="text/html")
    raise HTTPException(status_code=404, detail="Not Found")
