from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
import os
from pydantic import BaseModel

# Add current directory to path to allow relative imports
sys.path.insert(0, os.path.dirname(__file__))

from core.config import settings
from core.database import get_qdrant_client, ensure_collection
from core.llm import groq_client
from core.currency import convert_to_tnd, format_price_tnd
from api import routes

logger = logging.getLogger("uvicorn")

# --- AUTH SCHEMAS ---
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = None

class LoginRequest(BaseModel):
    email: str
    password: str

# Demo users with roles
DEMO_USERS = {
    "admin@finfit.com": {
        "password": "admin123",
        "name": "Admin User",
        "role": "super_admin",  # Super admin role
        "email": "admin@finfit.com"
    },
    "user@finfit.com": {
        "password": "user123",
        "name": "Regular User",
        "role": "user",  # Regular user role
        "email": "user@finfit.com"
    },
    "test@example.com": {
        "password": "test123",
        "name": "Test User",
        "role": "user",
        "email": "test@example.com"
    }
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize and verify connections
    logger.info("🚀 Starting RAG Application...")
    
    # Verify Qdrant connection
    try:
        client = get_qdrant_client()
        ensure_collection(vector_size=384)
        logger.info("✅ Qdrant connection verified")
    except Exception as e:
        logger.error(f"⚠️ Warning: Qdrant connection failed. Limited functionality: {str(e)}")
    
    # Verify Groq API key
    if not settings.GROQ_API_KEY or groq_client is None:
        logger.error("⚠️ Warning: Groq API not configured. LLM features will not work.")
    else:
        logger.info("✅ Groq API configured")
    
    logger.info("🎯 RAG Application ready!")
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files FIRST (before all routes) - CSS, JS, images, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routes with /api prefix
app.include_router(routes.router, prefix="/api")

# Legacy search endpoints (for backward compatibility with frontend)
@app.post("/search")
async def legacy_search(user_query: str, limit: int = 12):
    """Legacy search endpoint that forwards to /api/search"""
    from api.routes import SearchRequest
    request = SearchRequest(user_query=user_query, limit=limit)
    return await routes.production_search(request)

@app.get("/search")
async def legacy_search_get(q: str, limit: int = 12):
    """Legacy GET search endpoint"""
    from api.routes import SearchRequest
    request = SearchRequest(user_query=q, limit=limit)
    return await routes.production_search(request)

@app.post("/search/image")
async def legacy_search_image(request: routes.SearchRequest):
    """Legacy image search endpoint that forwards to /api/search/image"""
    return await routes.production_search(request)

@app.get("/status/image-search")
async def image_search_status():
    """Check status of image search service"""
    return {
        "status": "unavailable",
        "message": "Image search service is not available",
        "available": False
    }

# Auth endpoints (placeholder - frontend calls these)
@app.post("/api/register")
async def register(request: RegisterRequest):
    """User registration endpoint"""
    return {
        "success": True,
        "message": "Registration feature coming soon",
        "token": "dummy_token_123",
        "user": {"email": request.email, "name": request.name}
    }

@app.post("/api/login")
async def login(request: LoginRequest):
    """
    User login endpoint with role-based access.
    
    Demo credentials:
    - admin@finfit.com / admin123 → super_admin (goes to dashboard)
    - user@finfit.com / user123 → user (goes to e-commerce)
    - test@example.com / test123 → user
    """
    # Check if user exists
    user = DEMO_USERS.get(request.email)
    
    if not user or user["password"] != request.password:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    # Generate a dummy token (in production, use JWT)
    import hashlib
    token = hashlib.sha256(f"{request.email}{user['role']}".encode()).hexdigest()[:32]
    
    return {
        "success": True,
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "name": user["name"],
            "role": user["role"]  # Return the role
        }
    }

