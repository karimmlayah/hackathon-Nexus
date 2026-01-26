"""Get all collection info precisely"""
import os
import json
from dotenv import load_dotenv
from qdrant import get_qdrant_client

load_dotenv()

client = get_qdrant_client()
collections = client.get_collections().collections

output = []
for c in collections:
    info = client.get_collection(c.name)
    output.append({
        "name": c.name,
        "points": info.points_count,
        "vectors": str(info.config.params.vectors)
    })

with open("all_collections_detailed.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
print("Saved all collection details to all_collections_detailed.json")
