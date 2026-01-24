from __future__ import annotations

import os
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
            "category": product.get("category"),
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
    for p_field in ["price", "salePrice", "sale_price", "listedPrice", "listed_price", "currentPrice"]:
        val = payload.get(p_field)
        if val and val != "":
            try:
                price_val = float(val)
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
                import json
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
                import json
                parsed = json.loads(desc_fallback.replace("'", '"'))
                description = " ".join(parsed) if isinstance(parsed, list) else str(parsed)
             except:
                description = str(desc_fallback).strip('[]"\' ')
        else:
            description = str(desc_fallback)
    
    # Map rating and review count
    rating = payload.get("rating")
    review_count = payload.get("reviewCount") or payload.get("review_count")

    return {
        "id": payload.get("id", payload.get("row_id", point.id)),
        "name": name,
        "description": description,
        "category": payload.get("category") or payload.get("nodeName") or "Uncategorized",
        "price": price_val,
        "currency": payload.get("currency") or "$",
        "score": float(point.score) if hasattr(point, "score") and point.score is not None else 0.0,
        "brand": brand_display,
        "rating": rating,
        "review_count": review_count,
        "image_urls": image_urls,
        "image": image_single,
        "url": payload.get("url"),
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
        from qdrant_client.http.models import NamedVector
        if vector_name:
            nearest = NamedVector(name=vector_name, vector=query_vector)
        else:
            nearest = query_vector

        query = NearestQuery(
            nearest=nearest,
            mmr=mmr_config
        )
        response = client.query_points(
            collection_name=collection_name,
            query=query,
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
    return items

