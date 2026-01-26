from qdrant_client import QdrantClient
from core.config import settings

client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)

try:
    info = client.get_collection(settings.COLLECTION_NAME)
    print("Collection Info:")
    print(info.config.params.vectors)
except Exception as e:
    print(f"Error: {e}")
