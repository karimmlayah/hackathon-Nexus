from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.rag import search_and_answer

logger = logging.getLogger(__name__)
router = APIRouter()

# --- SCHEMAS ---

class SearchRequest(BaseModel):
    user_query: Optional[str] = None
    image_base64: Optional[str] = None
    limit: Optional[int] = 12

class ProductMetadata(BaseModel):
    name: str
    price: str
    price_numeric: Optional[float] = None # For sorting/filtering
    availability: str
    image_url: Optional[str] = None
    image: Optional[str] = None  # Frontend compatibility
    price_usd: Optional[float] = None
    url: Optional[str] = None
    description: Optional[str] = None
    asin: Optional[str] = None  # For linking to single product page
    id: Optional[str] = None   # Qdrant point id, for linking when asin missing
    rating: Optional[float] = None  # For star display
    discount: Optional[float] = None  # For deal/sale display

class InteractionRequest(BaseModel):
    user_email: str
    type: str # view, wishlist, cart, purchase
    product_id: str

class InteractionResponse(BaseModel):
    success: bool
    message: str

class RecommendationResponse(BaseModel):
    success: bool
    products: List[ProductMetadata]

class SearchResponse(BaseModel):
    answer: str
    products: List[ProductMetadata]
    results: List[ProductMetadata] = [] # Frontend compatibility
    count: int = 0 # Frontend compatibility


class ShortenTitlesRequest(BaseModel):
    titles: List[str]
    max_chars: int = 35


class ShortenTitlesResponse(BaseModel):
    ok: bool
    short_titles: List[str] = []


# --- ENDPOINTS ---

@router.post("/search", response_model=SearchResponse)
async def production_search(request: SearchRequest):
    """
    Production-grade RAG search endpoint.
    Retrieves relevant products from the 'amazon30015' collection 
    and generates a grounded shopping assistant answer using an LLM.
    
    Returns friendly error messages for connection issues.
    """
    try:
        # Validate input: require either text or image
        if not request.user_query and not request.image_base64:
            raise HTTPException(
                status_code=400,
                detail="Please provide a text query or an image for searching."
            )
        
        # Executes the multimodal RAG pipeline
        from services.rag import multimodal_search_and_answer
        result = await multimodal_search_and_answer(
            question=request.user_query, 
            image_base64=request.image_base64,
            production_mode=True, 
            limit=request.limit
        )
        return result
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        detail = f"Search endpoint error: {error_msg}\n{traceback.format_exc()}"
        logger.error(detail)
        raise HTTPException(status_code=500, detail=detail)

@router.post("/search/image", response_model=SearchResponse)
async def image_search(request: SearchRequest):
    """
    Search using image (and optional text query).
    """
    return await production_search(request)

# --- STATS ENDPOINT ---

@router.get("/stats")
async def get_dashboard_stats():
    """
    Get statistics for the dashboard.
    Returns counts for products, categories, brands, and availability from Qdrant.
    """
    try:
        from core.database import get_qdrant_client
        from core.config import settings
        from qdrant_client.http import models

        client = get_qdrant_client()
        collection_name = settings.COLLECTION_NAME

        # 1. Total Products (Exact)
        count_result = client.count(collection_name=collection_name, exact=True)
        total_products = count_result.count

        # 2. Categories, Brands & In Stock (Approximation via Scroll)
        # We scroll a sample to estimate derived metrics to avoid complex filter errors
        # and performance issues.
        limit = 1000
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=["category", "categories", "brand", "manufacturer", "availability"],
            with_vectors=False
        )

        categories = set()
        brands = set()
        sample_in_stock = 0
        sample_size = len(points)

        for point in points:
            payload = point.payload or {}
            
            # Category
            cat = payload.get("category") or payload.get("categories")
            if cat:
                if isinstance(cat, list):
                    for c in cat:
                        categories.add(str(c).strip())
                else:
                    categories.add(str(cat).strip())
            
            # Brand
            brand = payload.get("brand") or payload.get("manufacturer")
            if brand:
                brands.add(str(brand).strip())

            # In Stock Check
            avail = payload.get("availability", "In Stock")
            # Loose matching for "In Stock"
            if "stock" in str(avail).lower() and "out" not in str(avail).lower(): 
                 sample_in_stock += 1
            elif str(avail).lower() == "in stock":
                 sample_in_stock += 1

        # Calculate In Stock
        if sample_size > 0:
            ratio = sample_in_stock / sample_size
            in_stock = int(total_products * ratio)
        else:
            in_stock = 0

        return {
            "total_products": total_products,
            "total_categories": len(categories),
            "total_brands": len(brands),
            "in_stock": in_stock
        }

    except Exception as e:
        logger.error(f"Stats endpoint error: {str(e)}", exc_info=True)
        return {
            "total_products": 0,
            "total_categories": 0,
            "total_brands": 0,
            "in_stock": 0
        }


