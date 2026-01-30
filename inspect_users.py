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

def inspect_users():
    try:
        client = get_qdrant_client()
        
        if not client.collection_exists(USER_COLLECTION_NAME):
            logger.error(f"Collection '{USER_COLLECTION_NAME}' does NOT exist.")
            return

        # Scroll to see some users
        points, _ = client.scroll(
            collection_name=USER_COLLECTION_NAME,
            limit=10,
            with_payload=True,
            with_vectors=False
        )
        
        logger.info(f"Found {len(points)} users in '{USER_COLLECTION_NAME}'.")
        for p in points:
            logger.info(f"User Point ID: {p.id}")
            logger.info(f"Payload: {p.payload}")
            
    except Exception as e:
        logger.error(f"❌ Error inspecting users collection: {str(e)}")

if __name__ == "__main__":
    inspect_users()
