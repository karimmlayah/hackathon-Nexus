"""
Recommendations API Endpoints
Provides personalized product recommendations with collaborative filtering
and seed-based recommendations (favoris, panier, recherche) for guests and cold start.
Uses request.app.state.qdrant_client and .collection_name when available (same as main app).
"""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import numpy as np

from rag_app.services.collaborative_recommendation import collaborative_recommendation_service
from rag_app.core.database import get_qdrant_client, get_deterministic_id
from rag_app.core.config import settings
from rag_app.core import qdrant_ops as qdrant_tool

logger = logging.getLogger(__name__)

def _get_client_and_collection(request: Optional[Request] = None):
    """Use app.state when running under main app (uvicorn app:app) so we use same Qdrant/collection."""
    if request is not None:
        qc = getattr(request.app.state, "qdrant_client", None)
        cn = getattr(request.app.state, "collection_name", None)
        if qc is not None and cn:
            return qc, cn
    return get_qdrant_client(), settings.COLLECTION_NAME

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

class RecommendationResponse(BaseModel):
    """Response model for recommendations"""
    success: bool
    count: int
    recommendations: List[Dict[str, Any]]
    strategy: str
    message: Optional[str] = None


def _get_seed_from_sqlite(user_email: str, max_interactions: int = 100) -> tuple:
    """
    Load user's recent interactions from SQLite (user_interactions).
    Returns (product_ids: List[str], search_query: Optional[str]).
    """
    try:
        import os
        import sys
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if _root not in sys.path:
            sys.path.insert(0, _root)
        import django
        from django.conf import settings
        if not getattr(settings, "configured", False):
            settings.configure(
                DEBUG=True,
                DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.path.join(_root, "rag_app.db")}},
                INSTALLED_APPS=["django.contrib.auth", "django.contrib.contenttypes", "rag_app"],
                SECRET_KEY="django-insecure-rag-app",
                USE_TZ=True,
            )
            django.setup()
        from django.contrib.auth.models import User
        from rag_app.models import UserInteraction
        user = User.objects.filter(email=user_email.strip()).first()
        if not user:
            user = User.objects.filter(username=user_email.strip()).first()
        if not user:
            return ([], None)
        interactions = list(
            UserInteraction.objects.filter(user=user)
            .select_related("product")
            .order_by("-created_at")[:max_interactions]
        )
        product_ids = []
        search_queries = []
        for i in interactions:
            if i.interaction_type == "search" and i.metadata:
                q = (i.metadata or {}).get("query", "").strip()
                if q:
                    search_queries.append(q)
            elif i.product_id:
                product_ids.append(str(i.product.qdrant_id))
        product_ids = list(dict.fromkeys(product_ids))[:50]
        search_query = " ".join(search_queries[:3]) if search_queries else None
        return (product_ids, search_query)
    except Exception as e:
        logger.debug("SQLite seed for %s: %s", user_email, e)
        return ([], None)


def _id_sets(csv: Optional[str]) -> set:
    return {x.strip() for x in (csv or "").split(",") if x.strip()}


async def _recommendations_by_seed_impl(
    raw_ids: List[str],
    search_query: Optional[str],
    limit: int,
    client=None,
    collection_name: Optional[str] = None,
    cart_ids: Optional[set] = None,
    wishlist_ids: Optional[set] = None,
) -> List[Dict[str, Any]]:
    """Core by-seed: product_ids + optional search_query. Cart/wishlist weighted more for a real mix."""
    if not raw_ids and not (search_query and search_query.strip()):
        return []
    if client is None:
        client = get_qdrant_client()
    if not collection_name:
        collection_name = settings.COLLECTION_NAME
    vector_name = settings.VECTOR_NAME
    cart_ids = cart_ids or set()
    wishlist_ids = wishlist_ids or set()
    weighted = []
    seed_ids_set = set()
    for pid_str in (raw_ids or [])[:50]:
        try:
            pid = get_deterministic_id(pid_str)
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
                w = 2.0 if pid_str in cart_ids else (1.5 if pid_str in wishlist_ids else 1.0)
                weighted.append((v, w))
                seed_ids_set.add(pid)
                seed_ids_set.add(pid_str)
        except Exception as e:
            logger.debug("Skip product %s: %s", pid_str, e)
    if search_query and search_query.strip():
        try:
            from rag_app.core.llm import get_embedding
            qv = get_embedding(search_query.strip())
            weighted.append((qv, 1.5))
        except Exception as e:
            logger.warning("Search query embedding failed: %s", e)
    if not weighted:
        return []
    vectors = [x[0] for x in weighted]
    weights = [x[1] for x in weighted]
    total_w = sum(weights)
    avg_vector = (np.average(vectors, axis=0, weights=weights) if total_w > 0 else np.mean(vectors, axis=0)).astype(float).tolist()
    from qdrant_client.http import models
    query_filter = None
    if raw_ids:
        query_filter = models.Filter(
            must_not=[models.FieldCondition(key="id", match=models.MatchAny(any=raw_ids))]
        )
    recs = qdrant_tool.search_products(
        client=client,
        collection_name=collection_name,
        query_vector=avg_vector,
        limit=limit + len(raw_ids) + 5,
        vector_name=vector_name,
        query_filter=query_filter,
    )
    seed_str = {str(x) for x in seed_ids_set}
    seen = set()
    out = []
    for r in recs:
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
    return out


