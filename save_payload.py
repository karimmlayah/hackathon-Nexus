"""Save payload to JSON file for analysis"""
import os
import json
from dotenv import load_dotenv
from qdrant import get_qdrant_client

load_dotenv()

client = get_qdrant_client()

collection_name = "images-only-clip"
results, _ = client.scroll(
    collection_name=collection_name,
    limit=3,
    with_payload=True,
)

# Convert to serializable format
output = []
for point in results:
    output.append({
        "id": point.id,
        "payload": point.payload
    })

# Save to JSON
with open("sample_payloads.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Saved {len(output)} sample payloads to sample_payloads.json")
print(f"\nFirst product payload keys: {list(output[0]['payload'].keys())}")
