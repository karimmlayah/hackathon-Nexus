import sys
import os
sys.path.append(os.getcwd())
from rag_app.core.database import get_qdrant_client
from rag_app.core.config import settings
from qdrant_client.http import models

client = get_qdrant_client()
print("Connected")

try:
    print("Step 1: Count")
    c = client.count(settings.COLLECTION_NAME, exact=True)
    print(f"Count: {c.count}")
except Exception as e:
    print(f"Step 1 Failed: {e}")

try:
    print("Step 2: Filtered Count")
    f = models.Filter(
        must=[
            models.FieldCondition(
                key="availability",
                match=models.MatchValue(value="In Stock")
            )
        ]
    )
    c2 = client.count(settings.COLLECTION_NAME, count_filter=f, exact=True)
    print(f"Filtered Count: {c2.count}")
except Exception as e:
    print(f"Step 2 Failed: {e}")

try:
    print("Step 3: Scroll")
    p, _ = client.scroll(settings.COLLECTION_NAME, limit=100)
    print(f"Scroll: {len(p)}")
except Exception as e:
    print(f"Step 3 Failed: {e}")
