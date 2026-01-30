from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import re
import sys
import os
import json
from pydantic import BaseModel

# Add current directory to path to allow relative imports
sys.path.insert(0, os.path.dirname(__file__))

from core.config import settings
from core.database import get_qdrant_client, ensure_collection
from core.llm import groq_client
from core.currency import convert_to_tnd, format_price_tnd
from api import routes

logger = logging.getLogger("uvicorn")

# --- AUTH SCHEMAS ---
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = None

class LoginRequest(BaseModel):
    email: str
    password: str

def _setup_django():
    """Configure and initialize Django so Cart/Favorites models and DB exist."""
    import django
    from django.conf import settings as dj_settings
    if dj_settings.configured:
        return
    _root = os.path.dirname(os.path.abspath(__file__))
    _parent = os.path.dirname(_root)
    dj_settings.configure(
        DEBUG=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": os.path.join(_parent, "rag_app.db"),
            }
        },
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "rag_app",
        ],
        SECRET_KEY="django-insecure-rag-app-cart-favorites",
        USE_TZ=True,
    )
    django.setup()
    # Create tables if they don't exist (migrate rag_app)
    try:
        from django.core.management import call_command
        call_command("migrate", "--run-syncdb", verbosity=0)
    except Exception as e:
        logger.warning("Django migrate skipped: %s", e)


def _ensure_django_users():
    """Create Django User for each DEMO_USERS so cart/favorites can link to user."""
    from core.auth import DEMO_USERS
    from django.contrib.auth.models import User
    for u in DEMO_USERS.values():
        email = u["email"]
        if not User.objects.filter(email=email).exists():
            user = User.objects.create_user(
                username=email,
                email=email,
                password="demo-no-login",  # unused; auth is via token
            )
            user.set_unusable_password()
            user.save()
            logger.info("Created Django user for %s", email)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize and verify connections
    logger.info("🚀 Starting RAG Application...")
    
    # Django: required for Cart and Favorites (user-linked)
    try:
        _setup_django()
        _ensure_django_users()
        logger.info("✅ Django configured (cart & favorites linked to user)")
    except Exception as e:
        logger.warning("⚠️ Django not loaded (cart/favorites will 500): %s", e)
    
    # Verify Qdrant connection
    try:
        client = get_qdrant_client()
        ensure_collection(vector_size=384)
        logger.info("✅ Qdrant connection verified")
    except Exception as e:
        logger.error(f"⚠️ Warning: Qdrant connection failed. Limited functionality: {str(e)}")
    
    # Verify Groq API key
    if not settings.GROQ_API_KEY or groq_client is None:
        logger.error("⚠️ Warning: Groq API not configured. LLM features will not work.")
    else:
        logger.info("✅ Groq API configured")
    
    logger.info("🎯 RAG Application ready!")
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files FIRST (before all routes) - CSS, JS, images, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routes with /api prefix
app.include_router(routes.router, prefix="/api")
# Cart, recommendations, and user tracking (avoid "detail": "Not Found" on all pages)
try:
    from api import cart, recommendations, user_tracking
    app.include_router(cart.router, prefix="/api")
    app.include_router(recommendations.router, prefix="/api")
    app.include_router(user_tracking.router)  # already has prefix /api/track
except Exception as e:
    logger.warning(f"Optional API routers (cart, recommendations, tracking) not loaded: {e}")

# Legacy search endpoints (for backward compatibility with frontend)
@app.post("/search")
async def legacy_search(user_query: str, limit: int = 12):
    """Legacy search endpoint that forwards to /api/search"""
    from api.routes import SearchRequest
    request = SearchRequest(user_query=user_query, limit=limit)
    return await routes.production_search(request)

@app.get("/search")
async def legacy_search_get(q: str, limit: int = 12):
    """Legacy GET search endpoint"""
    from api.routes import SearchRequest
    request = SearchRequest(user_query=q, limit=limit)
    return await routes.production_search(request)

@app.post("/search/image")
async def legacy_search_image(request: routes.SearchRequest):
    """Legacy image search endpoint that forwards to /api/search/image"""
    return await routes.production_search(request)

@app.get("/status/image-search")
async def image_search_status():
    """Check status of image search service"""
    return {
        "status": "unavailable",
        "message": "Image search service is not available",
        "available": False
    }

# Auth: use shared DEMO_USERS and token from core.auth (cart/favorites use same token)
from core.auth import DEMO_USERS, make_token

@app.post("/api/register")
async def register(request: RegisterRequest):
    """User registration endpoint"""
    return {
        "success": True,
        "message": "Registration feature coming soon",
        "token": "dummy_token_123",
        "user": {"email": request.email, "name": request.name}
    }

