"""
Script to reload Qdrant collection with data from CSV.
Use this if the data format in Qdrant doesn't match your expectations.
"""

import os
from dotenv import load_dotenv

from data import PRODUCTS
from embedder import Embedder
from qdrant import (
    get_qdrant_client,
    build_product_text,
    upsert_products,
)

load_dotenv()


def main():
    collection_name = os.getenv("QDRANT_COLLECTION", "products")
    
    print(f"🔄 Reloading collection '{collection_name}' with {len(PRODUCTS)} products from CSV...")
    
    # Initialize
    print("📦 Loading SentenceTransformer model...")
    embedder = Embedder(model_name="all-MiniLM-L6-v2")
    
    print("🔌 Connecting to Qdrant Cloud...")
    client = get_qdrant_client()
    
    # Delete old collection
    try:
        print(f"🗑️  Deleting old collection '{collection_name}'...")
        client.delete_collection(collection_name)
        print("✅ Collection deleted")
    except Exception as e:
        print(f"⚠️  Could not delete collection (maybe it doesn't exist): {e}")
    
    # Recreate collection
    print(f"📊 Creating collection '{collection_name}'...")
    from qdrant_client.http.models import Distance, VectorParams
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=embedder.vector_size, distance=Distance.COSINE),
    )
    print("✅ Collection created")
    
    # Generate embeddings
    print("🔄 Building product texts...")
    texts = [build_product_text(p) for p in PRODUCTS]
    
    print(f"🧮 Generating embeddings for {len(texts)} products...")
    vectors = embedder.embed_texts(texts)
    print("✅ Embeddings generated")
    
    # Upload to Qdrant
    print(f"📤 Uploading {len(PRODUCTS)} products to Qdrant Cloud...")
    upsert_products(
        client=client,
        collection_name=collection_name,
        products=PRODUCTS,
        vectors=vectors,
    )
    print("✅ Products uploaded successfully!")
    
    # Verify
    collection_info = client.get_collection(collection_name)
    print(f"\n✅ Done! Collection now has {collection_info.points_count} products.")
    print(f"\nYou can now restart your API server: uvicorn app:app --reload --port 8001")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
