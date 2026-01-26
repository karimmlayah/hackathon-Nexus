"""Check the text collection for product data"""
import os
import json
from dotenv import load_dotenv
from qdrant import get_qdrant_client

load_dotenv()

client = get_qdrant_client()

# Default collection name from app.py logic
# In app.py line 281: text_collection = "nexus-text"
collection_name = "nexus-text"

print(f"Checking collection: {collection_name}")

try:
    results, _ = client.scroll(
        collection_name=collection_name,
        limit=3,
        with_payload=True,
    )
    
    print(f"\nFound {len(results)} sample products from '{collection_name}'")
    
    for i, point in enumerate(results, 1):
        print(f"\nProduct {i} - ID: {point.id}")
        # print first few chars of name to verify
        payload = point.payload
        print(f"Name: {payload.get('name')}")
        print(f"Price: {payload.get('price')}")
        
except Exception as e:
    print(f"\nError: {e}")
