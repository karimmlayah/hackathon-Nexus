"""Comprehensive diagnostic for image search"""
import os
import json
from dotenv import load_dotenv
from qdrant import get_qdrant_client

load_dotenv()

client = get_qdrant_client()
collection_name = "nexus-multivector_3k_f"

stats = {}

try:
    # 1. Collection Info
    info = client.get_collection(collection_name)
    stats["collection_info"] = {
        "status": "found",
        "points_count": info.points_count,
        "vectors_config": str(info.config.params.vectors)
    }

    # 2. Get 5 sample points with vectors
    results, _ = client.scroll(
        collection_name=collection_name,
        limit=5,
        with_vectors=True,
        with_payload=True
    )
    
    stats["samples"] = []
    for p in results:
        v_keys = list(p.vector.keys()) if isinstance(p.vector, dict) else "not a dict"
        stats["samples"].append({
            "id": p.id,
            "title": p.payload.get("title", "No title")[:50],
            "vector_keys": v_keys,
            "image_vector_len": len(p.vector.get("image_dense", [])) if isinstance(p.vector, dict) else 0
        })

    # 3. Self-Search Test
    if results and "image_dense" in results[0].vector:
        target_point = results[0]
        query_v = target_point.vector["image_dense"]
        
        # Search using the vector we just pulled out
        search_res = client.query_points(
            collection_name=collection_name,
            query=query_v,
            using="image_dense",
            limit=5,
            with_payload=True
        ).points
        
        stats["self_search"] = {
            "query_id": target_point.id,
            "results": [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "title": hit.payload.get("title", "")[:50]
                } for hit in search_res
            ]
        }
        
        if search_res and search_res[0].id == target_point.id:
            stats["self_search"]["status"] = "SUCCESS"
        else:
            stats["self_search"]["status"] = "FAILED - Top hit is different"
    else:
        stats["self_search"] = {"status": "ERROR - No image_dense vector in samples"}

    with open("image_search_diagnostic.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print("Diagnostic complete. Results saved to image_search_diagnostic.json")

except Exception as e:
    print(f"Error during diagnostic: {e}")
    with open("diagnostic_error.txt", "w") as f:
        f.write(str(e))
