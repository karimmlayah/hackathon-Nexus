from qdrant_client import QdrantClient
from qdrant_client.http import models
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import settings
import logging
import time

logger = logging.getLogger(__name__)

# Initialize Qdrant Client with timeout and retry handling
def create_qdrant_client(max_retries: int = 3) -> QdrantClient:
    """
    Creates a Qdrant client with retry logic for transient failures.
    """
    for attempt in range(max_retries):
        try:
            client = QdrantClient(
                url=settings.QDRANT_URL if settings.QDRANT_URL else ":memory:",
                api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
                timeout=10.0  # 10 second timeout for operations
            )
            # Test connection
            client.get_collections()
            logger.info("✅ Successfully connected to Qdrant")
            return client
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Connection attempt {attempt + 1} failed. Retrying in {wait_time}s: {str(e)}")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to connect to Qdrant after {max_retries} attempts")
                raise Exception(f"Unable to connect to Qdrant at {settings.QDRANT_URL}")
    
    raise Exception("Failed to create Qdrant client")
# Initialize client at module load
try:
    client = create_qdrant_client()
except Exception as e:
    logger.error(f"Critical: {str(e)}")
    client = None

def get_qdrant_client() -> QdrantClient:
    """
    Returns the Qdrant client. Raises an exception if connection failed.
    """
    if client is None:
        raise Exception(
            "Qdrant client is not initialized. Check QDRANT_URL and QDRANT_API_KEY in your .env file."
        )
    return client

def ensure_collection(vector_size: int = 384):
    """Ensures the collection exists with the correct configuration."""
    if client is None:
        logger.warning("Cannot ensure collection: Qdrant client not initialized")
        return
    
    try:
        if not client.collection_exists(settings.COLLECTION_NAME):
            client.create_collection(
                collection_name=settings.COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"✅ Created collection '{settings.COLLECTION_NAME}' with vector size {vector_size}")
        else:
            logger.info(f"✅ Collection '{settings.COLLECTION_NAME}' already exists")
    except Exception as e:
        logger.error(f"Failed to ensure collection: {str(e)}")