# --- CHAT ENDPOINT (Alternative naming) ---
# Alias for /search endpoint to support frontend calls to /api/chat

class ChatRequest(BaseModel):
    """Chat request with user message and optional image."""
    message: Optional[str] = None
    image_base64: Optional[str] = None
    limit: Optional[int] = 12

class ChatResponse(BaseModel):
    """Chat response with assistant answer and products."""
    answer: str
    products: List[ProductMetadata]
    results: List[ProductMetadata] = [] # Frontend compatibility
    count: int = 0 # Frontend compatibility

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint - alternative naming for the search/RAG pipeline.
    This allows the frontend to use /api/chat while using the same RAG logic.
    
    Supports both 'message' and 'user_query' parameter names for compatibility.
    """
    try:
        # Validate input: require either text or image
        query = request.message.strip() if request.message else ""
        if not query and not request.image_base64:
            raise HTTPException(
                status_code=400,
                detail="Please enter a message or upload an image"
            )
        
        # Executes the multimodal RAG pipeline
        from services.rag import multimodal_search_and_answer
        result = await multimodal_search_and_answer(
            question=query if query else None, 
            image_base64=request.image_base64,
            production_mode=True, 
            limit=request.limit
        )
        return ChatResponse(
            answer=result["answer"], 
            products=result["products"], 
            results=result["results"], 
            count=result["count"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Chat endpoint error: {error_msg}", exc_info=True)
        
        # Provide specific error messages based on error type
        if "connection" in error_msg.lower() or "connect" in error_msg.lower():
            detail = "Oops! I hit a snag. Please check your connection."
            status_code = 503
        elif "timeout" in error_msg.lower():
            detail = "The request took too long. Please try again."
            status_code = 504
        elif "api" in error_msg.lower() or "groq" in error_msg.lower():
            detail = "Oops! I hit a snag. Please check your connection."
            status_code = 503
        elif "database" in error_msg.lower() or "qdrant" in error_msg.lower():
            detail = "Oops! I hit a snag. Please check your connection."
            status_code = 503
        else:
            detail = "An unexpected error occurred. Please try again later."
            status_code = 500
        
        raise HTTPException(status_code=status_code, detail=detail)

# --- RECOMMENDATION ENDPOINTS ---

@router.post("/interactions", response_model=InteractionResponse)
async def track_interaction(request: InteractionRequest):
    """
    Track user interactions for recommendations.
    Types: view, wishlist, cart, purchase, search.
    Saves to SQLite (user_interactions) so recommendations change per account.
    """
    try:
        from services.recommendation_service import recommendation_service
        import asyncio
        asyncio.create_task(recommendation_service.capture_interaction(
            user_email=request.user_email,
            interaction_type=request.type,
            product_id=request.product_id
        ))
        # Save to SQLite (Django) so recommendations use search/favorite/cart per account
        try:
            from services.interaction_storage import save_interaction_to_db
            save_interaction_to_db(
                user_email=request.user_email,
                interaction_type=request.type,
                product_id=request.product_id or "",
            )
        except Exception as db_e:
            logger.warning("Failed to save interaction to SQLite: %s", db_e)
        return InteractionResponse(success=True, message="Interaction captured")
    except Exception as e:
        logger.error(f"Interaction tracking error: {str(e)}")
        return InteractionResponse(success=False, message=str(e))

# GET /api/recommendations is handled by rag_app.api.recommendations router
# (personalized from SQLite + by-seed; do not duplicate here to avoid generic list-by-id)

# --- PRODUCT DETAIL AND SIMILAR PRODUCTS ENDPOINTS ---

class SimilarProductsRequest(BaseModel):
    id: Optional[str] = None
    asin: Optional[str] = None
    limit: Optional[int] = 5

class SimilarProductsResponse(BaseModel):
    ok: bool
    results: List[ProductMetadata]

class ProductDetailsResponse(BaseModel):
    ok: bool
    product: dict


def _find_product_point(client, collection_name: str, *, asin: Optional[str], id: Optional[str], with_vectors: bool):
    next_offset = None
    while True:
        points, next_offset = client.scroll(
            collection_name=collection_name,
            offset=next_offset,
            limit=256,
            with_payload=True,
            with_vectors=with_vectors,
        )
        for point in points:
            if id is not None and str(point.id) == str(id):
                return point
            if asin is not None and point.payload and point.payload.get("asin") == asin:
                return point
        if next_offset is None:
            return None


def _parse_discount(value) -> Optional[float]:
    """
    Parse discount from payload. Handles:
    - numbers: 30, 50, 30.5
    - strings: "-30%", "30%", "-50%", "50%", "30", "-30"
    Returns the numeric percentage (e.g. 30 for "-30%" or "30%"), or None if invalid.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else abs(float(value))
    s = str(value).strip()
    if not s:
        return None
    m = re.search(r"-?(\d+(?:\.\d+)?)\s*%?", s)
    if m:
        return abs(float(m.group(1)))
    try:
        return abs(float(s))
    except (TypeError, ValueError):
        return None


