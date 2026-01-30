"""
User Profile Service
Manages user behavior profiles for collaborative filtering
"""
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from datetime import datetime
from typing import List, Dict, Optional
import numpy as np
import logging
import hashlib

logger = logging.getLogger(__name__)

class UserProfileService:
    """Service for managing user behavior profiles"""
    
    def __init__(self, client: QdrantClient, collection_name: str = "user_profiles"):
        self.client = client
        self.collection_name = collection_name
    
    def _generate_user_point_id(self, user_id: str) -> str:
        """Generate consistent point ID for a user"""
        return hashlib.md5(user_id.encode()).hexdigest()
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile from Qdrant"""
        try:
            point_id = self._generate_user_point_id(user_id)
            
            # Try to retrieve the point
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id],
                with_payload=True,
                with_vectors=True
            )
            
            if points:
                return {
                    "id": point_id,
                    "vector": points[0].vector,
                    "payload": points[0].payload
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user profile for {user_id}: {e}")
            return None
    
    async def update_user_profile(
        self,
        user_id: str,
        interaction_vectors: List[np.ndarray],
        interaction_data: List[Dict]
    ):
        """
        Update user profile based on new interactions
        
        Args:
            user_id: User identifier
            interaction_vectors: List of product embedding vectors
            interaction_data: List of interaction metadata (category, price, etc.)
        """
        try:
            point_id = self._generate_user_point_id(user_id)
            
            # Calculate average vector (user's taste profile)
            if not interaction_vectors:
                logger.warning(f"No interaction vectors for user {user_id}")
                return
            
            avg_vector = np.mean(interaction_vectors, axis=0).tolist()
            
            # Aggregate interaction data
            categories = set()
            prices = []
            
            for data in interaction_data:
                if "category" in data:
                    categories.add(data["category"])
                if "price" in data and data["price"]:
                    try:
                        # Extract numeric price
                        price_str = str(data["price"]).replace(",", "").replace("DT", "").strip()
                        price = float(price_str.split()[0])
                        prices.append(price)
                    except:
                        pass
            
            avg_price = np.mean(prices) if prices else 0
            
            # Create or update user profile
            payload = {
                "user_id": user_id,
                "interaction_count": len(interaction_vectors),
                "categories_viewed": list(categories),
                "avg_price_range": float(avg_price),
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Upsert the point
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=avg_vector,
                        payload=payload
                    )
                ]
            )
            
            logger.info(f"✅ Updated user profile for {user_id} with {len(interaction_vectors)} interactions")
            
        except Exception as e:
            logger.error(f"Error updating user profile for {user_id}: {e}")
            raise
    
    async def find_similar_users(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        Find users with similar behavior patterns using vector similarity
        
        Args:
            user_id: Current user ID
            limit: Number of similar users to return
            
        Returns:
            List of similar user profiles with similarity scores
        """
        try:
            # Get current user's profile
            user_profile = await self.get_user_profile(user_id)
            
            if not user_profile:
                logger.warning(f"No profile found for user {user_id}")
                return []
            
            # Search for similar users
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=user_profile["vector"],
                limit=limit + 1,  # +1 because current user will be in results
                with_payload=True
            )
            
            # Filter out the current user and return similar users
            similar_users = []
            for result in search_results:
                if result.payload.get("user_id") != user_id:
                    similar_users.append({
                        "user_id": result.payload.get("user_id"),
                        "similarity_score": result.score,
                        "interaction_count": result.payload.get("interaction_count", 0),
                        "categories": result.payload.get("categories_viewed", [])
                    })
            
            logger.info(f"Found {len(similar_users)} similar users for {user_id}")
            return similar_users[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar users for {user_id}: {e}")
            return []
    
    async def get_user_interaction_count(self, user_id: str) -> int:
        """Get the number of interactions a user has made"""
        try:
            profile = await self.get_user_profile(user_id)
            if profile and "payload" in profile:
                return profile["payload"].get("interaction_count", 0)
            return 0
        except Exception as e:
            logger.error(f"Error getting interaction count for {user_id}: {e}")
            return 0
