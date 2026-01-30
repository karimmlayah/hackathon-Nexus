from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
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
    Track user interactions for the AI Recommendation Agent.
    Types: view, wishlist, cart, purchase
    """
    try:
        from services.recommendation_service import recommendation_service
        # Run in background to not block the request
        import asyncio
        asyncio.create_task(recommendation_service.capture_interaction(
            user_email=request.user_email,
            interaction_type=request.type,
            product_id=request.product_id
        ))
        return InteractionResponse(success=True, message="Interaction captured")
    except Exception as e:
        logger.error(f"Interaction tracking error: {str(e)}")
        return InteractionResponse(success=False, message=str(e))

@router.get("/recommendations", response_model=RecommendationResponse)
async def get_personalized_recommendations(user_email: str, limit: int = 4):
    """
    Get personalized recommendations for a user based on their AI preference profile.
    """
    try:
        from services.recommendation_service import recommendation_service
        products = await recommendation_service.get_recommendations(user_email, limit)
        
        # Format for ProductMetadata
        formatted_products = []
        for p in products:
            formatted_products.append(ProductMetadata(
                name=p.get("name", "Unknown"),
                price=str(p.get("price", "0 DT")),
                availability=p.get("availability", "In Stock"),
                image_url=p.get("image", ""),
                url=p.get("url", ""),
                description=p.get("description", "")
            ))
            
        return RecommendationResponse(success=True, products=formatted_products)
    except Exception as e:
        logger.error(f"Recommendation error: {str(e)}")
        return RecommendationResponse(success=False, products=[])
