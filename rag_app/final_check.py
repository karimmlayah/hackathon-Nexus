from qdrant_client import QdrantClient
from core.config import settings

client = QdrantClient(
    url=settings.QDRANT_URL,
    api_key=settings.QDRANT_API_KEY
)

for target in ["nexus_multimodal_final", "amazon30015"]:
    try:
        info = client.get_collection(target)
        count = client.count(target).count
        print(f"\nNAME: {target} | COUNT: {count}")
        v_config = info.config.params.vectors
        if isinstance(v_config, dict):
            for k in v_config.keys(): print(f"  V_NAME: {k}")
        else:
            print("  V_NAME: UNNAMED")
    except:
        pass
