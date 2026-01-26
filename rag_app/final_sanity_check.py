import os
import json
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

def final_sanity_check():
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    collection = os.getenv("QDRANT_COLLECTION", "amazon30015")
    
    print(f"Connecting to: {url}")
    print(f"Collection: {collection}")
    
    client = QdrantClient(url=url, api_key=api_key)
    
    try:
        # Check collection info
        info = client.get_collection(collection)
        print(f"✅ Collection found. Points: {info.points_count}")
        
        # Sample points and check vectors
        res, _ = client.scroll(collection, limit=5, with_vectors=True, with_payload=True)
        for p in res:
            v_image = p.vector.get("image_dense", []) if isinstance(p.vector, dict) else []
            v_text = p.vector.get("text_dense", []) if isinstance(p.vector, dict) else []
            
            import math
            norm_i = math.sqrt(sum(x*x for x in v_image))
            norm_t = math.sqrt(sum(x*x for x in v_text))
            
            title = p.payload.get("title", p.payload.get("name", "No Title"))[:40]
            print(f"Point {p.id}: {title}")
            print(f"  - Image Vector Norm: {norm_i:.4f}")
            print(f"  - Text Vector Norm: {norm_t:.4f}")
            
    except Exception as e:
        print(f"❌ Error during sanity check: {e}")

if __name__ == "__main__":
    final_sanity_check()
