import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

url = os.getenv("QDRANT_URL", "").strip()
api_key = os.getenv("QDRANT_API_KEY", "").strip()
collection_name = os.getenv("QDRANT_COLLECTION", "products")

client = QdrantClient(url=url, api_key=api_key)

try:
    points, _ = client.scroll(collection_name=collection_name, limit=10, with_payload=True)
    all_keys = set()
    categories = set()
    for p in points:
        payload = p.payload or {}
        all_keys.update(payload.keys())
        # Try to find anything related to category
        for k, v in payload.items():
            if 'cat' in k.lower() or 'node' in k.lower() or 'path' in k.lower():
                print(f"Key '{k}': {v}")
                categories.add(str(v))
    
    print(f"\nAll keys found: {all_keys}")
    print(f"Potential categories: {categories}")

except Exception as e:
    print(f"Error: {e}")
