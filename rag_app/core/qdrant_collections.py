"""
Qdrant Collections Manager
Manages multiple Qdrant collections for products, user profiles, and interactions
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class QdrantCollections:
    """Manages Qdrant collections for the recommendation system"""
    
    # Collection names
    PRODUCTS = "products"
    USER_PROFILES = "user_profiles"
    USER_INTERACTIONS = "user_interactions"
    
    def __init__(self, client: QdrantClient):
        self.client = client
    
    def ensure_all_collections(self, vector_size: int = 384):
        """Ensure all required collections exist"""
        self.ensure_products_collection(vector_size)
        self.ensure_user_profiles_collection(vector_size)
        self.ensure_user_interactions_collection(vector_size)
    
    def ensure_products_collection(self, vector_size: int = 384):
        """Ensure products collection exists (should already exist)"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.PRODUCTS not in collection_names:
                logger.warning(f"Products collection '{self.PRODUCTS}' does not exist!")
            else:
                logger.info(f"✅ Products collection '{self.PRODUCTS}' exists")
        except Exception as e:
            logger.error(f"Error checking products collection: {e}")
    
    def ensure_user_profiles_collection(self, vector_size: int = 384):
        """
        Ensure user_profiles collection exists
        Stores user behavior vectors for collaborative filtering
        
        Vector: Average embedding of products the user has interacted with
        Payload: {
            "user_id": str,
            "email": str,
            "interaction_count": int,
            "categories_viewed": list[str],
            "avg_price_range": float,
            "last_updated": str (ISO timestamp)
        }
        """
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.USER_PROFILES not in collection_names:
                self.client.create_collection(
                    collection_name=self.USER_PROFILES,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created user_profiles collection with vector size {vector_size}")
            else:
                logger.info(f"✅ User profiles collection '{self.USER_PROFILES}' already exists")
        except Exception as e:
            logger.error(f"Error creating user_profiles collection: {e}")
            raise
    
    def ensure_user_interactions_collection(self, vector_size: int = 384):
        """
        Ensure user_interactions collection exists
        Stores individual user interactions with products
        
        Vector: Product embedding (copied from products collection)
        Payload: {
            "user_id": str,
            "product_id": str,
            "interaction_type": str (view, click, add_to_cart, purchase, favorite),
            "timestamp": str (ISO timestamp),
            "product_name": str,
            "product_category": str,
            "product_price": float
        }
        """
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.USER_INTERACTIONS not in collection_names:
                self.client.create_collection(
                    collection_name=self.USER_INTERACTIONS,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created user_interactions collection with vector size {vector_size}")
            else:
                logger.info(f"✅ User interactions collection '{self.USER_INTERACTIONS}' already exists")
        except Exception as e:
            logger.error(f"Error creating user_interactions collection: {e}")
            raise
