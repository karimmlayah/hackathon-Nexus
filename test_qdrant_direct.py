import sys
import os
import logging
from qdrant_client.http import models

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_app.core.database import get_qdrant_client
from rag_app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_COLLECTION_NAME = "users"

def test_qdrant_write():
    try:
        client = get_qdrant_client()
        
        test_id = 999999
        test_payload = {"user_email": "test_direct@example.com", "test": True}
        # Fake 384-dim vector
        import random
        test_vector = [random.uniform(-1, 1) for _ in range(384)]
        
        logger.info(f"Upserting test user {test_id}...")
        client.upsert(
            collection_name=USER_COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=test_id,
                    vector=test_vector,
                    payload=test_payload
                )
            ]
        )
        logger.info("✅ Upsert successful.")
        
        # Now try to retrieve it
        logger.info("Retrieving test user...")
        points = client.retrieve(
            collection_name=USER_COLLECTION_NAME,
            ids=[test_id],
            with_payload=True
        )
        
        if points:
            logger.info(f"✅ Retrieved! Payload: {points[0].payload}")
        else:
            logger.error("❌ Failed to retrieve after upsert!")
            
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_qdrant_write()
