import asyncio
from core.config import settings
from core.database import get_qdrant_client, ensure_collection
from core.llm import get_embeddings
from services.ingestion import process_local_file
from qdrant_client.http import models
import uuid

async def ingest_fixed_dataset():
    print(f"🚀 Starting ingestion of fixed dataset: {settings.FIXED_DATASET_PATH}")
    
    # 1. Parse File
    documents = await process_local_file(settings.FIXED_DATASET_PATH)
    
    if not documents:
        print("❌ No documents found or error reading file.")
        return

    print(f"📊 Found {len(documents)} items in dataset.")
    
    # 2. Check if already indexed
    client = get_qdrant_client()
    collection_name = settings.COLLECTION_NAME
    
    # Force a clean update to ensure named vector "vector" exists
    if client.collection_exists(collection_name):
        info = client.get_collection(collection_name)
        # Check if vectors config is a dict (named vectors) and contains "vector"
        is_named = isinstance(info.config.params.vectors, dict)
        if not is_named or "vector" not in info.config.params.vectors:
            print(f"⚠️ Collection '{collection_name}' needs named vector 'vector'. Recreating...")
            client.delete_collection(collection_name)
    
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config={"vector": models.VectorParams(size=384, distance=models.Distance.COSINE)}
        )
        print(f"✅ Created collection '{collection_name}' with named vector 'vector'")
    else:
        count_result = client.count(collection_name=collection_name).count
        if count_result > 0:
            print(f"✅ Collection '{collection_name}' ready with {count_result} points.")
            return

    print("🧠 Generating embeddings and indexing... This may take a moment.")
    
    # Batch processing to avoid memory issues
    batch_size = 50
    total_batches = (len(documents) + batch_size - 1) // batch_size
    
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i : i + batch_size]
        texts = [doc["text"] for doc in batch_docs]
        
        embeddings = get_embeddings(texts)
        
        points = []
        for j, doc in enumerate(batch_docs):
            points.append(models.PointStruct(
                id=str(uuid.uuid4()),
                vector={"vector": embeddings[j]},
                payload=doc
            ))
            
        client.upsert(
            collection_name=collection_name,
            points=points
        )
        print(f"   Processed batch {i // batch_size + 1}/{total_batches}")

    print("🎉 Fixed dataset ingestion complete!")

if __name__ == "__main__":
    asyncio.run(ingest_fixed_dataset())
