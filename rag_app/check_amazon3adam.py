from qdrant_client import QdrantClient
from core.config import settings

client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)

try:
    info = client.get_collection("amazon30015")
    count = client.count("amazon30015").count
    print(f"COLLECTION: amazon30015")
    print(f"COUNT: {count}")
    v_config = info.config.params.vectors
    if isinstance(v_config, dict):
        for k, v in v_config.items():
            print(f"VECTOR: {k} | SIZE: {v.size}")
    else:
        print(f"VECTOR: UNNAMED | SIZE: {v_config.size}")
except Exception as e:
    print(f"Error: {e}")
