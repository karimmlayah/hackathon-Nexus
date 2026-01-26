from __future__ import annotations

import ast
import json
import os
import re
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams, NearestQuery, Mmr


DEFAULT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "products")


def get_qdrant_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "").strip()
    api_key = os.getenv("QDRANT_API_KEY", "").strip()

    if not url or not api_key:
        raise RuntimeError(
            "Missing Qdrant Cloud credentials. Please set QDRANT_URL and QDRANT_API_KEY."
        )

    # QdrantClient auto-detects REST; HTTPS URL is expected for Qdrant Cloud.
    return QdrantClient(url=url, api_key=api_key, prefer_grpc=False)


def ensure_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int,
    distance: Distance = Distance.COSINE,
    vector_name: Optional[str] = None,
) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if collection_name in existing:
        return

    if vector_name:
        vectors_config = {vector_name: VectorParams(size=vector_size, distance=distance)}
    else:
        vectors_config = VectorParams(size=vector_size, distance=distance)

    client.create_collection(
        collection_name=collection_name,
        vectors_config=vectors_config,
    )


def get_collection_count(client: QdrantClient, collection_name: str) -> int:
    """Get the number of points in a collection."""
    try:
        collection_info = client.get_collection(collection_name)
        return collection_info.points_count
    except Exception:
        return 0


def build_product_text(product: Dict[str, Any]) -> str:
    # Combine fields to improve semantic matching.
    # Keeping category & name helps cross-lingual queries find the right intent.
    breadcrumbs = product.get("breadcrumbs") or []
    if isinstance(breadcrumbs, list):
        breadcrumbs_text = " > ".join([str(b) for b in breadcrumbs][:5])
    else:
        breadcrumbs_text = str(breadcrumbs)

    features = product.get("features") or []
    if isinstance(features, list):
        features_text = "; ".join([str(f) for f in features][:5])
    else:
        features_text = str(features)

    return "\n".join(
        [
            str(product.get("name", "")),
            str(product.get("brand", "")),
            str(product.get("description", "")),
            str(product.get("category", "")),
            breadcrumbs_text,
            features_text,
            str(product.get("material", "")),
            str(product.get("color", "")),
            str(product.get("style", "")),
            str(product.get("size", "")),
        ]
    ).strip()


def upsert_products(
    client: QdrantClient,
    collection_name: str,
    products: List[Dict[str, Any]],
    vectors: List[List[float]],
    vector_name: Optional[str] = None,
) -> None:
    if len(products) != len(vectors):
        raise ValueError("Products count does not match vectors count.")

    points: List[PointStruct] = []
    for product, vector in zip(products, vectors, strict=True):
        # Convert ID to int if it's numeric, otherwise use hash for string IDs
        product_id = product["id"]
        try:
            # Try to convert to int if it's numeric
            pid = int(product_id) if isinstance(product_id, (int, float)) else int(product_id)
        except (ValueError, TypeError):
            # For string IDs (like Amazon SKUs), use hash to create unique int
            pid = abs(hash(str(product_id))) % (10**18)  # Keep within int64 range
        
        payload = {
            "id": str(product_id),  # Keep original ID as string in payload
            "name": product.get("name"),
            "description": product.get("description"),
            "categories": product.get("categories"),  # Store categories list/string
            "category": product.get("category"),  # Store single category for compatibility
            "nodeName": product.get("nodeName") or product.get("category"),  # Store nodeName for category extraction
            "price": float(product.get("price") or 0.0),
            "listed_price": float(product.get("listed_price") or 0.0),
            "sale_price": float(product.get("sale_price") or 0.0),
            "currency": product.get("currency"),
            "brand": product.get("brand"),
            "rating": product.get("rating"),
            "review_count": product.get("review_count"),
            "breadcrumbs": product.get("breadcrumbs"),
            "color": product.get("color"),
            "features": product.get("features"),
            "material": product.get("material"),
            "mpn": product.get("mpn"),
            "gtin": product.get("gtin"),
            "size": product.get("size"),
            "style": product.get("style"),
            "weight": product.get("weight"),
            "in_stock": product.get("in_stock"),
            "variants": product.get("variants"),
            "current_depth": product.get("current_depth"),
            "new_path": product.get("new_path"),
            "additional_properties": product.get("additional_properties"),
            "image_urls": product.get("image_urls"),
            "url": product.get("url"),
        }
        if vector_name:
            vector_data = {vector_name: vector}
        else:
            vector_data = vector

        points.append(PointStruct(id=pid, vector=vector_data, payload=payload))

    client.upsert(collection_name=collection_name, points=points)


