import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from collections import Counter

load_dotenv()

url = os.getenv("QDRANT_URL", "").strip()
api_key = os.getenv("QDRANT_API_KEY", "").strip()
collection_name = os.getenv("QDRANT_COLLECTION", "products")

client = QdrantClient(url=url, api_key=api_key)

try:
    # Scroll through points and collect categories
    points, _ = client.scroll(
        collection_name=collection_name,
        limit=1000,
        with_payload=["category", "categories", "nodeName"],
        with_vectors=False
    )
    
    categories = []
    for p in points:
        payload = p.payload or {}
        cat = payload.get("category") or payload.get("nodeName")
        if cat:
            categories.append(str(cat))
    
    counts = Counter(categories)
    print("Top Categories in Qdrant:")
    for cat, count in counts.most_common(20):
        print(f"{cat}: {count}")

except Exception as e:
    print(f"Error: {e}")
