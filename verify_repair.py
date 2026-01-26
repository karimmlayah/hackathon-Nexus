"""Verify repaired items"""
import os
from dotenv import load_dotenv
from qdrant import get_qdrant_client

load_dotenv()

client = get_qdrant_client()
collection_name = "nexus-multivector_3k_f"

try:
    # 1. Get a fixed item (ID in first 10)
    res = client.retrieve(collection_name, ids=[2], with_vectors=True)
    if res:
        p = res[0]
        v = p.vector.get("image_dense", [])
        
        import math
        norm = math.sqrt(sum(x*x for x in v))
        print(f"Point {p.id} Norm: {norm}")
        
        if norm > 0:
            print("✅ Vector is valid! Testing search...")
            
            # 2. Search using this vector
            hits = client.query_points(
                collection_name=collection_name,
                query=v,
                using="image_dense",
                limit=3
            ).points
            
            print(f"Search results: {len(hits)}")
            for hit in hits:
                print(f"  - Hit ID: {hit.id}, Score: {hit.score}, Title: {hit.payload.get('title', '')[:30]}")
            
            if hits and hits[0].id == 2:
                print("✅ REPAIR SUCCESSFUL!")
            else:
                print("❌ Search did not return the point itself as top hit.")
        else:
            print("❌ Vector is still ZERO!")
    else:
        print("❌ Point not found.")

except Exception as e:
    print(f"Error: {e}")