@router.get("/discounted-products", response_model=SimilarProductsResponse)
async def get_discounted_products(min_discount: float = 30, limit: int = 10):
    """
    Return products with discount >= min_discount (e.g. 30% off or more).
    Discount in Qdrant can be a number or string like "-30%", "30%".
    Scrolls the full collection in batches so no discounted products are missed.
    """
    try:
        from core.database import get_qdrant_client
        from core.config import settings

        client = get_qdrant_client()
        collection_name = settings.COLLECTION_NAME

        results = []
        next_offset = None
        batch_size = 256
        max_batches = 500  # cap to avoid very long requests (~128k points)

        for _ in range(max_batches):
            points, next_offset = client.scroll(
                collection_name=collection_name,
                offset=next_offset,
                limit=batch_size,
                with_payload=True,
                with_vectors=False,
            )
            if not points:
                break
            for point in points:
                payload = point.payload or {}
                disc_raw = payload.get("discount")
                disc_num = _parse_discount(disc_raw)
                if disc_num is None or disc_num < min_discount:
                    continue
                results.append(
                    ProductMetadata(
                        name=payload.get("title", "Unknown Product"),
                        price=str(payload.get("final_price", payload.get("price", "0"))),
                        price_numeric=payload.get("final_price", payload.get("price", 0)),
                        availability=payload.get("availability", "Unknown"),
                        image_url=payload.get("image_url", ""),
                        image=payload.get("image_url", ""),
                        description=payload.get("description", ""),
                        url=payload.get("url", ""),
                        asin=payload.get("asin"),
                        id=str(point.id) if point.id is not None else None,
                        rating=payload.get("rating"),
                        discount=disc_num,
                    )
                )
                if len(results) >= limit:
                    break
            if len(results) >= limit or next_offset is None:
                break
        return SimilarProductsResponse(ok=True, results=results[:limit])
    except Exception as e:
        logger.error(f"Discounted products error: {str(e)}", exc_info=True)
        return SimilarProductsResponse(ok=False, results=[])


