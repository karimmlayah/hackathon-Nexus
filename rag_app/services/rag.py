from qdrant_client.http import models
from qdrant_client import QdrantClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.database import get_qdrant_client
from core.config import settings
from core.llm import get_embedding, query_llm
from core.currency import convert_to_tnd, format_price_tnd, detect_currency
import logging

logger = logging.getLogger(__name__)

async def search_and_answer(question: str, production_mode: bool = False):
    """
    Full RAG pipeline specialized for E-commerce.
    Includes error handling for Qdrant and LLM failures.
    """
    try:
        client = get_qdrant_client()
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {str(e)}")
        raise Exception(f"Database connection error: Unable to reach vector database. Please try again later.")
    
    # 1. Embed question using same model as indexing
    try:
        query_vector = get_embedding(question)
    except Exception as e:
        logger.error(f"Failed to generate embedding: {str(e)}")
        raise Exception("Failed to process your query. Please try again.")
    
    # 2. Search Qdrant (top_k=5)
    try:
        search_result = client.query_points(
            collection_name=settings.COLLECTION_NAME,
            query=query_vector,
            using=settings.VECTOR_NAME,
            limit=5
        ).points
    except Exception as e:
        logger.error(f"Qdrant search failed: {str(e)}")
        raise Exception(f"Search service error: Unable to complete search. Please verify your connection and try again.")
    
    # 3. Construct Context & Extracted metadata
    context_lines = []
    products_metadata = []
    
    for hit in search_result:
        p = hit.payload
        
        # Extract fields for structured response
        name = p.get("name") or p.get("title") or "Unknown Product"
        raw_price = p.get("final_price") or p.get("price") or "N/A"
        raw_currency = p.get("currency", "")
        
        # Detect currency intelligently
        try:
            price_float = float(str(raw_price).replace(",", "")) if raw_price != "N/A" else 0
        except (ValueError, TypeError):
            price_float = 0
        
        # Auto-detect currency based on price value and metadata
        currency = "USD"  # default
        if raw_currency:
            raw_currency = str(raw_currency).upper().strip()
            if "IDR" in raw_currency or "Rp" in raw_currency:
                currency = "IDR"
            elif "DT" in raw_currency or "TND" in raw_currency:
                currency = "TND"
            elif "$" in raw_currency or "USD" in raw_currency:
                currency = "USD"
        else:
            # If no currency specified, guess based on price magnitude
            if price_float > 1000:
                currency = "IDR"  # Large numbers = IDR
            else:
                currency = "USD"  # Small numbers = USD
        
        availability = p.get("availability", "In Stock")
        image_url = p.get("image_url") or p.get("image") or ""
        description = p.get("description", "")[:250]
        
        # Convert price to TND for display
        if currency == "TND":
            price_tnd = price_float
            price = f"{price_float:,.2f} DT"
        else:
            try:
                price_tnd = convert_to_tnd(price_float, currency)
                price = f"{price_tnd:,.2f} DT"
            except Exception as e:
                logger.error(f"Price conversion error: {e}")
                price = f"{price_float:,.2f} {currency}"
                price_tnd = None
        
        url = p.get("url") or p.get("product_url") or p.get("link") or ""
        
        # Format for LLM Context - ONLY show TND price
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
            "price": price,  # Price in TND with DT symbol
            "price_numeric": price_tnd,  # Numeric TND price for sorting
            "availability": availability,
            "image_url": image_url,
            "url": url,
            "description": description
        })
            
    context = "\n\n".join(context_lines)
    
    # 4. Generate Expert Answer
    try:
        answer = query_llm(context, question)
    except Exception as e:
        logger.error(f"LLM query failed: {str(e)}")
        # Fallback response when LLM fails
        if not search_result:
            answer = f"I couldn't find relevant products for '{question}'. Please try a different search."
        else:
            product_names = [p["name"] for p in products_metadata]
            answer = f"Here are some products that might interest you:\n\n" + "\n".join([f"- {name}" for name in product_names[:3]])
    
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
