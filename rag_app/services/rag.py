from qdrant_client.http import models
from qdrant_client import QdrantClient
import sys
import os

# Add root and rag_app to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)
RAG_APP_DIR = os.path.join(ROOT_DIR, "rag_app")
sys.path.insert(0, RAG_APP_DIR)

from core.database import get_qdrant_client
from core.config import settings
from core.llm import get_embedding, query_llm
from core.currency import convert_to_tnd, format_price_tnd, detect_currency
import logging

try:
    from image_embedder import ImageEmbedder
    import base64
    from PIL import Image
    import io
    import numpy as np
except ImportError as e:
    logging.getLogger(__name__).error(f"Failed to import multimodal dependencies: {e}")

logger = logging.getLogger(__name__)

# Initialize CLIP model for multimodal search
try:
    clip_embedder = ImageEmbedder("clip-ViT-B-32")
    logger.info("✅ CLIP embedder initialized for multimodal search")
except Exception as e:
    logger.error(f"Failed to initialize CLIP embedder: {str(e)}")
    clip_embedder = None

async def multimodal_search_and_answer(
    question: str = None, 
    image_base64: str = None, 
    production_mode: bool = False, 
    limit: int = 12
):
    """
    Multimodal RAG pipeline: Handles text, image, or both.
    Uses 'image_dense' vector (CLIP) for searching.
    """
    try:
        client = get_qdrant_client()
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {str(e)}")
        raise Exception("Database connection error")

    # 1. Generate Combined Query Vector
    query_vectors = []
    
    # Text contribution (via CLIP)
    if question and clip_embedder:
        try:
            # clip_embedder uses sentence_transformers which encodes text too
            text_vec = clip_embedder.model.encode(
                question, 
                convert_to_numpy=True, 
                normalize_embeddings=True
            )
            query_vectors.append(text_vec)
        except Exception as e:
            logger.error(f"Text encoding error (multimodal): {e}")

    # Image contribution
    if image_base64 and clip_embedder:
        try:
            # Handle data URL prefix if present
            if "," in image_base64:
                image_base64 = image_base64.split(",")[1]
            
            image_bytes = base64.b64decode(image_base64)
            img_vec = clip_embedder.embed_image_from_bytes(image_bytes)
            query_vectors.append(np.array(img_vec))
        except Exception as e:
            logger.error(f"Image encoding error: {e}")

    if not query_vectors:
        # Fallback to standard text search if no clip or failed encoding
        if question:
            return await search_and_answer(question, production_mode, limit)
        raise Exception("No valid search query provided")

    # Average vectors if multimodal
    if len(query_vectors) > 1:
        final_query_vector = np.mean(query_vectors, axis=0)
        # Re-normalize
        final_query_vector = final_query_vector / np.linalg.norm(final_query_vector)
    else:
        final_query_vector = query_vectors[0]

    # 2. Search Qdrant using 'image_dense'
    try:
        search_result = client.query_points(
            collection_name=settings.COLLECTION_NAME,
            query=final_query_vector.tolist(),
            using="image_dense", # Specified by user
            limit=limit
        ).points
    except Exception as e:
        logger.error(f"Multimodal search failed: {str(e)}")
        # If image_dense fails, fallback to text_dense if possible
        if question:
             return await search_and_answer(question, production_mode, limit)
        raise Exception(f"Search service error: {str(e)}")

    # 3. Construct Context & Results
    products_metadata = []
    
    for hit in search_result:
        p = hit.payload
        name = p.get("name") or p.get("title") or "Unknown Product"
        raw_price = p.get("final_price") or p.get("price") or 0
        raw_currency = p.get("currency", "")
        
        # Try to extract a numeric price for sorting
        try:
            if isinstance(raw_price, str):
                price_numeric = float(raw_price.replace(",", "").replace("$", "").strip())
            else:
                price_numeric = float(raw_price)
        except:
            price_numeric = 0.0

        availability = p.get("availability", "In Stock")
        image_url = p.get("image_url") or p.get("image") or (p.get("image_urls", [""])[0] if p.get("image_urls") else "")
        description = p.get("description", "")[:250]
        url = p.get("url") or p.get("product_url") or p.get("amazon_url") or "#"
        
        products_metadata.append({
            "name": name,
            "price": f"{price_numeric:,.2f} {raw_currency}".strip() or f"{price_numeric:,.2f} USD",
            "price_numeric": price_numeric,
            "availability": availability,
            "image_url": image_url,
            "image": image_url,
            "url": url,
            "description": description,
            "score": hit.score
        })

    # 4. Handle Price Sorting Intent
    if question:
        q_lower = question.lower()
        if any(word in q_lower for word in ["cheapest", "lowest price", "cheap", "expensive", "highest price"]):
            reverse = any(word in q_lower for word in ["expensive", "highest price"])
            # Sort by price_numeric
            products_metadata.sort(key=lambda x: x["price_numeric"], reverse=reverse)
            logger.info(f"Sorted results by price (reverse={reverse}) due to intent in: {question}")

    # Create context from (possibly sorted) metadata
    context_lines = [f"- {p['name']} ({p['price']}): {p['description']}" for p in products_metadata]
    context = "\n\n".join(context_lines)
    
    # 5. Generate Answer (if text provided)
    answer = ""
    if question:
        try:
            answer = query_llm(context, question)
        except:
            answer = "I found some products based on your search."
    else:
        answer = "Here are the closest items found based on your image search."

    return {
        "answer": answer,
        "products": products_metadata,
        "results": products_metadata,
        "count": len(products_metadata)
    }

async def search_and_answer(question: str, production_mode: bool = False, limit: int = 12):
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
    
    # 2. Search Qdrant
    try:
        search_result = client.query_points(
            collection_name=settings.COLLECTION_NAME,
            query=query_vector,
            using=settings.VECTOR_NAME,
            limit=limit
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
            "image": image_url, # Frontend compatibility
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

    # 5. Handle Price Sorting Intent
    q_lower = question.lower()
    if any(word in q_lower for word in ["cheapest", "lowest price", "cheap", "expensive", "highest price"]):
        reverse = any(word in q_lower for word in ["expensive", "highest price"])
        # Sort by price_numeric
        products_metadata.sort(key=lambda x: x.get("price_numeric", 0) or 0, reverse=reverse)
        logger.info(f"Sorted text results by price (reverse={reverse}) due to intent in: {question}")

    if production_mode:
        return {
            "answer": answer,
            "products": products_metadata,
            "results": products_metadata, # Frontend compatibility
            "count": len(products_metadata) # Frontend compatibility
        }
    
    # Legacy support
    return {
        "answer": answer,
        "sources": [p["name"] for p in products_metadata],
        "images": [p["image_url"] for p in products_metadata if p["image_url"]],
        "context": context_lines
    }
