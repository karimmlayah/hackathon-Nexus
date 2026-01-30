"""
User Tracking API
Endpoints for tracking user interactions and updating profiles
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime

from rag_app.services.recommendation_service import recommendation_service
from rag_app.core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/track", tags=["tracking"])

class TrackInteractionRequest(BaseModel):
    user_id: Optional[str] = None
    product_id: str
    interaction_type: str  # view, click, add-to-cart, search
    metadata: Optional[dict] = None

class TrackSearchRequest(BaseModel):
    user_id: Optional[str] = None
    query: str
    results_count: int
    metadata: Optional[dict] = None

@router.post("/view")
async def track_view(request: TrackInteractionRequest, current_user: dict = Depends(get_current_user)):
    """Track product view"""
    try:
        user_id = request.user_id or current_user.get("email", "anonymous")
        await recommendation_service.capture_interaction(user_id, "view", request.product_id)
        
        logger.info(f"Tracked view: user {user_id} viewed product {request.product_id}")
        return {"status": "success", "message": "View tracked successfully"}
    
    except Exception as e:
        logger.error(f"Error tracking view: {e}")
        raise HTTPException(status_code=500, detail="Failed to track view")

@router.post("/click")
async def track_click(request: TrackInteractionRequest, current_user: dict = Depends(get_current_user)):
    """Track product click"""
    try:
        user_id = request.user_id or current_user.get("email", "anonymous")
        await recommendation_service.capture_interaction(user_id, "click", request.product_id)
        
        logger.info(f"Tracked click: user {user_id} clicked product {request.product_id}")
        return {"status": "success", "message": "Click tracked successfully"}
    
    except Exception as e:
        logger.error(f"Error tracking click: {e}")
        raise HTTPException(status_code=500, detail="Failed to track click")

@router.post("/add-to-cart")
async def track_add_to_cart(request: TrackInteractionRequest, current_user: dict = Depends(get_current_user)):
    """Track add to cart"""
    try:
        user_id = request.user_id or current_user.get("email", "anonymous")
        await recommendation_service.capture_interaction(user_id, "cart", request.product_id)
        
        logger.info(f"Tracked add to cart: user {user_id} added product {request.product_id} to cart")
        return {"status": "success", "message": "Add to cart tracked successfully"}
    
    except Exception as e:
        logger.error(f"Error tracking add to cart: {e}")
        raise HTTPException(status_code=500, detail="Failed to track add to cart")

@router.post("/wishlist")
async def track_wishlist(request: TrackInteractionRequest, current_user: dict = Depends(get_current_user)):
    """Track wishlist addition"""
    try:
        user_id = request.user_id or current_user.get("email", "anonymous")
        await recommendation_service.capture_interaction(user_id, "wishlist", request.product_id)
        
        logger.info(f"Tracked wishlist: user {user_id} added product {request.product_id} to wishlist")
        return {"status": "success", "message": "Wishlist addition tracked successfully"}
    
    except Exception as e:
        logger.error(f"Error tracking wishlist: {e}")
        raise HTTPException(status_code=500, detail="Failed to track wishlist")

@router.post("/purchase")
async def track_purchase(request: TrackInteractionRequest, current_user: dict = Depends(get_current_user)):
    """Track purchase"""
    try:
        user_id = request.user_id or current_user.get("email", "anonymous")
        await recommendation_service.capture_interaction(user_id, "purchase", request.product_id)
        
        logger.info(f"Tracked purchase: user {user_id} purchased product {request.product_id}")
        return {"status": "success", "message": "Purchase tracked successfully"}
    
    except Exception as e:
        logger.error(f"Error tracking purchase: {e}")
        raise HTTPException(status_code=500, detail="Failed to track purchase")

@router.post("/search")
async def track_search(request: TrackSearchRequest, current_user: dict = Depends(get_current_user)):
    """Track search query"""
    try:
        user_id = request.user_id or current_user.get("email", "anonymous")
        
        # Store search interaction - we could store this in a separate collection
        # For now, we'll just log it
        logger.info(f"Tracked search: user {user_id} searched for '{request.query}' ({request.results_count} results)")
        
        return {
            "status": "success", 
            "message": "Search tracked successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error tracking search: {e}")
        raise HTTPException(status_code=500, detail="Failed to track search")

@router.get("/interactions/{user_id}")
async def get_user_interactions(user_id: str, limit: int = 20):
    """Get user interaction history"""
    try:
        from rag_app.core.database import get_qdrant_client
        from qdrant_client.http import models
        
        client = get_qdrant_client()
        
        # Get user profile with interaction history
        points = client.scroll(
            collection_name="users",
            scroll_filter=models.Filter(
                must=[models.FieldCondition(key="user_email", match=models.MatchValue(value=user_id))]
            ),
            limit=1,
            with_payload=True
        )[0]
        
        if not points:
            return {"interactions": [], "user_id": user_id}
        
        user_profile = points[0]
        interactions = user_profile.payload.get("interactions", [])
        
        # Return recent interactions
        recent_interactions = interactions[-limit:] if interactions else []
        
        return {
            "user_id": user_id,
            "interactions": recent_interactions,
            "total_interactions": len(interactions)
        }
    
    except Exception as e:
        logger.error(f"Error getting user interactions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user interactions")
