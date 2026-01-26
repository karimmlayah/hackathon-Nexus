from qdrant_client import QdrantClient
from qdrant_client.http import models
from core.config import settings

# Initialize Qdrant Client
# If QDRANT_URL is set to a Cloud URL, api_key is used. 
# If it's ":memory:" or local path, it runs locally.
client = QdrantClient(
    url=settings.QDRANT_URL if settings.QDRANT_URL else ":memory:",
    api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
)

def get_qdrant_client() -> QdrantClient:
    return client

def ensure_collection(vector_size: int = 384):
    """Ensures the collection exists with the correct configuration."""
    if not client.collection_exists(settings.COLLECTION_NAME):
        client.create_collection(
            collection_name=settings.COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE
            )
        )
        print(f"Created collection '{settings.COLLECTION_NAME}' with vector size {vector_size}")
