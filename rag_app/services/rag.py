from qdrant_client.http import models
from core.database import get_qdrant_client
from core.config import settings
from core.llm import get_embedding, query_llm

async def search_and_answer(question: str, production_mode: bool = False):
    """
    Full RAG pipeline specialized for E-commerce.
    """
    client = get_qdrant_client()
    
    # 1. Embed question using same model as indexing
    query_vector = get_embedding(question)
    
    # 2. Search Qdrant (top_k=5)
    search_result = client.query_points(
        collection_name=settings.COLLECTION_NAME,
        query=query_vector,
        using=settings.VECTOR_NAME,
        limit=5
    ).points
    
    # 3. Construct Context & Extracted metadata
    context_lines = []
    products_metadata = []
    
    for hit in search_result:
        p = hit.payload
        
        # Extract fields for structured response
        name = p.get("name") or p.get("title") or "Unknown Product"
        price = f"{p.get('final_price', p.get('price', 'N/A'))} {p.get('currency', '$')}"
        availability = p.get("availability", "In Stock")
        image_url = p.get("image_url") or p.get("image") or ""
        description = p.get("description", "")[:250]
        
        # Format for LLM Context
        product_context = (
            f"- Name: {name}\n"
            f"  Price: {price}\n"
            f"  Availability: {availability}\n"
            f"  Description: {description}\n"
            f"  Image URL: {image_url}\n"
        )
        context_lines.append(product_context)
        
        # Add to structured product list for API response
        products_metadata.append({
            "name": name,
            "price": price,
            "availability": availability,
            "image_url": image_url
        })
            
    context = "\n\n".join(context_lines)
    
    # 4. Generate Expert Answer
    answer = query_llm(context, question)
    
    if production_mode:
        return {
            "answer": answer,
            "products": products_metadata
        }
    
    # Legacy support
    return {
        "answer": answer,
        "sources": [p["name"] for p in products_metadata],
        "images": [p["image_url"] for p in products_metadata if p["image_url"]],
        "context": context_lines
    }