@app.post("/api/login")
async def login(request: LoginRequest):
    """
    User login endpoint with role-based access.
    Token is used by cart and favorites APIs (user must be connected).
    Demo: admin@finfit.com / admin123, user@finfit.com / user123, test@example.com / test123
    """
    user = DEMO_USERS.get(request.email)
    if not user or user["password"] != request.password:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    token = make_token(request.email, user["role"])
    return {
        "success": True,
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "name": user["name"],
            "role": user["role"]
        }
    }

# Health check endpoint
@app.get("/health")
def health_check():
    """
    Health check endpoint to verify service connectivity.
    Returns the status of Qdrant and Groq connections.
    """
    status = {
        "status": "healthy",
        "qdrant": "unknown",
        "groq": "unknown",
    }
    
    # Check Qdrant
    try:
        client = get_qdrant_client()
        client.get_collections()
        status["qdrant"] = "connected"
    except Exception as e:
        status["qdrant"] = f"disconnected: {str(e)}"
        status["status"] = "degraded"
    
    # Check Groq
    if groq_client is not None:
        status["groq"] = "configured"
    else:
        status["groq"] = "not configured"
        status["status"] = "degraded"
    
    status_code = 200 if status["status"] == "healthy" else 503
    return JSONResponse(content=status, status_code=status_code)

@app.get("/api/users")
async def get_users():
    """Get all registered users (excluding passwords)"""
    return {
        "success": True,
        "users": [
            {
                "email": user["email"],
                "name": user["name"],
                "role": user["role"]
            }
            for user in DEMO_USERS.values()
        ]
    }

@app.get("/api/dashboard/widgets")
async def get_dashboard_widgets():
    """Get data for dashboard widgets: top products and user stats"""
    try:
        # 1. User stats
        user_counts = {"user": 0, "super_admin": 0, "admin": 0}
        for user in DEMO_USERS.values():
            role = user.get("role", "user")
            user_counts[role] = user_counts.get(role, 0) + 1
        
        # 2. Top Products (by rating)
        client = get_qdrant_client()
        collection_name = settings.COLLECTION_NAME
        
        # Scroll a larger sample to find best rated (Qdrant doesn't support complex sort on payload as easily as SQL)
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=50,
            with_payload=True,
            with_vectors=False
        )
        
        all_products = []
        for point in points:
            payload = point.payload
            
            # Extract and convert price (reusing logic from get_products)
            raw_price = payload.get("price") or payload.get("final_price") or 0
            raw_currency = payload.get("currency", "USD")
            
            try:
                price_float = float(str(raw_price).replace(",", "")) if raw_price else 0
            except (ValueError, TypeError):
                price_float = 0
                
            # Convert to TND
            price_tnd_str = "N/A"
            if price_float > 0:
                try:
                    # Basic detection logic matches get_products
                    if "IDR" in str(raw_currency).upper() or price_float > 1000:
                        price_tnd = convert_to_tnd(price_float, "IDR")
                    elif "TND" in str(raw_currency).upper() or "DT" in str(raw_currency).upper():
                        price_tnd = price_float
                    else:
                        price_tnd = convert_to_tnd(price_float, "USD")
                    
                    price_tnd_str = f"{price_tnd:,.2f} DT"
                except:
                    price_tnd_str = f"{raw_price} {raw_currency}"

            all_products.append({
                "id": str(point.id),
                "name": payload.get("name") or payload.get("title") or "Unknown Product",
                "rating": float(payload.get("rating") or 0),
                "price": price_tnd_str,
                "image": payload.get("image_url") or payload.get("image") or "/static/img/placeholder.png",
                "category": payload.get("category", "General")
            })
        
        # Sort by rating and take top 5
        top_products = sorted(all_products, key=lambda x: x["rating"], reverse=True)[:5]
        
        return {
            "success": True,
            "user_stats": {
                "super_users": user_counts.get("super_admin", 0),
                "admins": user_counts.get("admin", 0),
                "regular_users": user_counts.get("user", 0),
                "total_users": sum(user_counts.values())
            },
            "top_products": top_products
        }
    except Exception as e:
        logger.error(f"Widget data error: {str(e)}")
        return {"success": False, "error": str(e)}


