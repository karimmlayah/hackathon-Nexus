"""Count fixed items in collection by scrolling"""
import os
from dotenv import load_dotenv
from qdrant import get_qdrant_client

load_dotenv()

client = get_qdrant_client()
collection_name = "nexus-multivector_3k_f"

try:
    total_fixed = 0
    next_page = None
    
    # We only check up to 500 items to see if progress is real
    print(f"Checking progress in '{collection_name}'...")
    results, _ = client.scroll(
        collection_name=collection_name,
        limit=500,
        with_payload=True,
        with_vectors=False
    )
    
    if results:
        count = sum(1 for p in results if p.payload.get("_fixed_image"))
        print(f"Fixed items in first 500: {count}")
    else:
        print("No items found.")

except Exception as e:
    print(f"Error: {e}")
