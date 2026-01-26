from qdrant_client import QdrantClient
from core.config import settings

client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)

try:
    collections = client.get_collections().collections
    for coll in collections:
        name = coll.name
        info = client.get_collection(name)
        vectors = info.config.params.vectors
        count = client.count(name).count
        print(f"\n--- COLLECTION: {name} ({count} points) ---")
        if isinstance(vectors, dict):
            for v_name, params in vectors.items():
                print(f"  [NAMED] {v_name}: size={params.size}")
        else:
            print(f"  [UNNAMED]: size={vectors.size}")
except Exception as e:
    print(f"Error: {e}")
