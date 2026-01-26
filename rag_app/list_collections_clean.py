from qdrant_client import QdrantClient
from core.config import settings

client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)

try:
    collections = client.get_collections().collections
    print("Available Collections:")
    for coll in collections:
        print(f"- {coll.name}")
except Exception as e:
    print(f"Error: {e}")