# Declare "" and "/" first so GET /api/recommendations (no path param) matches before /{user_email}
@router.get("")
@router.get("/")
async def get_recommendations_query(
    request: Request,
    user_email: str,
    limit: int = 6,
    include_explanation: bool = True,
    budget_max: Optional[float] = None,
    budget_min: Optional[float] = None,
    availability: Optional[bool] = None,
    payment_method: Optional[str] = None,
    product_ids: Optional[str] = Query(None, description="Comma-separated product IDs from cart/wishlist"),
    cart_ids: Optional[str] = Query(None, description="IDs in cart (weighted higher)"),
    wishlist_ids: Optional[str] = Query(None, description="IDs in wishlist (weighted higher)"),
    search_query: Optional[str] = Query(None, description="Last search query from client"),
) -> RecommendationResponse:
    """GET /api/recommendations?user_email=...&product_ids=...&cart_ids=...&wishlist_ids=... (query params)."""
    return await get_recommendations(
        request, user_email, limit, include_explanation,
        budget_max=budget_max, budget_min=budget_min,
        availability=availability, payment_method=payment_method,
        product_ids=product_ids, cart_ids=cart_ids, wishlist_ids=wishlist_ids, search_query=search_query,
    )


@router.get("/debug")
async def get_recommendations_debug(user_email: str = Query(..., description="User email to debug")):
    """
    Debug endpoint: see how many interactions are in SQLite for this user and which strategy would be used.
    Call: GET /api/recommendations/debug?user_email=your@email.com
    """
    product_ids, search_query = _get_seed_from_sqlite(user_email.strip())
    try:
        from django.contrib.auth.models import User
        from rag_app.models import UserInteraction
        user = User.objects.filter(email=user_email.strip()).first()
        if not user:
            user = User.objects.filter(username=user_email.strip()).first()
        count = UserInteraction.objects.filter(user=user).count() if user else 0
    except Exception as e:
        count = -1
    return {
        "user_email": user_email,
        "sqlite_interactions_count": count,
        "product_ids_from_sqlite": product_ids,
        "search_queries_from_sqlite": search_query,
        "strategy_will_be": "by-seed (SQLite)" if (product_ids or (search_query and search_query.strip())) else "fallback (Qdrant/trending)",
        "message": "Faites une recherche, ajoutez aux favoris ou au panier puis rechargez Pour vous pour voir des recommandations personnalisées.",
    }


@router.get("/by-seed", response_model=RecommendationResponse)
async def get_recommendations_by_seed(
    request: Request,
    product_ids: Optional[str] = Query(None, description="Comma-separated product IDs"),
    cart_ids: Optional[str] = Query(None, description="IDs in cart (weighted higher)"),
    wishlist_ids: Optional[str] = Query(None, description="IDs in wishlist (weighted higher)"),
    history_ids: Optional[str] = Query(None, description="IDs from history"),
    search_query: Optional[str] = Query(None, description="Optional search query to mix with product vectors"),
    limit: int = Query(12, ge=1, le=24),
) -> RecommendationResponse:
    """
    Recommendations from seed; cart and wishlist weighted more for a real mix.
    """
    try:
        raw_ids = [x.strip() for x in (product_ids or "").split(",") if x.strip()]
        if not raw_ids and not (search_query and search_query.strip()):
            return RecommendationResponse(
                success=True,
                count=0,
                recommendations=[],
                strategy="by-seed",
                message="Provide product_ids and/or search_query",
            )
        client, collection_name = _get_client_and_collection(request)
        cart_set = _id_sets(cart_ids)
        wishlist_set = _id_sets(wishlist_ids)
        out = await _recommendations_by_seed_impl(
            raw_ids, search_query, limit, client=client, collection_name=collection_name,
            cart_ids=cart_set, wishlist_ids=wishlist_set,
        )
        return RecommendationResponse(
            success=True,
            count=len(out),
            recommendations=out,
            strategy="by-seed",
            message=f"Found {len(out)} recommendations from your favoris, panier and search.",
        )
    except Exception as e:
        logger.error("Recommendations by-seed failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Recommendations failed: {str(e)}")


