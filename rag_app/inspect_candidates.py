from qdrant_client import QdrantClient
from core.config import settings

client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)

candidates = ["nexus_multimodal_final", "amazon30015"]

for name in candidates:
    try:
        info = client.get_collection(name)
        count = client.count(name).count
        print(f"\n--- {name} ({count} points) ---")
        print(f"Vectors: {info.config.params.vectors}")
    except:
        print(f"\n--- {name} NOT FOUND ---")
