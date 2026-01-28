import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from collections import Counter

load_dotenv()

url = os.getenv("QDRANT_URL", "").strip()
api_key = os.getenv("QDRANT_API_KEY", "").strip()
collection_name = "amazon30015"

client = QdrantClient(url=url, api_key=api_key)

try:
    print(f"Connecting to {collection_name}...")
    # Scroll and get categories
    points, _ = client.scroll(
        collection_name=collection_name,
        limit=500,
        with_payload=True
    )
    
    categories = []
    for p in points:
        payload = p.payload or {}
        cat = payload.get("category") or payload.get("nodeName")
        if cat:
            categories.append(str(cat))
    
    counts = Counter(categories)
    print("Top Categories in amazon30015:")
    for cat, count in counts.most_common(20):
        print(f"{cat}: {count}")

except Exception as e:
    print(f"Error: {e}")
