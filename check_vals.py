"""Check vector values specifically"""
import os
from dotenv import load_dotenv
from qdrant import get_qdrant_client

load_dotenv()

client = get_qdrant_client()
collection_name = "nexus-multivector_3k_f"

try:
    results, _ = client.scroll(
        collection_name=collection_name,
        limit=1,
        with_vectors=True
    )
    
    if results:
        p = results[0]
        v = p.vector.get("image_dense", [])
        print(f"Point ID: {p.id}")
        print(f"Vector Len: {len(v)}")
        if v:
            print(f"First 10 values: {v[:10]}")
            import math
            sum_sq = sum(x*x for x in v)
            print(f"Vector L2 Norm: {math.sqrt(sum_sq)}")
            nonzero = [x for x in v if abs(x) > 1e-9]
            print(f"Non-zero elements: {len(nonzero)}")
        else:
            print("Vector is EMPTY or MISSING")
    else:
        print("No points found")

except Exception as e:
    print(f"Error: {e}")