def _point_to_product(point) -> dict:
    """Build product dict from a Qdrant point (payload + id)."""
    payload = point.payload
    category_value = _extract_category(payload)
    raw_price = payload.get("price") or payload.get("final_price") or "N/A"
    raw_currency = payload.get("currency", "")
    try:
        price_float = float(str(raw_price).replace(",", "")) if raw_price != "N/A" else 0
    except (ValueError, TypeError):
        price_float = 0
    currency = "USD"
    if raw_currency:
        raw_currency = str(raw_currency).upper().strip()
        if "IDR" in raw_currency or "Rp" in raw_currency:
            currency = "IDR"
        elif "DT" in raw_currency or "TND" in raw_currency:
            currency = "TND"
        elif "$" in raw_currency or "USD" in raw_currency:
            currency = "USD"
    else:
        currency = "IDR" if price_float > 1000 else "USD"
    if currency == "TND":
        price_tnd = price_float
        price_tnd_str = f"{price_float:,.2f} DT"
    else:
        try:
            price_tnd = convert_to_tnd(price_float, currency)
            price_tnd_str = f"{price_tnd:,.2f} DT"
        except (ValueError, TypeError):
            price_tnd = None
            price_tnd_str = f"{raw_price} {currency}"
    initial_price_raw = payload.get("initial_price") or payload.get("original_price") or payload.get("listedPrice") or ""
    try:
        initial_price_float = float(str(initial_price_raw).replace(",", "").replace("$", "").strip()) if initial_price_raw else 0
    except (ValueError, TypeError):
        initial_price_float = 0
    discount_raw = payload.get("discount")
    discount_percent = None
    if discount_raw:
        m = re.search(r"(\d+)", str(discount_raw))
        if m:
            discount_percent = int(m.group(1))
    elif initial_price_float and price_tnd and initial_price_float > (price_tnd or 0):
        discount_percent = min(99, int(round((1 - (price_tnd or 0) / initial_price_float) * 100)))

    return {
        "id": str(point.id) if point.id is not None else None,
        "title": payload.get("name") or payload.get("title") or "Unknown Product",
        "name": payload.get("name") or payload.get("title") or "Unknown Product",
        "price": price_tnd_str,
        "price_original": f"{raw_price} {currency}",
        "price_numeric": price_tnd,
        "currency": "TND",
        "image": payload.get("image_url") or payload.get("image") or "/static/img/placeholder.png",
        "availability": payload.get("availability", "In Stock"),
        "category": category_value,
        "description": (payload.get("description") or "")[:500] or "",
        "topreview": (payload.get("topreview") or payload.get("top_review") or "").strip() or "",
        "rating": payload.get("rating") or 4.5,
        "url": payload.get("url") or payload.get("product_url") or "#",
        "discount": discount_raw,
        "discount_percent": discount_percent,
        "initial_price": initial_price_float if initial_price_float else None,
        "color": (payload.get("color") or "").strip() or None,
    }


def _extract_category(payload: dict) -> str:
    """Extract a meaningful category from Qdrant payload."""
    def _clean(s: str) -> str:
        s = (s or "").strip()
        if not s:
            return ""
        low = s.lower()
        if low in ("uncategorized", "unknown", "n/a", "none", "null"):
            return ""
        return s

    cat = _clean(str(payload.get("category") or ""))
    if cat:
        return cat

    cats = payload.get("categories")
    if isinstance(cats, list):
        for v in reversed(cats):
            c = _clean(str(v))
            if c:
                return c
    elif isinstance(cats, str) and cats.strip():
        raw = cats.strip()
        parsed = None
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = None
        if isinstance(parsed, list):
            for v in reversed(parsed):
                c = _clean(str(v))
                if c:
                    return c
        parts = [p.strip().strip("'\"[]") for p in raw.split(",")]
        for v in reversed(parts):
            c = _clean(v)
            if c:
                return c

    node_name = _clean(str(payload.get("nodeName") or ""))
    if node_name:
        return node_name
    return "General"


@app.get("/product/{product_id}")
def get_product(product_id: str):
    """Get a single product by ID from Qdrant (for single product page)."""
    try:
        client = get_qdrant_client()
        collection_name = settings.COLLECTION_NAME
        point_id = product_id if isinstance(product_id, str) and product_id.isdigit() else product_id
        try:
            point_id = int(point_id)
        except (ValueError, TypeError):
            pass
        records = client.retrieve(
            collection_name=collection_name,
            ids=[point_id],
            with_payload=True,
            with_vectors=False,
        )
        if not records:
            raise HTTPException(status_code=404, detail="Product not found")
        product = _point_to_product(records[0])
        return {"success": True, "product": product}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/products/facets")
