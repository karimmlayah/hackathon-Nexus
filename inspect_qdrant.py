import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
import json

load_dotenv()

url = os.getenv("QDRANT_URL", "").strip()
api_key = os.getenv("QDRANT_API_KEY", "").strip()
collection_name = os.getenv("QDRANT_COLLECTION", "products")

client = QdrantClient(url=url, api_key=api_key)

try:
    print(f"Collection: {collection_name}")
    points, _ = client.scroll(
        collection_name=collection_name,
        limit=5,
        with_payload=True
    )
    
    for i, p in enumerate(points):
        print(f"\n--- Point {i+1} ---")
        print(json.dumps(p.payload, indent=2))

except Exception as e:
    print(f"Error: {e}")