def map_qdrant_product(point: Any) -> Dict[str, Any]:
    """Robustly map a Qdrant point/payload to a product dictionary."""
    payload = point.payload or {}
    
    # 1. Map Title/Name - handle empty strings and diverse keys
    name = (
        payload.get("name") or 
        payload.get("title") or 
        payload.get("itemName") or 
        payload.get("product_name") or
        ""
    )
    
    # If name is still empty, try to get it from 'brand' if brand is long
    brand_raw = payload.get("brand") or payload.get("brandName") or ""
    if not name and len(brand_raw) > 20:
        name = brand_raw
        brand_display = ""
    else:
        brand_display = brand_raw
        
    # Final fallback for name
    if not name:
        name = f"Product {payload.get('row_id', point.id)}"

    # 2. Map Price
    price_val = 0.0
    # Added 'final_price' for the new collection schema
    for p_field in ["final_price", "price", "salePrice", "sale_price", "listedPrice", "listed_price", "currentPrice"]:
        val = payload.get(p_field)
        if val and val != "":
            try:
                # Handle formatted prices like "$19.99" or "19.99"
                val_str = str(val).replace("$", "").replace(",", "").strip()
                price_val = float(val_str)
                if price_val > 0: break
            except: continue
    
    # 3. Handle Images
    # Use 'image' first as it's the specific key in the user's example
    image_field = (
        payload.get("image") or
        payload.get("image_url") or 
        payload.get("imageUrls") or 
        payload.get("images") or 
        payload.get("image_urls")
    )
    
    image_urls = []
    if isinstance(image_field, list):
        image_urls = [str(url) for url in image_field if url]
    elif isinstance(image_field, str) and image_field.strip():
        trim_image = image_field.strip()
        # Handle cases where the string might be a JSON-encoded list or comma-separated
        if trim_image.startswith("["):
            try:
                # Handle potential formatting issues in JSON string
                clean_json = trim_image.replace("'", '"')
                parsed = json.loads(clean_json)
                if isinstance(parsed, list):
                    image_urls = [str(url) for url in parsed if url]
                else:
                    image_urls = [str(parsed)]
            except:
                # Regex fallback for URLs if JSON parsing fails
                image_urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', trim_image)
        elif "," in trim_image:
            image_urls = [u.strip() for u in trim_image.split(",") if u.strip()]
        else:
            image_urls = [trim_image]
    
    # Final image cleanup (remove potential brackets/quotes/dots if they slipped through)
    image_urls = [url.strip(' ."\'[]') for url in image_urls if "http" in str(url)]
    image_single = image_urls[0] if image_urls else None
    
    # 4. Map Description
    description = payload.get("description") or payload.get("descriptionRaw") or ""
    if not description or len(str(description)) < 20:
        desc_fallback = payload.get("features") or payload.get("about_this_item") or ""
        if isinstance(desc_fallback, list):
            description = " ".join([str(d) for d in desc_fallback])
        elif isinstance(desc_fallback, str) and desc_fallback.startswith("["):
             try:
                parsed = json.loads(desc_fallback.replace("'", '"'))
                description = " ".join(parsed) if isinstance(parsed, list) else str(parsed)
             except:
                description = str(desc_fallback).strip('[]"\' ')
        else:
            description = str(desc_fallback)
    
    # Map rating and review count
    # Handle rating being a string "3.5" or number
    rating_raw = payload.get("rating")
    rating = 0.0
    if rating_raw:
        try:
            rating = float(str(rating_raw).strip())
        except: pass
        
    review_count = payload.get("reviewCount") or payload.get("reviews_count") or payload.get("review_count")

    # Map initial price if available
    initial_price_val = 0.0
    for p_field in ["initial_price", "original_price", "listedPrice", "listed_price", "compare_at_price"]:
        val = payload.get(p_field)
        if val and val != "":
            try:
                val_str = str(val).replace("$", "").replace(",", "").strip()
                initial_price_val = float(val_str)
                if initial_price_val > 0: break
            except: continue

    # 5. Map Category - try multiple sources
    category = None
    
    # First, try to parse 'categories' field (can be a list or string-formatted list)
    categories_field = payload.get("categories")
    if categories_field:
        categories_list = None
        if isinstance(categories_field, list):
            categories_list = categories_field
        elif isinstance(categories_field, str) and categories_field.strip():
            # Try to parse string-formatted list like "['Health & Household', 'Household Supplies', ...]"
            try:
                # Try JSON first (if it's JSON format)
                if categories_field.strip().startswith('['):
                    # Try ast.literal_eval for Python list format
                    try:
                        categories_list = ast.literal_eval(categories_field)
                    except:
                        # Try JSON parsing
                        try:
                            # Replace single quotes with double quotes for JSON
                            json_str = categories_field.replace("'", '"')
                            categories_list = json.loads(json_str)
                        except:
                            # Fallback: split by comma if it's a simple comma-separated string
                            categories_list = [c.strip().strip("'\"") for c in categories_field.split(",") if c.strip()]
            except:
                # If parsing fails, try simple split
                if "," in categories_field:
                    categories_list = [c.strip().strip("'\"[]") for c in categories_field.split(",") if c.strip()]
        
        # Extract the most specific category (last in list) or first if only one
        if categories_list and len(categories_list) > 0:
            # Take the last category (most specific) or first if it's a single-item list
            category = str(categories_list[-1]).strip() if len(categories_list) > 1 else str(categories_list[0]).strip()
    
    # If no category from 'categories' field, try direct 'category' field
    if not category or not category.strip() or category.lower() == "uncategorized":
        category = payload.get("category")
        if category and str(category).strip() and str(category).strip().lower() != "uncategorized":
            category = str(category).strip()
        else:
            # Try nodeName (as used in data.py)
            node_name = payload.get("nodeName")
            if node_name and str(node_name).strip():
                category = str(node_name).strip()
            else:
                # Try to extract from breadcrumbs
                breadcrumbs = payload.get("breadcrumbs")
                if breadcrumbs:
                    if isinstance(breadcrumbs, list) and len(breadcrumbs) > 0:
                        # Get the last breadcrumb (most specific category)
                        last_breadcrumb = breadcrumbs[-1]
                        if isinstance(last_breadcrumb, dict):
                            category = last_breadcrumb.get("name") or str(last_breadcrumb)
                        else:
                            category = str(last_breadcrumb)
                    elif isinstance(breadcrumbs, str) and breadcrumbs.strip():
                        # Try to parse breadcrumb string
                        parts = [p.strip() for p in breadcrumbs.split(">") if p.strip()]
                        if parts:
                            category = parts[-1]  # Last part is usually the category
                
                # If still no category, try new_path
                if not category or not category.strip():
                    new_path = payload.get("new_path")
                    if new_path and isinstance(new_path, str):
                        # Extract category from path (e.g., "Electronics > Computers > Laptops")
                        path_parts = [p.strip() for p in new_path.split(">") if p.strip()]
                        if path_parts:
                            category = path_parts[-1]  # Last part is the category
                
                # Final fallback: try to infer from product name
                if not category or not category.strip():
                    name_lower = name.lower()
                    # Simple keyword matching for common categories
                    if any(kw in name_lower for kw in ["phone", "smartphone", "mobile", "tablet"]):
                        category = "Mobiles & Tablets"
                    elif any(kw in name_lower for kw in ["laptop", "computer", "desktop", "pc", "monitor"]):
                        category = "Computers"
                    elif any(kw in name_lower for kw in ["tv", "television", "screen", "display"]):
                        category = "Electronics"
                    elif any(kw in name_lower for kw in ["headphone", "speaker", "audio", "sound"]):
                        category = "Electronics"
                    elif any(kw in name_lower for kw in ["camera", "photo", "video", "recorder"]):
                        category = "Electronics"
                    else:
                        category = "Uncategorized"
    
    # Clean up category
    if not category or not str(category).strip():
        category = "Uncategorized"
    else:
        category = str(category).strip()

    return {
        "id": payload.get("id", payload.get("row_id", point.id)),
        "name": name,
        "description": description,
        "category": category,
        "price": price_val,
        "initial_price": initial_price_val,
        "currency": payload.get("currency") or "$",
        "score": float(point.score) if hasattr(point, "score") and point.score is not None else 0.0,
        "brand": brand_display,
        "rating": rating,
        "review_count": review_count,
        "image_urls": image_urls,
        "image": image_single,
        "url": payload.get("url"),
        "discount": payload.get("discount"),
    }