@router.get("/{user_email}")
async def get_recommendations(
    request: Request,
    user_email: str,
    limit: int = 6,
    include_explanation: bool = True,
    budget_max: Optional[float] = None,
    budget_min: Optional[float] = None,
    availability: Optional[bool] = None,
    payment_method: Optional[str] = None,
    product_ids: Optional[str] = Query(None, description="Comma-separated product IDs from cart/wishlist"),
    cart_ids: Optional[str] = Query(None, description="IDs in cart (weighted higher)"),
    wishlist_ids: Optional[str] = Query(None, description="IDs in wishlist (weighted higher)"),
    search_query: Optional[str] = Query(None, description="Last search query from client"),
) -> RecommendationResponse:
    """
    Personalized recommendations per account.
    First uses SQLite (user_interactions). If SQLite empty, uses product_ids/cart_ids/wishlist_ids from query params.
    Cart and wishlist weighted more for a real mix.
    """
    try:
        logger.info(f"Getting recommendations for {user_email}, limit={limit}")
        client, collection_name = _get_client_and_collection(request)
        sqlite_ids, sqlite_query = _get_seed_from_sqlite(user_email)
        product_ids_list = list(sqlite_ids) if sqlite_ids else []
        search_query_val = (sqlite_query or "").strip() or None
        cart_set = _id_sets(cart_ids)
        wishlist_set = _id_sets(wishlist_ids)
        if not product_ids_list and not search_query_val and product_ids:
            product_ids_list = [x.strip() for x in product_ids.split(",") if x.strip()][:50]
        if not search_query_val and search_query and search_query.strip():
            search_query_val = search_query.strip()
        if product_ids_list or search_query_val:
            recs = await _recommendations_by_seed_impl(
                product_ids_list, search_query_val, limit, client=client, collection_name=collection_name,
                cart_ids=cart_set, wishlist_ids=wishlist_set,
            )
            if recs:
                return RecommendationResponse(
                    success=True,
                    count=len(recs),
                    recommendations=recs,
                    strategy="by-seed (SQLite)" if (sqlite_ids or sqlite_query) else "by-seed",
                    message=f"Recommandations basées sur vos recherches, favoris et panier ({len(recs)} produits).",
                )
        # Fallback: Qdrant collaborative / trending
        recommendations = await collaborative_recommendation_service.get_recommendations_with_collaborative(
            user_email=user_email,
            limit=limit,
            include_explanation=include_explanation,
            budget_max=budget_max,
            budget_min=budget_min,
            availability=availability,
            payment_method=payment_method,
        )
        
        # Fallback to basic recommendation service if no results
        if not recommendations:
            logger.info(f"No collaborative recommendations for {user_email}, trying basic service")
            from rag_app.services.recommendation_service import recommendation_service
            basic_recs = await recommendation_service.get_recommendations(user_email, limit)
            
            # Convert basic recommendations to expected format
            recommendations = []
            for product in basic_recs:
                rec = {
                    "id": product.get("id"),
                    "name": product.get("name"),
                    "title": product.get("title"),
                    "price": product.get("price"),
                    "image": product.get("image"),
                    "image_url": product.get("image_url"),
                    "category": product.get("category"),
                    "rating": product.get("rating"),
                    "url": product.get("url"),
                    "explanation": "Produit populaire correspondant à vos intérêts",
                    "sources": ["trending"],
                    "discount": product.get("discount", 0)
                }
                recommendations.append(rec)
        
        # Determine strategy used
        if recommendations:
            sources = recommendations[0].get("sources", [])
            if "collaborative" in sources:
                strategy = "hybrid (personal + collaborative)"
            elif "personal" in sources:
                strategy = "personal (cold start)"
            elif "trending" in sources:
                strategy = "trending (fallback)"
            else:
                strategy = "trending (fallback)"
        else:
            strategy = "none"
        
        return RecommendationResponse(
            success=True,
            count=len(recommendations),
            recommendations=recommendations,
            strategy=strategy,
            message=f"Found {len(recommendations)} personalized recommendations"
        )
        
    except Exception as e:
        logger.error(f"Error getting recommendations for {user_email}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recommendations: {str(e)}"
        )
