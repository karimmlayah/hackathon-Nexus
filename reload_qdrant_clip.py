"""
Script to reload Qdrant collection with CLIP embeddings for multimodal search.
This allows both text and image search in the same vector space.

OPTIMIZED: Uses batch encoding for much faster processing.
"""

import os
import sys
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

load_dotenv()

def log(msg):
    """Print with immediate flush"""
    print(msg, flush=True)


def main():
    log("[*] Starting CLIP re-encoding script...")
    
    from data import PRODUCTS
    from image_embedder import ImageEmbedder
    from qdrant import (
        get_qdrant_client,
        build_product_text,
        upsert_products,
    )
    
    collection_name = os.getenv("QDRANT_COLLECTION", "products")
    
    log(f"[*] Reloading collection '{collection_name}' with CLIP embeddings...")
    log(f"[*] Total products to process: {len(PRODUCTS)}")
    
    # Initialize CLIP embedder
    log("[*] Loading CLIP model (this may take 1-2 minutes first time)...")
    embedder = ImageEmbedder()
    log(f"[OK] CLIP model loaded. Vector size: {embedder.vector_size}")
    
    log("[*] Connecting to Qdrant Cloud...")
    client = get_qdrant_client()
    log("[OK] Connected to Qdrant")
    
    # Delete old collection
    try:
        log(f"[*] Deleting old collection '{collection_name}'...")
        client.delete_collection(collection_name)
        log("[OK] Collection deleted")
    except Exception as e:
        log(f"[WARN] Could not delete collection: {e}")
    
    # Recreate collection with named vectors (supporting both Text and CLIP)
    log(f"[*] Creating new collection with named vectors (Text=384D, CLIP={embedder.vector_size}D)...")
    from qdrant_client.http.models import Distance, VectorParams
    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "dense": VectorParams(size=384, distance=Distance.COSINE), # Standard text
            "clip": VectorParams(size=embedder.vector_size, distance=Distance.COSINE), # CLIP
        },
    )
    log("[OK] Collection created")
    
    # Check if we have pre-computed embeddings (from previous failed upload)
    import pickle
    embeddings_file = "clip_embeddings.pkl"
    vectors = None
    
    if os.path.exists(embeddings_file):
        log(f"[*] Found existing embeddings file: {embeddings_file}")
        try:
            with open(embeddings_file, "rb") as f:
                saved = pickle.load(f)
                if len(saved.get("embeddings", [])) == len(PRODUCTS):
                    vectors = saved["embeddings"]
                    log(f"[OK] Loaded {len(vectors)} pre-computed CLIP embeddings (skipping generation!)")
                else:
                    log(f"[WARN] Embeddings count mismatch. Will regenerate.")
        except Exception as e:
            log(f"[WARN] Could not load embeddings: {e}. Will regenerate.")
    
    if vectors is None:
        # Generate CLIP embeddings from product text using BATCH encoding (much faster!)
        log("[*] Building product texts...")
        texts = [build_product_text(p) for p in PRODUCTS]
        log(f"[OK] Built {len(texts)} product texts")
        
        log(f"[*] Generating CLIP embeddings using BATCH encoding...")
        log("[*] This is optimized - should take 5-15 minutes for ~26k products...")
        
        # Batch encoding is MUCH faster than one-by-one
        BATCH_SIZE = 64  # Process 64 at a time
        vectors = []
        total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(texts))
            batch_texts = texts[start_idx:end_idx]
            
            # Batch encode
            batch_vectors = embedder._model.encode(
                batch_texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=BATCH_SIZE,
            )
            
            vectors.extend(batch_vectors.tolist())
            
            # Progress update every 10 batches
            if (batch_idx + 1) % 10 == 0 or batch_idx == total_batches - 1:
                percent = (end_idx / len(texts)) * 100
                log(f"    Progress: {end_idx}/{len(texts)} ({percent:.1f}%)")
    
    log(f"[OK] Generated {len(vectors)} embeddings")
    
    # Save embeddings to file (in case upload fails, we can resume)
    import pickle
    embeddings_file = "clip_embeddings.pkl"
    log(f"[*] Saving embeddings to {embeddings_file} (backup)...")
    with open(embeddings_file, "wb") as f:
        pickle.dump({"embeddings": vectors, "products": PRODUCTS}, f)
    log(f"[OK] Embeddings saved")
    
    # Upload to Qdrant in small batches (Qdrant Cloud has request size limits)
    log(f"[*] Uploading products to Qdrant Cloud in batches...")
    
    UPLOAD_BATCH_SIZE = 100  # Small batches to avoid timeout
    total_uploaded = 0
    
    from qdrant_client.http.models import PointStruct
    import time
    
    for batch_start in range(0, len(PRODUCTS), UPLOAD_BATCH_SIZE):
        batch_end = min(batch_start + UPLOAD_BATCH_SIZE, len(PRODUCTS))
        batch_products = PRODUCTS[batch_start:batch_end]
        batch_vectors = vectors[batch_start:batch_end]
        
        # Build points for this batch
        points = []
        for i, (product, vector) in enumerate(zip(batch_products, batch_vectors)):
            product_id = product.get("id", batch_start + i)
            # Convert string IDs to integers using hash
            if isinstance(product_id, str):
                point_id = abs(hash(product_id)) % (10**18)
            else:
                point_id = int(product_id)
            
            points.append(PointStruct(
                id=point_id,
                vector={"clip": vector}, # Specify 'clip' vector name
                payload={
                    "id": str(product_id),
                    "name": product.get("name", ""),
                    "title": product.get("name", ""),
                    "description": product.get("description", ""),
                    "category": product.get("category", ""),
                    "price": float(product.get("price", 0) or 0),
                    "sale_price": float(product.get("sale_price", 0) or 0),
                    "listed_price": float(product.get("listed_price", 0) or 0),
                    "brand": product.get("brand", ""),
                    "rating": float(product.get("rating", 0) or 0),
                    "review_count": int(product.get("review_count", 0) or 0),
                    "breadcrumbs": product.get("breadcrumbs", []),
                    "image_urls": product.get("image_urls", []),
                    "features": product.get("features", []),
                    "color": product.get("color", ""),
                    "material": product.get("material", ""),
                    "style": product.get("style", ""),
                    "size": product.get("size", ""),
                    "amazon_url": product.get("amazon_url", ""),
                }
            ))
        
        # Upload with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                client.upsert(collection_name=collection_name, points=points)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    log(f"    [WARN] Retry {attempt + 1}/{max_retries} for batch {batch_start}-{batch_end}")
                    time.sleep(2)
                else:
                    raise e
        
        total_uploaded += len(batch_products)
        
        if (batch_start // UPLOAD_BATCH_SIZE + 1) % 10 == 0 or batch_end == len(PRODUCTS):
            percent = (total_uploaded / len(PRODUCTS)) * 100
            log(f"    Uploaded: {total_uploaded}/{len(PRODUCTS)} ({percent:.1f}%)")
    
    log("[OK] All products uploaded successfully!")
    
    # Verify
    collection_info = client.get_collection(collection_name)
    log(f"\n========================================")
    log(f"[OK] DONE! Collection now has {collection_info.points_count} products.")
    log(f"[OK] Image search is now enabled!")
    log(f"========================================")
    log(f"\nRestart your API server:")
    log(f"  uvicorn app:app --reload --port 8001")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n\n[WARN] Interrupted by user")
    except Exception as e:
        log(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
