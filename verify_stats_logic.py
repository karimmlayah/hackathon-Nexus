import sys
import os
sys.path.append(os.getcwd())
from rag_app.core.database import get_qdrant_client
from rag_app.core.config import settings
from qdrant_client.http import models

try:
    client = get_qdrant_client()
    print(f"Connected to Qdrant at {settings.QDRANT_URL}")
    print(f"Collection: {settings.COLLECTION_NAME}")

    print("1. Total Products (Exact)")
    count_result = client.count(collection_name=settings.COLLECTION_NAME, exact=True)
    total_products = count_result.count
    print(f"Total Products: {total_products}")

    print("2. In Stock (Exact filter)")
    in_stock_result = client.count(
        collection_name=settings.COLLECTION_NAME,
        count_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="availability",
                    match=models.MatchValue(value="In Stock")
                )
            ]
        ),
        exact=True
    )
    in_stock = in_stock_result.count
    print(f"In Stock: {in_stock}")

    print("3. Categories & Brands (Approximation via Scroll)")
    limit = 1000
    points, _ = client.scroll(
        collection_name=settings.COLLECTION_NAME,
        limit=limit,
        with_payload=["category", "brand", "manufacturer", "availability"],
        with_vectors=False
    )
    print(f"Scrolled {len(points)} points")

except Exception as e:
    print(f"Error: {e}")
