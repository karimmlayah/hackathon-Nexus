"""Inspect product payload to check discount field"""
import os
import json
from dotenv import load_dotenv
from qdrant import get_qdrant_client

load_dotenv()

client = get_qdrant_client()
collection_name = "nexus-multivector_3k_f"

# Search for the product by title text
from qdrant_client.http.models import Filter, FieldCondition, MatchText

# Using scroll with filter to find the specific product
results, _ = client.scroll(
    collection_name=collection_name,
    scroll_filter=Filter(
        must=[
            FieldCondition(
                key="title",
                match=MatchText(text="Hardwired LED Under Cabinet Lighting")
            )
        ]
    ),
    limit=1,
    with_payload=True,
)

if results:
    point = results[0]
    print(f"\nProduct ID: {point.id}")
    print(f"Title: {point.payload.get('title')}")
    print(f"Final Price: {point.payload.get('final_price')}")
    print(f"Discount Raw: '{point.payload.get('discount')}'")
    print("-" * 40)
    # Print discount type
    disc = point.payload.get('discount')
    print(f"Discount Type: {type(disc)}")
else:
    print("Product not found via text match. Trying semantic search...")
    # Fallback to semantic search if exact match fails
    from embedder import Embedder
    embedder = Embedder()
    query_vector = embedder.embed_text("Hardwired LED Under Cabinet Lighting - 16 Watt, 24\", Dimmable")
    
    search_results = client.search(
        collection_name=collection_name,
        query_vector=("text_dense", query_vector),
        limit=1,
        with_payload=True
    )
    
    if search_results:
        point = search_results[0]
        print(f"\nFound via semantic search (Score: {point.score})")
        print(f"Product ID: {point.id}")
        print(f"Title: {point.payload.get('title')}")
        print(f"Final Price: {point.payload.get('final_price')}")
        print(f"Discount Raw: '{point.payload.get('discount')}'")
    else:
        print("Product definitively not found.")
