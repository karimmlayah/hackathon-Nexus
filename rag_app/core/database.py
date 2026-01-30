from qdrant_client import QdrantClient
from qdrant_client.http import models
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from config import settings
import logging
import time
import hashlib

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
                timeout=30.0  # Increased timeout for complex searches
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
    """Ensures the collections exist with the correct configuration."""
    if client is None:
        logger.warning("Cannot ensure collection: Qdrant client not initialized")
        return
    
    try:
        # 1. Product Collection (with named vectors)
        if not client.collection_exists(settings.COLLECTION_NAME):
            client.create_collection(
                collection_name=settings.COLLECTION_NAME,
                vectors_config={
                    settings.VECTOR_NAME: models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    )
                }
            )
            logger.info(f"✅ Created product collection '{settings.COLLECTION_NAME}' with vector '{settings.VECTOR_NAME}'")
            
            # Create payload indexes for filtering
            client.create_payload_index(collection_name=settings.COLLECTION_NAME, field_name="price", field_schema=models.PayloadSchemaType.FLOAT)
            client.create_payload_index(collection_name=settings.COLLECTION_NAME, field_name="in_stock", field_schema=models.PayloadSchemaType.BOOL)
        else:
            # Ensure indexes exist even if collection does too
            try:
                client.create_payload_index(collection_name=settings.COLLECTION_NAME, field_name="price", field_schema=models.PayloadSchemaType.FLOAT)
            except Exception: pass
            try:
                client.create_payload_index(collection_name=settings.COLLECTION_NAME, field_name="in_stock", field_schema=models.PayloadSchemaType.BOOL)
            except Exception: pass
        
        # 2. User Collection (unnamed vector)
        user_collection = "users"
        if not client.collection_exists(user_collection):
            client.create_collection(
                collection_name=user_collection,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"✅ Created user collection '{user_collection}'")
            
            # Create payload index for user_email
            client.create_payload_index(
                collection_name=user_collection,
                field_name="user_email",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            logger.info(f"✅ Created payload index for 'user_email' in '{user_collection}'")
        else:
            # Even if collection exists, try to ensure index exists
            # (Note: create_payload_index is idempotent if index already exists in many Qdrant versions, 
            # but we can wrap it in try-except)
            try:
                client.create_payload_index(
                    collection_name=user_collection,
                    field_name="user_email",
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
            except Exception:
                pass
            
    except Exception as e:
        logger.error(f"Failed to ensure collection: {str(e)}")

def get_deterministic_id(source_id: str) -> int:
    """
    Creates a deterministic integer ID from a string in the range [0, 10^18].
    This ensures that the same string ID always maps to the same Qdrant point ID
    regardless of process or environment.
    """
    if str(source_id).isdigit():
        return int(source_id)
    
    # Use SHA-256 for deterministic hashing
    hash_object = hashlib.sha256(str(source_id).encode())
    hash_hex = hash_object.hexdigest()
    # Convert hex to int and take modulo to stay within int64 range for Qdrant
    return int(hash_hex, 16) % (10**18)
