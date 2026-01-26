"""Check image vectors in nexus-multivector_3k_f"""
import os
import json
from dotenv import load_dotenv
from qdrant import get_qdrant_client

load_dotenv()

client = get_qdrant_client()
collection_name = "nexus-multivector_3k_f"

print(f"Checking collection: {collection_name}")

try:
    # 1. Check Collection Info
    info = client.get_collection(collection_name)
    print(f"\n✅ Collection Found!")
    print(f"Points: {info.points_count}")
    print(f"Vectors Config: {info.config.params.vectors}")

    # 2. Check a random point
    results, _ = client.scroll(
        collection_name=collection_name,
        limit=1,
        with_vectors=True,
    )
    
    if results:
        point = results[0]
        vectors = point.vector
        print(f"\n📦 Sample Point ID: {point.id}")
        if isinstance(vectors, dict):
            print(f"Available Vectors: {list(vectors.keys())}")
            if "image_dense" in vectors:
                print(f"✅ 'image_dense' found (length: {len(vectors['image_dense'])})")
            else:
                print(f"❌ 'image_dense' NOT found in sample point!")
        else:
            print(f"❌ Vectors is not a dict: {type(vectors)}")
            
    # 3. Self-Search Test
    print("\n🔍 Testing Self-Search (Using Real Vector)...")
    if results and "image_dense" in results[0].vector:
        real_vector = results[0].vector["image_dense"]
        
        hits = client.query_points(
            collection_name=collection_name,
            query=real_vector,
            using="image_dense",
            limit=3
        ).points
        
        print(f"Self-Search Hit Count: {len(hits)}")
        if hits:
            print(f"Top Hit ID: {hits[0].id}")
            print(f"Top Score: {hits[0].score}")
            if hits[0].id == results[0].id:
                print("✅ Self-search match successful!")
            else:
                print("❌ Self-search returned different item!")
        else:
            print("❌ No results found for self-search!")
    else:
        print("❌ Could not get real vector for test.")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
