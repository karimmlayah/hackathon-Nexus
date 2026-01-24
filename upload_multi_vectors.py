"""
Upload multi-vector embeddings to Qdrant Cloud.

This script loads the embeddings generated from Kaggle/Colab and uploads them to Qdrant
with named vectors for hybrid search:
- semantic: SentenceTransformer embeddings (meaning-based)
- keyword: Dense/sparse keyword embeddings
- image: CLIP image embeddings
"""

import os
import sys
import pickle
import time
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

load_dotenv()


def log(msg):
    print(msg, flush=True)


def main():
    log("[*] Multi-Vector Upload to Qdrant")
    log("=" * 50)
    
    # Configuration
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "products")
    EMBEDDINGS_FILE = "multi_vector_embeddings.pkl"
    
    if not QDRANT_URL or not QDRANT_API_KEY:
        log("[ERROR] Set QDRANT_URL and QDRANT_API_KEY in .env")
        return
    
    # Load embeddings
    log(f"[*] Loading embeddings from {EMBEDDINGS_FILE}...")
    
    if not os.path.exists(EMBEDDINGS_FILE):
        log(f"[ERROR] File not found: {EMBEDDINGS_FILE}")
        log("[*] Generate embeddings first using the Kaggle notebook:")
        log("    generate_multi_vectors_kaggle.ipynb")
        return
    
    with open(EMBEDDINGS_FILE, "rb") as f:
        data = pickle.load(f)
    
    products = data["products"]
    semantic_vectors = data["semantic_vectors"]
    image_vectors = data["image_vectors"]
    use_sparse = data.get("use_sparse", False)
    
    if use_sparse:
        sparse_vectors = data.get("sparse_vectors", [])
        keyword_vectors = None
    else:
        keyword_vectors = data.get("keyword_vectors", [])
        sparse_vectors = None
    
    log(f"[OK] Loaded {len(products)} products")
    log(f"    Semantic vectors: {len(semantic_vectors)} x {len(semantic_vectors[0])}D")
    if keyword_vectors:
        log(f"    Keyword vectors: {len(keyword_vectors)} x {len(keyword_vectors[0])}D")
    if sparse_vectors:
        log(f"    Sparse vectors: {len(sparse_vectors)}")
    log(f"    Image vectors: {len(image_vectors)} x {len(image_vectors[0])}D")
    
    # Connect to Qdrant
    log("[*] Connecting to Qdrant Cloud...")
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import (
        Distance, VectorParams, PointStruct,
        SparseVectorParams, SparseIndexParams
    )
    
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    log("[OK] Connected!")
    
    # Delete old collection
    try:
        log(f"[*] Deleting old collection '{COLLECTION_NAME}'...")
        client.delete_collection(COLLECTION_NAME)
        log("[OK] Deleted")
    except Exception as e:
        log(f"[WARN] {e}")
    
    # Create collection with named vectors
    log(f"[*] Creating collection '{COLLECTION_NAME}' with multi-vectors...")
    
    vectors_config = {
        "semantic": VectorParams(
            size=len(semantic_vectors[0]),
            distance=Distance.COSINE
        ),
        "image": VectorParams(
            size=len(image_vectors[0]),
            distance=Distance.COSINE
        ),
    }
    
    # Add keyword vector config
    if keyword_vectors:
        vectors_config["keyword"] = VectorParams(
            size=len(keyword_vectors[0]),
            distance=Distance.COSINE
        )
    
    sparse_vectors_config = None
    if use_sparse and sparse_vectors:
        sparse_vectors_config = {
            "keyword_sparse": SparseVectorParams(
                index=SparseIndexParams(on_disk=False)
            )
        }
    
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=vectors_config,
        sparse_vectors_config=sparse_vectors_config,
    )
    log("[OK] Collection created!")
    log(f"    Vectors: {list(vectors_config.keys())}")
    if sparse_vectors_config:
        log(f"    Sparse: {list(sparse_vectors_config.keys())}")
    
    # Upload in batches
    log("[*] Uploading products to Qdrant...")
    
    BATCH_SIZE = 50
    total_uploaded = 0
    
    for batch_start in range(0, len(products), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(products))
        
        points = []
        for i in range(batch_start, batch_end):
            product = products[i]
            product_id = product.get("id", str(i))
            point_id = abs(hash(str(product_id))) % (10**18)
            
            # Named vectors
            vectors = {
                "semantic": semantic_vectors[i],
                "image": image_vectors[i],
            }
            
            if keyword_vectors:
                vectors["keyword"] = keyword_vectors[i]
            
            point = PointStruct(
                id=point_id,
                vector=vectors,
                payload=product
            )
            points.append(point)
        
        # Upload with retry
        for attempt in range(3):
            try:
                client.upsert(collection_name=COLLECTION_NAME, points=points)
                break
            except Exception as e:
                if attempt < 2:
                    log(f"    [WARN] Retry {attempt+1}/3...")
                    time.sleep(2)
                else:
                    log(f"    [ERROR] Failed batch {batch_start}: {e}")
                    raise
        
        total_uploaded += len(points)
        
        if (batch_start // BATCH_SIZE + 1) % 20 == 0 or batch_end == len(products):
            percent = total_uploaded / len(products) * 100
            log(f"    Progress: {total_uploaded}/{len(products)} ({percent:.1f}%)")
    
    # Verify
    info = client.get_collection(COLLECTION_NAME)
    
    log("")
    log("=" * 50)
    log("[OK] UPLOAD COMPLETE!")
    log("=" * 50)
    log(f"Collection: {COLLECTION_NAME}")
    log(f"Points: {info.points_count}")
    log(f"Vectors: semantic, keyword, image")
    log("")
    log("You can now use hybrid search with:")
    log("  - Semantic search (meaning)")
    log("  - Keyword search (exact words)")
    log("  - Image search (CLIP)")
    log("")
    log("Start your API: uvicorn app:app --reload --port 8001")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n[WARN] Interrupted")
    except Exception as e:
        log(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
