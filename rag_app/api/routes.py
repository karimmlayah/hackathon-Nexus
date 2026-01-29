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
    user_query: str

class ProductMetadata(BaseModel):
    name: str
    price: str
    availability: str
    image_url: Optional[str] = None
    price_usd: Optional[float] = None  # For frontend currency conversion
    url: Optional[str] = None  # Product link
    description: Optional[str] = None  # Product description

class SearchResponse(BaseModel):
    answer: str
    products: List[ProductMetadata]

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
        # Validate input
        if not request.user_query or not request.user_query.strip():
            raise HTTPException(
                status_code=400,
                detail="Please enter a search query"
            )
        
        # Executes the RAG pipeline: Embedding -> Vector Search -> Prompt -> LLM
        result = await search_and_answer(request.user_query, production_mode=True)
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Search endpoint error: {error_msg}", exc_info=True)
        
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


# --- CHAT ENDPOINT (Alternative naming) ---
# Alias for /search endpoint to support frontend calls to /api/chat

class ChatRequest(BaseModel):
    """Chat request with user message."""
    message: str

class ChatResponse(BaseModel):
    """Chat response with assistant answer and products."""
    answer: str
    products: List[ProductMetadata]

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint - alternative naming for the search/RAG pipeline.
    This allows the frontend to use /api/chat while using the same RAG logic.
    
    Supports both 'message' and 'user_query' parameter names for compatibility.
    """
    try:
        # Validate input
        query = request.message.strip() if request.message else ""
        if not query:
            raise HTTPException(
                status_code=400,
                detail="Please enter a message"
            )
        
        # Executes the RAG pipeline: Embedding -> Vector Search -> Prompt -> LLM
        result = await search_and_answer(query, production_mode=True)
        return ChatResponse(answer=result["answer"], products=result["products"])
        
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