def get_products_facets():
    """Return real category values from Qdrant payloads (for sidebar filters)."""
    try:
        client = get_qdrant_client()
        collection_name = settings.COLLECTION_NAME
        category_counts = {}
        offset = None
        for _ in range(30):
            points, next_offset = client.scroll(
                collection_name=collection_name,
                limit=500,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not points:
                break
            for point in points:
                cat = _extract_category(point.payload)
                if cat and cat.lower() != "general":
                    category_counts[cat] = category_counts.get(cat, 0) + 1
            if next_offset is None:
                break
            offset = next_offset
        categories_sorted = sorted(
            category_counts.keys(),
            key=lambda k: (-category_counts[k], k.lower()),
        )
        return {"success": True, "categories": categories_sorted[:60]}
    except Exception as e:
        logger.error(f"Error fetching facets: {str(e)}")
        return {"success": False, "categories": []}


# Products endpoint - returns products from Qdrant
@app.get("/products")
def get_products(
    limit: int = 12,
    category: str = None,
    page: int = 1,
    min_price: float = None,
    max_price: float = None,
    sort: str = None,
):
    """
    Get products from Qdrant with pagination and filters.
    - category: exact match against extracted category
    - min_price, max_price: price range in TND
    - sort: price_asc | price_desc
    """
    try:
        client = get_qdrant_client()
        collection_name = settings.COLLECTION_NAME
        scroll_limit = 3000
        offset = None
        all_points = []
        while True:
            points, next_offset = client.scroll(
                collection_name=collection_name,
                limit=min(1000, scroll_limit - len(all_points)),
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not points:
                break
            all_points.extend(points)
            if next_offset is None or len(all_points) >= scroll_limit:
                break
            offset = next_offset

        def _sort_products(items: list) -> list:
            if sort == "price_asc":
                return sorted(
                    items,
                    key=lambda p: (p.get("price_numeric") is None, p.get("price_numeric") or 0),
                )
            if sort == "price_desc":
                return sorted(
                    items,
                    key=lambda p: (p.get("price_numeric") is None, -(p.get("price_numeric") or 0)),
                )
            return items

        has_filters = category or min_price is not None or max_price is not None
        if has_filters:
            products = []
            cat_query = (category or "").strip().lower() if category else ""
            for point in all_points:
                payload = point.payload
                if cat_query and cat_query not in ("all", ""):
                    cat = _extract_category(payload).strip().lower()
                    if not cat or cat != cat_query:
                        continue
                product = _point_to_product(point)
                if min_price is not None and (product.get("price_numeric") or 0) < min_price:
                    continue
                if max_price is not None and (product.get("price_numeric") or 0) > max_price:
                    continue
                product["description"] = (product.get("description") or "")[:200]
                products.append(product)
            products = _sort_products(products)
            total_products = len(products)
            total_pages = max(1, (total_products + limit - 1) // limit)
            page = max(1, min(page, total_pages))
            start = (page - 1) * limit
            products_page = products[start : start + limit]
            return {
                "success": True,
                "count": len(products_page),
                "products": products_page,
                "current_page": page,
                "total_pages": total_pages,
                "total_products": total_products,
            }
        else:
            products_all = []
            for point in all_points:
                product = _point_to_product(point)
                product["description"] = (product.get("description") or "")[:200]
                products_all.append(product)
            products_all = _sort_products(products_all)
            total_products = len(products_all)
            total_pages = max(1, (total_products + limit - 1) // limit)
            page = max(1, min(page, total_pages))
            start = (page - 1) * limit
            products_page = products_all[start : start + limit]
            return {
                "success": True,
                "count": len(products_page),
                "products": products_page,
                "current_page": page,
                "total_pages": total_pages,
                "total_products": total_products,
            }
    except Exception as e:
        logger.error(f"Error fetching products: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "products": [],
            "current_page": page,
            "total_pages": 1,
            "total_products": 0,
        }


@app.get("/")
def read_root():
    """Serve index.html for root path"""
    return FileResponse("static/index.html")

# Proxy to Next.js dashboard server
@app.api_route("/dashboard", methods=["GET"])
@app.api_route("/dashboard/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_dashboard(path: str = "", request: Request = None):
    """Proxy requests to Next.js server on port 3000"""
    import httpx
    
    try:
        # Construct the target URL
        target_url = f"http://127.0.0.1:3000/dashboard/{path}" if path else "http://127.0.0.1:3000/"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=request.headers,
                content=await request.body()
            )
            return Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))
    except Exception as e:
        logger.error(f"Proxy error: {str(e)}")
        raise HTTPException(status_code=503, detail="Dashboard service unavailable")

# Catch-all route for serving HTML pages (must be AFTER static mount and BEFORE more specific routes)
@app.get("/{path:path}")
async def serve_page(path: str):
    """
    Serve HTML pages from the static directory.
    If the requested file exists as .html, serve it.
    Otherwise, check if it's a static asset.
    """
    import os
    
    # Don't intercept /api routes (let router handle them)
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    
    # Try to serve the requested file as-is
    file_path = f"static/{path}"
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Try adding .html extension
    if os.path.isfile(f"{file_path}.html"):
        return FileResponse(f"{file_path}.html")
    
    # Default to index.html for SPA-like behavior
    if os.path.isfile("static/index.html") and "." not in path:
        return FileResponse("static/index.html")
    
    # Return 404 if nothing found
    raise HTTPException(status_code=404, detail="Not Found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)