import sys
import os
import logging
from qdrant_client.http import models

# Add root directory to path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

from rag_app.core.database import get_qdrant_client
from rag_app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def inspect_product_payload():
    try:
        client = get_qdrant_client()
        collection_name = settings.COLLECTION_NAME
        
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=1,
            with_payload=True,
            with_vectors=False
        )
        
        if not points:
            logger.error("No products found.")
            return

        p = points[0]
        logger.info(f"Product ID: {p.id}")
        logger.info(f"Payload: {p.payload}")
            
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    inspect_product_payload()
