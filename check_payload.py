"""Check what fields are available in the images-only-clip collection"""
import os
from dotenv import load_dotenv
from qdrant import get_qdrant_client

load_dotenv()

client = get_qdrant_client()

# Get a sample point from the collection
collection_name = "images-only-clip"
try:
    results, _ = client.scroll(
        collection_name=collection_name,
        limit=3,
        with_payload=True,
    )
    
    print(f"\n✅ Found {len(results)} sample products from '{collection_name}'")
    print("\n" + "="*80)
    
    for i, point in enumerate(results, 1):
        print(f"\n📦 Product {i} (ID: {point.id}):")
        print(f"\nAvailable payload fields:")
        for key, value in point.payload.items():
            # Truncate long values for readability
            if isinstance(value, str) and len(value) > 100:
                value_display = value[:100] + "..."
            elif isinstance(value, list) and len(value) > 3:
                value_display = f"[{len(value)} items] {value[:2]}..."
            else:
                value_display = value
            print(f"  - {key}: {value_display}")
        print("\n" + "-"*80)
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
