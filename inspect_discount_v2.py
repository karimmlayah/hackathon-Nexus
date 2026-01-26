"""Inspect product payload to check discount field using semantic search"""
import os
import json
from dotenv import load_dotenv
from qdrant import get_qdrant_client
from embedder import Embedder

load_dotenv()

try:
    client = get_qdrant_client()
    collection_name = "nexus-multivector_3k_f"
    
    embedder = Embedder()
    # Use a distinctive part of the title
    query_text = "Hardwired LED Under Cabinet Lighting - 16 Watt, 24 inches"
    print(f"Embedding query: '{query_text}'...")
    query_vector = embedder.embed_text(query_text)
    
    print(f"Searching in '{collection_name}'...")
    search_results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        using="text_dense",
        limit=50,
        with_payload=True
    ).points
    
    print(f"\nFound {len(search_results)} results. Searching for target product...")
    
    target_found = False
    for point in search_results:
        title = point.payload.get('title', '')
        if "Hardwired LED" in title and "Under Cabinet" in title:
            print(f"\n✅ TARGET FOUND!")
            print(f"ID: {point.id}")
            print(f"Title: {title}")
            print(f"Final Price: {point.payload.get('final_price')}")
            print(f"Discount: '{point.payload.get('discount')}'")
            print(f"Payload Keys: {list(point.payload.keys())}")
            
            # Save to JSON file
            with open("debug_payload_target.json", "w", encoding="utf-8") as f:
                json.dump(point.payload, f, indent=2, default=str)
            print("Payload saved to debug_payload_target.json")
            target_found = True
            break
            
    if not target_found:
        print("\n❌ Target product NOT found in top 50 results.")

except Exception as e:
    print(f"\nERROR: {e}")
    # Print full error details if available
    try:
        import traceback
        traceback.print_exc()
    except: pass
