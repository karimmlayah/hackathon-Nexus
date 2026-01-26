from __future__ import annotations

import os
import pickle
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import base64

from dotenv import load_dotenv
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from data import PRODUCTS
from embedder import Embedder
from image_embedder import ImageEmbedder
from qdrant import (
    DEFAULT_COLLECTION_NAME,
    build_product_text,
    ensure_collection,
    get_collection_count,
    get_qdrant_client,
    search_products,
    upsert_products,
    get_stats,
)
from chatbot_service import ChatbotService


load_dotenv()  # Loads .env locally for development


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    
    logger = logging.getLogger("uvicorn")
    logger.info(f"🚀 Starting up... Loading {len(PRODUCTS)} products")
    
    # Initialize dependencies
    collection_name = os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION_NAME)
    logger.info("📦 Loading SentenceTransformer model...")
    embedder = Embedder(model_name="all-MiniLM-L6-v2")
    
    logger.info("🔌 Connecting to Qdrant Cloud...")
    client = get_qdrant_client()

    # Ensure collection exists
    logger.info(f"📊 Ensuring collection '{collection_name}' exists...")
    # Default to 'text_dense' for text search if using named vectors
    ensure_collection(
        client=client, 
        collection_name=collection_name, 
        vector_size=embedder.vector_size,
        vector_name="text_dense"
    )

    # Check if data is already in Qdrant
    existing_count = get_collection_count(client, collection_name)
    expected_count = len(PRODUCTS)
    
    if existing_count >= expected_count:
        logger.info(
            f"✅ Collection already has {existing_count} products. "
            f"Skipping embedding and upload (fast startup!)"
        )
    else:
        logger.info(
            f"📥 Collection has {existing_count} products, need to add {expected_count - existing_count}. "
            f"Starting embedding process..."
        )
        
        # Try to load pre-computed embeddings from Kaggle
        embeddings_file = os.path.join(os.path.dirname(__file__), "product_embeddings.pkl")
        vectors = None
        products_to_upload = PRODUCTS
        
        if os.path.exists(embeddings_file):
            logger.info(f"📂 Found pre-computed embeddings file: {embeddings_file}")
            logger.info("📥 Loading embeddings from file (fast!)...")
            try:
                with open(embeddings_file, "rb") as f:
                    saved_data = pickle.load(f)
                    vectors = saved_data.get("embeddings")
                    saved_products = saved_data.get("products")
                    
                    # Verify the products match
                    if saved_products and len(saved_products) == len(PRODUCTS):
                        logger.info("✅ Using pre-computed embeddings from Kaggle!")
                        products_to_upload = saved_products
                    else:
                        logger.warning(
                            f"⚠️  Product count mismatch. Saved: {len(saved_products) if saved_products else 0}, "
                            f"Current: {len(PRODUCTS)}. Will regenerate embeddings."
                        )
                        vectors = None
            except Exception as e:
                logger.warning(f"⚠️  Failed to load embeddings file: {e}. Will generate new embeddings.")
                vectors = None
        
        # Generate embeddings if not loaded from file
        if vectors is None:
            logger.info("🔄 Building product texts...")
            texts = [build_product_text(p) for p in PRODUCTS]
            
            logger.info(
                f"🧮 Generating embeddings for {len(texts)} products "
                f"(this may take a few minutes, only done once)..."
            )
            vectors = embedder.embed_texts(texts)
        
        logger.info(f"📤 Uploading {len(products_to_upload)} products to Qdrant Cloud...")
        upsert_products(
            client=client, 
            collection_name=collection_name, 
            products=products_to_upload, 
            vectors=vectors,
            vector_name="text_dense"
        )
        logger.info("✅ Products uploaded successfully!")
    
    logger.info("✅ Startup complete! API is ready.")

    # Initialize image embedder for multimodal search
    logger.info("🖼️  Loading CLIP model for image search...")
    try:
        image_embedder = ImageEmbedder()
        image_vector_size = image_embedder.vector_size
        text_vector_size = embedder.vector_size
        
        logger.info(f"✅ CLIP model loaded. Image vector size: {image_vector_size}")
        
        # Check compatibility
        if image_vector_size != text_vector_size:
            logger.warning(
                f"⚠️  Vector size mismatch: CLIP={image_vector_size}D, Text={text_vector_size}D. "
                f"Image search may not work. Consider re-encoding products with CLIP using reload_qdrant_clip.py"
            )
        else:
            logger.info("✅ Vector sizes match! Image search is ready.")
    except Exception as e:
        logger.warning(f"⚠️  Failed to load CLIP model: {e}. Image search will be disabled.")
        image_embedder = None

    # Store in app state
    app.state.qdrant_client = client
    app.state.embedder = embedder
    app.state.image_embedder = image_embedder
    app.state.collection_name = collection_name
    
    # Initialize Chatbot Service
    try:
        app.state.chatbot = ChatbotService(embedder)
        logger.info("✅ Chatbot Service initialized!")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Chatbot Service: {e}")
        app.state.chatbot = None

    yield


