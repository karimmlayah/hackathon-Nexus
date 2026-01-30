from __future__ import annotations

import ast
import json
import os
import re
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams, NearestQuery, Mmr, Filter, FieldCondition, Range, MatchValue

from rag_app.core.database import get_deterministic_id, get_qdrant_client


def ensure_collection_old(
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
        # Use deterministic mapping from string to int
        product_id = product["id"]
        pid = get_deterministic_id(product_id)
        
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
    
    brand_raw = payload.get("brand") or payload.get("brandName") or ""
    if not name and len(brand_raw) > 20:
        name = brand_raw
        brand_display = ""
    else:
        brand_display = brand_raw
        
    if not name:
        name = f"Product {payload.get('row_id', point.id)}"

    # 2. Map Price
    price_val = 0.0
    for p_field in ["final_price", "price", "salePrice", "sale_price", "listedPrice", "listed_price", "currentPrice"]:
        val = payload.get(p_field)
        if val and val != "":
            try:
                val_str = str(val).replace("$", "").replace(",", "").strip()
                price_val = float(val_str)
                if price_val > 0: break
            except: continue
    
    # 3. Handle Images
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
        if trim_image.startswith("["):
            try:
                clean_json = trim_image.replace("'", '"')
                parsed = json.loads(clean_json)
                if isinstance(parsed, list):
                    image_urls = [str(url) for url in parsed if url]
                else:
                    image_urls = [str(parsed)]
            except:
                image_urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', trim_image)
        elif "," in trim_image:
            image_urls = [u.strip() for u in trim_image.split(",") if u.strip()]
        else:
            image_urls = [trim_image]
    
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
    
    rating_raw = payload.get("rating")
    rating = 0.0
    if rating_raw:
        try:
            rating = float(str(rating_raw).strip())
        except: pass
        
    review_count = payload.get("reviewCount") or payload.get("reviews_count") or payload.get("review_count")

    initial_price_val = 0.0
    for p_field in ["initial_price", "original_price", "listedPrice", "listed_price", "compare_at_price"]:
        val = payload.get(p_field)
        if val and val != "":
            try:
                val_str = str(val).replace("$", "").replace(",", "").strip()
                initial_price_val = float(val_str)
                if initial_price_val > 0: break
            except: continue

    # 5. Map Category
    category = None
    categories_field = payload.get("categories")
    if categories_field:
        categories_list = None
        if isinstance(categories_field, list):
            categories_list = categories_field
        elif isinstance(categories_field, str) and categories_field.strip():
            try:
                if categories_field.strip().startswith('['):
                    try:
                        categories_list = ast.literal_eval(categories_field)
                    except:
                        try:
                            json_str = categories_field.replace("'", '"')
                            categories_list = json.loads(json_str)
                        except:
                            categories_list = [c.strip().strip("'\"") for c in categories_field.split(",") if c.strip()]
            except:
                if "," in categories_field:
                    categories_list = [c.strip().strip("'\"[]") for c in categories_field.split(",") if c.strip()]
        
        if categories_list and len(categories_list) > 0:
            category = str(categories_list[-1]).strip() if len(categories_list) > 1 else str(categories_list[0]).strip()
    
    if not category or not category.strip() or category.lower() == "uncategorized":
        category = payload.get("category")
        if category and str(category).strip() and str(category).strip().lower() != "uncategorized":
            category = str(category).strip()
        else:
            node_name = payload.get("nodeName")
            if node_name and str(node_name).strip():
                category = str(node_name).strip()
    
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
    query_filter: Optional[Filter] = None,
) -> List[Dict[str, Any]]:
    """Search products with optional MMR for diversity."""
    if use_mmr:
        mmr_config = Mmr(
            diversity=mmr_diversity,
            candidates_limit=limit * 3
        )
        query = NearestQuery(
            nearest=query_vector,
            mmr=mmr_config
        )
        response = client.query_points(
            collection_name=collection_name,
            query=query,
            using=vector_name,
            limit=limit,
            with_payload=True,
            score_threshold=score_threshold,
            query_filter=query_filter,
            timeout=30.0
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
            query_filter=query_filter,
            timeout=30.0
        )

    items: List[Dict[str, Any]] = [map_qdrant_product(p) for p in response.points]
    
    if use_mmr and len(items) > 1:
        items = rerank_by_brand_diversity(items)
    
    return items


def rerank_by_brand_diversity(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Re-rank results to maximize brand diversity while maintaining score order."""
    if len(items) <= 1:
        return items
    
    reranked = []
    remaining = items.copy()
    last_brand = None
    
    while remaining:
        best_item = None
        best_idx = -1
        best_score = -1
        
        for idx, item in enumerate(remaining):
            brand = item.get("brand", "").strip().lower()
            if not brand:
                brand = "unknown"
            
            score = item.get("score", 0)
            
            if brand != last_brand:
                if best_item is None or score > best_score:
                    best_item = item
                    best_idx = idx
                    best_score = score
        
        if best_item is None:
            best_idx = 0
            best_score = remaining[0].get("score", 0)
            for idx, item in enumerate(remaining):
                if item.get("score", 0) > best_score:
                    best_idx = idx
                    best_score = item.get("score", 0)
            best_item = remaining[best_idx]
        
        reranked.append(best_item)
        last_brand = best_item.get("brand", "").strip().lower()
        if not last_brand:
            last_brand = "unknown"
        remaining.pop(best_idx)
    
    return reranked
