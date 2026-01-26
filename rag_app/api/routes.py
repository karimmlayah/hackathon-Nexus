from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from services.rag import search_and_answer

router = APIRouter()

# --- SCHEMAS ---

class SearchRequest(BaseModel):
    user_query: str

class ProductMetadata(BaseModel):
    name: str
    price: str
    availability: str
    image_url: Optional[str] = None

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
    """
    try:
        # Executes the RAG pipeline: Embedding -> Vector Search -> Prompt -> LLM
        result = await search_and_answer(request.user_query, production_mode=True)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Internal Server Error: {str(e)}"
        )
