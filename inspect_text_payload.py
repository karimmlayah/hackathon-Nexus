"""Inspect full payload of nexus-text collection"""
import os
import json
from dotenv import load_dotenv
from qdrant import get_qdrant_client

load_dotenv()

client = get_qdrant_client()
collection_name = "nexus-text"

results, _ = client.scroll(
    collection_name=collection_name,
    limit=2,
    with_payload=True,
)

for point in results:
    print(f"\nID: {point.id}")
    print(json.dumps(point.payload, indent=2, ensure_ascii=False))