app = FastAPI(
    title="Smart Semantic Search API",
    version="1.0.0",
    description="Semantic (vector) search over products using Qdrant Cloud and SentenceTransformers.",
    lifespan=lifespan,
)

@app.get("/api/stats")
async def stats_endpoint():
    """
    Get aggregate stats for dashboard
    """
    client = get_qdrant_client()
    collection_name = os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION_NAME)
    stats = get_stats(client, collection_name)
    return stats

class ChatRequest(BaseModel):
    message: str
    currency: str = "USD"

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Chat with the RAG assistant
    """
    if not app.state.chatbot:
        raise HTTPException(status_code=503, detail="Chatbot service not available")
    
    response = await app.state.chatbot.get_response(request.message, request.currency)
    return response

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
def home():
    """Redirect to search interface"""
    return FileResponse("static/index.html")


@app.get("/shop.html", response_class=HTMLResponse)
def shop():
    """Serve shop page"""
    return FileResponse("static/shop.html")


@app.get("/{page}.html", response_class=HTMLResponse)
def serve_html_pages(page: str):
    """Serve other HTML pages from static directory"""
    import os
    file_path = f"static/{page}.html"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Page not found")


@app.get("/status/image-search")
def image_search_status():
    """Check if image search is available (CLIP model loaded and vectors compatible)"""
    if not app.state.image_embedder:
        return {
            "available": False,
            "reason": "CLIP model not loaded",
            "solution": "Restart the server to load CLIP model"
        }
    
    # Check vector size compatibility
    client = app.state.qdrant_client
    collection_name = app.state.collection_name
    
    try:
        collection_info = client.get_collection(collection_name)
        vectors_config = collection_info.config.params.vectors
        
        # Handle both named vectors (dict) and single vector configurations
        if isinstance(vectors_config, dict):
            # Try to get the specific vector size from 'image_dense' or fall back
            sample_vector = vectors_config.get("image_dense") or vectors_config.get("text_dense") or list(vectors_config.values())[0]
            collection_vector_size = sample_vector.size
        else:
            collection_vector_size = vectors_config.size
            
        image_vector_size = app.state.image_embedder.vector_size
        
        if image_vector_size != collection_vector_size:
            return {
                "available": False,
                "reason": f"Vector size mismatch: CLIP={image_vector_size}D, Collection={collection_vector_size}D",
                "solution": "Run: python reload_qdrant_clip.py",
                "image_vector_size": image_vector_size,
                "collection_vector_size": collection_vector_size
            }
        
        return {
            "available": True,
            "image_vector_size": image_vector_size,
            "collection_vector_size": collection_vector_size
        }
    except Exception as e:
        return {
            "available": False,
            "reason": str(e),
            "solution": "Check Qdrant connection"
        }




# =============================
# API
# =============================

@app.get("/products")
def list_products(
    limit: int = Query(12, ge=1, le=100, description="Number of products per page"),
    page: int = Query(1, ge=1, description="Page number"),
    category: str = Query(None, description="Filter by category"),
):
    """
    Get products from Qdrant with pagination & category filter
    """
    from qdrant_client.http import models
    from qdrant import map_qdrant_product
    import logging
    
    logger = logging.getLogger("uvicorn")
    client = app.state.qdrant_client
    collection = app.state.collection_name

    try:
        # Get total count
        collection_info = client.get_collection(collection)
        total_count = collection_info.points_count
        
        # Calculate offset for pagination
        offset = (page - 1) * limit
        
        # Scroll through Qdrant with offset
        results, _ = client.scroll(
            collection_name=collection,
            limit=limit,
            offset=offset,
            with_payload=True,
        )
        
        products = [map_qdrant_product(p) for p in results]
        
        # Filter by category after mapping if needed
        if category and category != "All Products":
            category_lower = category.lower()
            # Get more results for filtering
            all_results, _ = client.scroll(
                collection_name=collection,
                limit=limit * 10,
                with_payload=True,
            )
            all_products = [map_qdrant_product(p) for p in all_results]
            filtered = [
                p for p in all_products 
                if p.get("category", "").lower() == category_lower 
                or category_lower in p.get("category", "").lower()
                or p.get("category", "").lower() in category_lower
            ]
            total_count = len(filtered)
            products = filtered[offset:offset+limit]
        
        total_pages = (total_count + limit - 1) // limit

        return {
            "products": products,
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "limit": limit
        }

    except Exception as e:
        # =============================
        # Fallback CSV
        # =============================
        logger.error(f"❌ Qdrant error: {e}")

        filtered = PRODUCTS
        if category and category != "All Products":
            filtered = [
                p for p in PRODUCTS
                if category.lower() in (p.get("category") or "").lower()
            ]

        total_count = len(filtered)
        offset = (page - 1) * limit

        return {
            "products": filtered[offset:offset + limit],
            "total_count": total_count,
            "total_pages": (total_count + limit - 1) // limit,
            "current_page": page,
            "limit": limit
        }


@app.get("/search")
def search(
    q: str = Query(..., min_length=1, description="Natural language query"),
    limit: int = Query(30, ge=1, le=50, description="Number of results"),
    threshold: float = Query(0.3, ge=0.0, le=1.0, description="Minimum similarity score (0.0-1.0)"),
    mmr: bool = Query(False, description="Enable MMR for diverse results"),
):
    """
    Semantic search with optional MMR (Maximal Marginal Relevance).
    
    - **q**: Search query in any language
    - **limit**: Max number of results (1-20)
    - **threshold**: Minimum similarity score (e.g., 0.5 = 50% match)
    - **mmr**: Enable diversity mode (reduces similar results)
    
    Examples:
    - `/search?q=headphones` - Basic search
    - `/search?q=headphones&threshold=0.5` - Only results > 50% match
    - `/search?q=headphones&limit=10&threshold=0.6` - Top 10, min 60%
    - `/search?q=headphones&mmr=true` - Diverse results
    """
    embedder: Embedder = app.state.embedder
    client = app.state.qdrant_client
    
    # Use the unified collection for both text and image
    # containing 'text_dense' and 'image_dense' vectors
    collection_name = app.state.collection_name
    
    query_vector = embedder.embed_text(q)
    
    items = search_products(
        client=client,
        collection_name=collection_name,
        query_vector=query_vector,
        limit=limit,
        score_threshold=threshold,
        use_mmr=mmr,
        vector_name="text_dense", # Use explicit text vector
    )
    return {
        "query": q,
        "results": items,
        "mmr_enabled": mmr,
        "threshold": threshold,
        "count": len(items),
    }


class ImageSearchRequest(BaseModel):
    """Request model for image search using base64."""
    image_base64: str  # Base64 encoded image
    limit: int = 30
    threshold: float = 0.3
    mmr: bool = False


@app.post("/search/image")
async def search_by_image(request: ImageSearchRequest):
    """
    Multimodal search: find products similar to an uploaded image.
    Uses 'nexus-multivector_3k_f' collection with 'image_dense' vector.
    """
    if not app.state.image_embedder:
        raise HTTPException(
            status_code=503,
            detail="Image search not available. CLIP model not loaded. Check server logs."
        )
    
    # Decode base64 image
    try:
        # Remove data URL prefix if present
        image_data = request.image_base64
        if "," in image_data:
            image_data = image_data.split(",")[1]
        image_bytes = base64.b64decode(image_data)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to decode image: {str(e)}"
        )
    
    # Encode image with CLIP
    image_embedder: ImageEmbedder = app.state.image_embedder
    try:
        query_vector = image_embedder.embed_image_from_bytes(image_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process image: {str(e)}"
        )
    
    client = app.state.qdrant_client
    # Use the unified collection
    collection_name = app.state.collection_name
    
    # Check vector size compatibility (optional log, but good for debug)
    # image_vector_size = len(query_vector) # Should be 512
    
    # Search with image vector in the unified collection
    items = search_products(
        client=client,
        collection_name=collection_name,
        query_vector=query_vector,
        limit=request.limit,
        score_threshold=request.threshold,
        use_mmr=request.mmr,
        vector_name="image_dense", # Use 'image_dense' vector for image search
    )
    
    # Data is already in the payload (title, final_price, etc.)
    # The map_qdrant_product function handles mapping these fields to standard keys
    
    return {
        "query": "Image search",
        "results": items,
        "mmr_enabled": request.mmr,
        "threshold": request.threshold,
        "count": len(items),
        "search_type": "image",
    }

