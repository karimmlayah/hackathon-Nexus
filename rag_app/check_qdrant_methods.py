from qdrant_client import QdrantClient
from core.config import settings

try:
    client = QdrantClient(
        url=settings.QDRANT_URL if settings.QDRANT_URL else ":memory:",
        api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
    )
    print("Client Type:", type(client))
    print("Has 'search'?", hasattr(client, "search"))
    print("Has 'query_points'?", hasattr(client, "query_points"))
    print("Has 'search_points'?", hasattr(client, "search_points"))
    print("Directory sample:", [x for x in dir(client) if "search" in x or "query" in x])
except Exception as e:
    print("Error:", e)
