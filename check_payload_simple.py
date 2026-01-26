"""Check what fields are available in the images-only-clip collection"""
import os
import json
from dotenv import load_dotenv
from qdrant import get_qdrant_client

load_dotenv()

client = get_qdrant_client()

# Get a sample point from the collection
collection_name = "images-only-clip"
try:
    results, _ = client.scroll(
        collection_name=collection_name,
        limit=2,
        with_payload=True,
    )
    
    print(f"\nFound {len(results)} sample products from '{collection_name}'")
    print("="*80)
    
    for i, point in enumerate(results, 1):
        print(f"\nProduct {i} - ID: {point.id}")
        print(f"Payload keys: {list(point.payload.keys())}")
        print("\nFull payload:")
        print(json.dumps(point.payload, indent=2, ensure_ascii=False))
        print("-"*80)
        
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