def search_products(
    client: QdrantClient,
    collection_name: str,
    query_vector: List[float],
    limit: int = 5,
    score_threshold: Optional[float] = None,
    use_mmr: bool = False,
    mmr_diversity: float = 0.5,
    vector_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search products with optional MMR for diversity.
    
    Args:
        use_mmr: Enable Maximal Marginal Relevance for diverse results
        mmr_diversity: Diversity score (0.0 to 1.0). Default 0.5
                      Higher = more diversity, Lower = more relevance
    """
    if use_mmr:
        # Use MMR for diverse results
        # Create Mmr object with diversity parameter
        mmr_config = Mmr(
            diversity=mmr_diversity,  # 0.5 = balanced, 1.0 = max diversity, 0.0 = no diversity
            candidates_limit=limit * 3  # Fetch 3x more candidates for MMR selection
        )
        
        # If vector_name is provided, we must use NamedVector in the query
        query = NearestQuery(
            nearest=query_vector,
            mmr=mmr_config
        )
        response = client.query_points(
            collection_name=collection_name,
            query=query,
            using=vector_name, # Specify vector name here if provided
            limit=limit,
            with_payload=True,
            score_threshold=score_threshold,
        )
    else:
        # Standard vector search (most similar)
        # In query_points, if vector_name is used, we pass a list of floats to 'query' 
        # but must specify 'using' parameter
        response = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            using=vector_name,
            limit=limit,
            with_payload=True,
            score_threshold=score_threshold,
        )

    items: List[Dict[str, Any]] = [map_qdrant_product(p) for p in response.points]
    
    # Apply brand diversity if MMR is enabled
    if use_mmr and len(items) > 1:
        items = rerank_by_brand_diversity(items)
    
    return items


def rerank_by_brand_diversity(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Re-rank results to maximize brand diversity while maintaining score order.
    At each step, picks the HIGHEST-scoring item with a brand different from the last.
    """
    if len(items) <= 1:
        return items
    
    reranked = []
    remaining = items.copy()
    last_brand = None
    
    while remaining:
        # Find the BEST (highest score) item with a different brand than the last one
        best_item = None
        best_idx = -1
        best_score = -1
        
        for idx, item in enumerate(remaining):
            brand = item.get("brand", "").strip().lower()
            if not brand:
                brand = "unknown"
            
            score = item.get("score", 0)
            
            # Pick this item if it has a different brand AND higher score
            if brand != last_brand:
                if best_item is None or score > best_score:
                    best_item = item
                    best_idx = idx
                    best_score = score
        
        # If all remaining items have the same brand as last, take the highest-scoring one
        if best_item is None:
            best_idx = 0
            best_score = remaining[0].get("score", 0)
            for idx, item in enumerate(remaining):
                if item.get("score", 0) > best_score:
                    best_idx = idx
                    best_score = item.get("score", 0)
            best_item = remaining[best_idx]
        
        # Add to results and update state
        reranked.append(best_item)
        last_brand = best_item.get("brand", "").strip().lower()
        if not last_brand:
            last_brand = "unknown"
        remaining.pop(best_idx)
    
    return reranked


def get_stats(client: QdrantClient, collection_name: str) -> Dict[str, Any]:
    """Get aggregate statistics from the collection."""
    try:
        # 1. Get total count
        collection_info = client.get_collection(collection_name)
        total_points = collection_info.points_count
        
        if total_points == 0:
            return {
                "total_products": 0,
                "total_categories": 0,
                "total_brands": 0,
                "in_stock": 0
            }

        # 2. Extract unique categories and brands (using scroll with limit since we don't have built-in aggregation)
        # For small-medium collections this is fast enough.
        # We only need 'category' and 'brand' fields.
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=1000, # Large batch to cover most items
            with_payload=["category", "brand", "in_stock"],
            with_vectors=False
        )
        
        categories = set()
        brands = set()
        in_stock_count = 0
        
        for p in points:
            payload = p.payload or {}
            cat = payload.get("category")
            if cat: categories.add(str(cat).strip())
            
            brand = payload.get("brand")
            if brand: brands.add(str(brand).strip())
            
            if payload.get("in_stock") is True or payload.get("in_stock") == 1:
                in_stock_count += 1
            elif payload.get("in_stock") is None: # Default to in stock if not specified
                in_stock_count += 1

        # Adjust in_stock_count proportionally if scroll limit was reached
        if total_points > 1000:
            ratio = total_points / 1000
            in_stock_count = int(in_stock_count * ratio)

        return {
            "total_products": total_points,
            "total_categories": len(categories),
            "total_brands": len(brands),
            "in_stock": in_stock_count
        }
    except Exception as e:
        print(f"DEBUG: Error getting stats: {e}")
        return {
            "total_products": 0,
            "total_categories": 0,
            "total_brands": 0,
            "in_stock": 0
        }

