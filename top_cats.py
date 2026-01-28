import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from collections import Counter
import ast

load_dotenv()

url = os.getenv("QDRANT_URL", "").strip()
api_key = os.getenv("QDRANT_API_KEY", "").strip()
collection_name = os.getenv("QDRANT_COLLECTION", "products")

client = QdrantClient(url=url, api_key=api_key)

try:
    points, _ = client.scroll(collection_name=collection_name, limit=1000, with_payload=["categories"])
    
    all_cats = []
    for p in points:
        payload = p.payload or {}
        cats = payload.get("categories")
        if isinstance(cats, list) and cats:
            # Add the first or last category to represent the item
            all_cats.append(cats[0]) # usually the main category
        elif isinstance(cats, str) and cats.strip():
            try:
                parsed = ast.literal_eval(cats)
                if isinstance(parsed, list) and parsed:
                    all_cats.append(parsed[0])
            except:
                pass
    
    counts = Counter(all_cats)
    print("Top Main Categories:")
    for cat, count in counts.most_common(10):
        print(f"{cat}: {count}")

except Exception as e:
    print(f"Error: {e}")