@router.post("/shorten-titles", response_model=ShortenTitlesResponse)
async def shorten_titles_api(request: ShortenTitlesRequest):
    """
    Shorten product titles using Groq LLM so they fit a fixed-width card.
    Returns one short title per input, in the same order.
    """
    try:
        from core.llm import shorten_titles as llm_shorten
        short = llm_shorten(request.titles, request.max_chars)
        return ShortenTitlesResponse(ok=True, short_titles=short)
    except Exception as e:
        logger.warning(f"Shorten titles error: {e}")
        # Fallback: truncate
        max_c = request.max_chars
        short = []
        for t in request.titles:
            t = (t or "").strip()
            if len(t) <= max_c:
                short.append(t)
            else:
                short.append(t[: max_c - 1] + "…" if max_c > 1 else t[:max_c])
        return ShortenTitlesResponse(ok=True, short_titles=short)


@router.get("/similar-products", response_model=SimilarProductsResponse)
async def get_similar_products(id: Optional[str] = None, asin: Optional[str] = None, limit: int = 5):
    """
    Get similar products using vector search based on product ID or ASIN.
    Uses the text_dense vector (384 dimensions) for similarity search.
    """
    try:
        from core.database import get_qdrant_client
        from core.config import settings
        
        client = get_qdrant_client()
        collection_name = settings.COLLECTION_NAME

        if not id and not asin:
            raise HTTPException(status_code=400, detail="Either 'id' or 'asin' parameter is required")

        target_point = _find_product_point(
            client,
            collection_name,
            asin=asin,
            id=id,
            with_vectors=True,
        )
        if not target_point:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get the text_dense vector
        target_vector = target_point.vector.get("text_dense") if target_point.vector else None
        
        if not target_vector:
            raise HTTPException(status_code=500, detail="Target product has no text_dense vector")
        
        # Search for similar products using query_points
        similar_results = client.query_points(
            collection_name=collection_name,
            query=target_vector,
            using="text_dense",
            limit=limit + 1,  # Get one extra to account for the original
            with_payload=True
        )
        
        # Filter out the original product and format results
        similar_products = []
        for point in similar_results.points:
            if point.id != target_point.id:  # Exclude the original product
                payload = point.payload or {}
                product = ProductMetadata(
                    name=payload.get("title", "Unknown Product"),
                    price=str(payload.get("final_price", payload.get("price", "0"))),
                    price_numeric=payload.get("final_price", payload.get("price", 0)),
                    availability=payload.get("availability", "Unknown"),
                    image_url=payload.get("image_url", ""),
                    image=payload.get("image_url", ""),  # Frontend compatibility
                    description=payload.get("description", ""),
                    url=payload.get("url", ""),
                    asin=payload.get("asin"),
                    id=str(point.id) if point.id is not None else None,
                    rating=payload.get("rating"),
                )
                similar_products.append(product)
                
                if len(similar_products) >= limit:
                    break
        
        return SimilarProductsResponse(ok=True, results=similar_products)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similar products error: {str(e)}", exc_info=True)
        return SimilarProductsResponse(ok=False, results=[])

@router.get("/product-details", response_model=ProductDetailsResponse)
async def get_product_details(id: Optional[str] = None, asin: Optional[str] = None):
    """
    Get detailed product information including top_review.
    """
    try:
        from core.database import get_qdrant_client
        from core.config import settings
        
        client = get_qdrant_client()
        collection_name = settings.COLLECTION_NAME
        
        if not id and not asin:
            raise HTTPException(status_code=400, detail="Either 'id' or 'asin' parameter is required")
        
        target_point = _find_product_point(
            client,
            collection_name,
            asin=asin,
            id=id,
            with_vectors=False,
        )
        if not target_point:
            raise HTTPException(status_code=404, detail="Product not found")
        
        payload = target_point.payload or {}
        
        # Return all product data including top_review
        return ProductDetailsResponse(ok=True, product=payload)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Product details error: {str(e)}", exc_info=True)
        return ProductDetailsResponse(ok=False, product={})