# Health check endpoint
@app.get("/health")
def health_check():
    """
    Health check endpoint to verify service connectivity.
    Returns the status of Qdrant and Groq connections.
    """
    status = {
        "status": "healthy",
        "qdrant": "unknown",
        "groq": "unknown",
    }
    
    # Check Qdrant
    try:
        client = get_qdrant_client()
        client.get_collections()
        status["qdrant"] = "connected"
    except Exception as e:
        status["qdrant"] = f"disconnected: {str(e)}"
        status["status"] = "degraded"
    
    # Check Groq
    if groq_client is not None:
        status["groq"] = "configured"
    else:
        status["groq"] = "not configured"
        status["status"] = "degraded"
    
    status_code = 200 if status["status"] == "healthy" else 503
    return JSONResponse(content=status, status_code=status_code)

@app.get("/api/users")
async def get_users():
    """Get all registered users (excluding passwords)"""
    return {
        "success": True,
        "users": [
            {
                "email": user["email"],
                "name": user["name"],
                "role": user["role"]
            }
            for user in DEMO_USERS.values()
        ]
    }

@app.get("/api/dashboard/widgets")
async def get_dashboard_widgets():
    """Get data for dashboard widgets: top products and user stats"""
    try:
        # 1. User stats
        user_counts = {"user": 0, "super_admin": 0, "admin": 0}
        for user in DEMO_USERS.values():
            role = user.get("role", "user")
            user_counts[role] = user_counts.get(role, 0) + 1
        
        # 2. Top Products (by rating)
        client = get_qdrant_client()
        collection_name = settings.COLLECTION_NAME
        
        # Scroll a larger sample to find best rated (Qdrant doesn't support complex sort on payload as easily as SQL)
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=50,
            with_payload=True,
            with_vectors=False
        )
        
        all_products = []
        for point in points:
            payload = point.payload
            
            # Extract and convert price (reusing logic from get_products)
            raw_price = payload.get("price") or payload.get("final_price") or 0
            raw_currency = payload.get("currency", "USD")
            
            try:
                price_float = float(str(raw_price).replace(",", "")) if raw_price else 0
            except (ValueError, TypeError):
                price_float = 0
                
            # Convert to TND
            price_tnd_str = "N/A"
            if price_float > 0:
                try:
                    # Basic detection logic matches get_products
                    if "IDR" in str(raw_currency).upper() or price_float > 1000:
                        price_tnd = convert_to_tnd(price_float, "IDR")
                    elif "TND" in str(raw_currency).upper() or "DT" in str(raw_currency).upper():
                        price_tnd = price_float
                    else:
                        price_tnd = convert_to_tnd(price_float, "USD")
                    
                    price_tnd_str = f"{price_tnd:,.2f} DT"
                except:
                    price_tnd_str = f"{raw_price} {raw_currency}"

            all_products.append({
                "id": str(point.id),
                "name": payload.get("name") or payload.get("title") or "Unknown Product",
                "rating": float(payload.get("rating") or 0),
                "price": price_tnd_str,
                "image": payload.get("image_url") or payload.get("image") or "/static/img/placeholder.png",
                "category": payload.get("category", "General")
            })
        
        # Sort by rating and take top 5
        top_products = sorted(all_products, key=lambda x: x["rating"], reverse=True)[:5]
        
        return {
            "success": True,
            "user_stats": {
                "super_users": user_counts.get("super_admin", 0),
                "admins": user_counts.get("admin", 0),
                "regular_users": user_counts.get("user", 0),
                "total_users": sum(user_counts.values())
            },
            "top_products": top_products
        }
    except Exception as e:
        logger.error(f"Widget data error: {str(e)}")
        return {"success": False, "error": str(e)}

