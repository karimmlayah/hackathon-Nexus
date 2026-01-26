"""Quick diagnostic to check Qdrant connection"""
import os
from dotenv import load_dotenv

load_dotenv()

print(f"QDRANT_URL: {os.getenv('QDRANT_URL')}")
print(f"QDRANT_COLLECTION: {os.getenv('QDRANT_COLLECTION')}")

try:
    from qdrant import get_qdrant_client
    client = get_qdrant_client()
    
    collection_name = os.getenv("QDRANT_COLLECTION", "amazon30015")
    print(f"\nTrying to connect to collection: {collection_name}")
    
    info = client.get_collection(collection_name)
    print(f"✅ Collection found!")
    print(f"Points: {info.points_count}")
    print(f"Vectors: {info.config.params.vectors}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
