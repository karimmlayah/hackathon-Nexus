from qdrant_client import QdrantClient
from core.config import settings

def check_cloud():
    print(f"📡 Connecting to: {settings.QDRANT_URL}")
    client = QdrantClient(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY
    )
    
    try:
        exists = client.collection_exists(settings.COLLECTION_NAME)
        print(f"📦 Collection '{settings.COLLECTION_NAME}' exists: {exists}")
        
        if exists:
            count = client.count(collection_name=settings.COLLECTION_NAME).count
            print(f"📊 QDRANT CLOUD COUNT: {count}")
            
            import pandas as pd
            df = pd.read_csv(settings.FIXED_DATASET_PATH)
            local_count = len(df)
            print(f"📊 LOCAL CSV COUNT: {local_count}")
            
            if count >= local_count:
                print("✅ DATA IS FULLY SYNCED.")
            else:
                print(f"⚠️ MISSING {local_count - count} POINTS.")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_cloud()