# Products endpoint - returns products from Qdrant
@app.get("/products")
def get_products(limit: int = 12, category: str = None, page: int = 1):
    """
    Get products from Qdrant vector database with pagination support.
    
    Parameters:
    - limit: Number of products to return per page (default 12)
    - category: Optional category filter (Electronics, Fashion, etc.)
    - page: Page number for pagination (default 1)
    """
    try:
        client = get_qdrant_client()
        collection_name = settings.COLLECTION_NAME
        
        # Calculate offset for pagination
        offset = (page - 1) * limit
        
        # Fetch products from Qdrant
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        products = []
        for point in points:
            payload = point.payload
            
            # Filter by category if provided
            if category and category.lower() != "all":
                product_category = payload.get("category", "").lower()
                if category.lower() not in product_category:
                    continue
            
            # Extract and convert price
            raw_price = payload.get("price") or payload.get("final_price") or "N/A"
            raw_currency = payload.get("currency", "")
            
            # Detect currency intelligently
            try:
                price_float = float(str(raw_price).replace(",", "")) if raw_price != "N/A" else 0
            except (ValueError, TypeError):
                price_float = 0
            
            # Auto-detect currency
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
            
            # Convert to TND
            if currency == "TND":
                price_tnd = price_float
                price_tnd_str = f"{price_float:,.2f} DT"
            else:
                try:
                    price_tnd = convert_to_tnd(price_float, currency)
                    price_tnd_str = f"{price_tnd:,.2f} DT"
                except (ValueError, TypeError):
                    price_tnd = None
                    price_tnd_str = f"{raw_price} {currency}"
            
            product = {
                "id": point.id,
                "title": payload.get("name") or payload.get("title") or "Unknown Product",  # Both 'name' and 'title'
                "name": payload.get("name") or payload.get("title") or "Unknown Product",
                "price": price_tnd_str,  # Display in TND
                "price_original": f"{raw_price} {currency}",  # Original price for reference
                "price_numeric": price_tnd,  # Numeric value for sorting
                "currency": "TND",  # Display currency is now TND
                "image": payload.get("image_url") or payload.get("image") or "/static/img/placeholder.png",
                "availability": payload.get("availability", "In Stock"),
                "category": payload.get("category", "General"),
                "description": payload.get("description", "")[:200] if payload.get("description") else "",
                "rating": payload.get("rating") or 4.5,
                "url": payload.get("url") or payload.get("product_url") or "#"
            }
            products.append(product)
        
        # Ensure we return exactly the requested limit (or less if fewer available)
        products = products[:limit]
        
        # Calculate total pages (approximate, based on collection size)
        collection_info = client.get_collection(collection_name)
        total_products = collection_info.points_count
        total_pages = (total_products + limit - 1) // limit  # Ceiling division
        
        return {
            "success": True,
            "count": len(products),
            "products": products,
            "current_page": page,
            "total_pages": total_pages,
            "total_products": total_products
        }
    except Exception as e:
        logger.error(f"Error fetching products: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "products": [],
            "current_page": page,
            "total_pages": 1,
            "total_products": 0
        }

@app.get("/")
def read_root():
    """Serve index.html for root path"""
    return FileResponse("static/index.html")

# Proxy to Next.js dashboard server
@app.api_route("/dashboard", methods=["GET"])
@app.api_route("/dashboard/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_dashboard(path: str = "", request: Request = None):
    """Proxy requests to Next.js server on port 3000"""
    import httpx
    
    try:
        # Construct the target URL
        target_url = f"http://127.0.0.1:3000/dashboard/{path}" if path else "http://127.0.0.1:3000/"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=request.headers,
                content=await request.body()
            )
            return Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))
    except Exception as e:
        logger.error(f"Proxy error: {str(e)}")
        raise HTTPException(status_code=503, detail="Dashboard service unavailable")

# Catch-all route for serving HTML pages (must be AFTER static mount and BEFORE more specific routes)
@app.get("/{path:path}")
async def serve_page(path: str):
    """
    Serve HTML pages from the static directory.
    If the requested file exists as .html, serve it.
    Otherwise, check if it's a static asset.
    """
    import os
    
    # Don't intercept /api routes (let router handle them)
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    
    # Try to serve the requested file as-is
    file_path = f"static/{path}"
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Try adding .html extension
    if os.path.isfile(f"{file_path}.html"):
        return FileResponse(f"{file_path}.html")
    
    # Default to index.html for SPA-like behavior
    if os.path.isfile("static/index.html") and "." not in path:
        return FileResponse("static/index.html")
    
    # Return 404 if nothing found
    raise HTTPException(status_code=404, detail="Not Found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
