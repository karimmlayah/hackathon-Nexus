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

def setup_users_collection():
    try:
        client = get_qdrant_client()
        
        if not client.collection_exists(USER_COLLECTION_NAME):
            logger.info(f"Creating collection '{USER_COLLECTION_NAME}'...")
            client.create_collection(
                collection_name=USER_COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=384, # Same as products
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"✅ Collection '{USER_COLLECTION_NAME}' created.")
        else:
            logger.info(f"✅ Collection '{USER_COLLECTION_NAME}' already exists.")
            
    except Exception as e:
        logger.error(f"❌ Failed to setup users collection: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    setup_users_collection()
