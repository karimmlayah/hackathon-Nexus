from typing import List, Dict, Any, Optional
import logging
import sys
import os
import time
from datetime import datetime
from qdrant_client.http import models

from rag_app.core.database import get_qdrant_client, get_deterministic_id
from rag_app.core.config import settings
from rag_app.core.llm import get_embedding
from rag_app.core import qdrant_ops as qdrant_tool

logger = logging.getLogger(__name__)

USER_COLLECTION = "users"
PRODUCT_COLLECTION = settings.COLLECTION_NAME

# Influence weights for different interaction types
INTERACTION_WEIGHTS = {
    "view": 0.1,
    "wishlist": 0.3,
    "cart": 0.5,
    "purchase": 1.0
}

class RecommendationService:
    def __init__(self):
        self.client = get_qdrant_client()

    async def capture_interaction(self, user_email: str, interaction_type: str, product_id: str):
        """
        AI Interaction Agent & Financial Context Agent logic.
        Captures user behavior and updates their preference profile in real-time.
        """
        try:
            logger.info(f"Processing {interaction_type} for user {user_email} on product {product_id}")
            
            # 1. Get Product Data from Qdrant
            try:
                # product_id might be int or string, Qdrant ids are often ints in this project
                # We need a deterministic mapping from string to int
                pid = get_deterministic_id(product_id)

                product_points = self.client.retrieve(
                    collection_name=PRODUCT_COLLECTION,
                    ids=[pid],
                    with_vectors=True,
                    with_payload=True
                )
                
                if not product_points:
                    logger.warning(f"Product {product_id} (mapped ID: {pid}) not found in Qdrant.")
                    return
                
                product = product_points[0]
                # Extract vector (handle named vectors)
                if isinstance(product.vector, dict):
                    product_vector = product.vector.get(settings.VECTOR_NAME)
                else:
                    product_vector = product.vector

                if not product_vector:
                    logger.warning(f"Product {product_id} has no vector '{settings.VECTOR_NAME}'")
                    return

                product_payload = product.payload
                product_price = float(product_payload.get("price") or product_payload.get("final_price") or 0.0)
                product_category = product_payload.get("category") or "General"
            except Exception as e:
                logger.error(f"Error retrieving product {product_id}: {str(e)}")
                return

            # 2. Get User Profile
            user_points = self.client.scroll(
                collection_name=USER_COLLECTION,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key="user_email", match=models.MatchValue(value=user_email))]
                ),
                limit=1,
                with_vectors=True,
                with_payload=True
            )[0]

            user_profile = user_points[0] if user_points else None
            
            weight = INTERACTION_WEIGHTS.get(interaction_type, 0.1)
            
            if not user_profile:
                # Cold start for this user
                new_vector = product_vector
                new_payload = {
                    "user_email": user_email,
                    "budget": {"min": product_price * 0.7, "max": product_price * 1.3, "confidence": 0.3},
                    "preferred_categories": {product_category: 1},
                    "financial_context": {"preferred_payment": None, "affordability": "medium"},
                    "interactions": [{"id": product_id, "type": interaction_type, "ts": time.time()}],
                    "last_updated": datetime.utcnow().isoformat()
                }
                user_point_id = get_deterministic_id(user_email)
            else:
                # Update existing profile
                old_vector = user_profile.vector
                # Weighted average: new_vec = (old_vec * (1-w)) + (prod_vec * w)
                new_vector = [(ov * (1 - weight)) + (pv * weight) for ov, pv in zip(old_vector, product_vector)]
                
                payload = user_profile.payload
                
                # Update budget (Financial Context Agent logic)
                budget = payload.get("budget", {"min": 0, "max": 10000, "confidence": 0.1})
                if interaction_type == "purchase":
                    # Heavy weight on purchase price
                    budget["min"] = (budget["min"] * 0.5) + (product_price * 0.5 * 0.7)
                    budget["max"] = (budget["max"] * 0.5) + (product_price * 0.5 * 1.5)
                    budget["confidence"] = min(budget.get("confidence", 0) + 0.2, 1.0)
                else:
                    # Light weight on views/clicks
                    budget["min"] = min(budget["min"], product_price * 0.5)
                    budget["max"] = max(budget["max"], product_price * 1.5)
                    budget["confidence"] = min(budget.get("confidence", 0) + 0.05, 1.0)
                
                # Update categories
                cats = payload.get("preferred_categories", {})
                cats[product_category] = cats.get(product_category, 0) + 1
                
                # Update interaction history
                history = payload.get("interactions", [])
                history.append({"id": product_id, "type": interaction_type, "ts": time.time()})
                history = history[-20:] # Keep last 20
                
                new_payload = payload
                new_payload["budget"] = budget
                new_payload["preferred_categories"] = cats
                new_payload["interactions"] = history
                new_payload["last_updated"] = datetime.utcnow().isoformat()
                user_point_id = user_profile.id

            # 3. Upsert into Qdrant
            self.client.upsert(
                collection_name=USER_COLLECTION,
                points=[
                    models.PointStruct(
                        id=user_point_id,
                        vector=new_vector,
                        payload=new_payload
                    )
                ]
            )
            logger.info(f"✅ Successfully updated user profile for {user_email}")

        except Exception as e:
            logger.error(f"Failed to capture interaction: {str(e)}", exc_info=True)

    async def get_recommendations(self, user_email: str, limit: int = 4) -> List[Dict[str, Any]]:
        """
        AI Recommendation Agent logic.
        Uses the user profile to find semantically similar products and applies constraints.
        """
        try:
            # 1. Get User Profile
            user_points = self.client.scroll(
                collection_name=USER_COLLECTION,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key="user_email", match=models.MatchValue(value=user_email))]
                ),
                limit=1,
                with_vectors=True,
                with_payload=True
            )[0]

            if not user_points:
                logger.info(f"No profile for {user_email}, falling back to trending.")
                return await self.get_trending_products(limit)

            user_profile = user_points[0]
            user_vector = user_profile.vector
            budget = user_profile.payload.get("budget", {})
            
            # 2. Vector Search in Products with Hard Constraints
            # Hard constraints: Price range and Availability
            price_min = budget.get("min", 0)
            price_max = budget.get("max", 1000000)
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="price",
                        range=models.Range(
                            gte=max(0, float(price_min) * 0.5),
                            lte=float(price_max) * 2.0
                        )
                    )
                ]
            )

            logger.info(f"Searching with filter: {query_filter}")
            
            # Use the high-level search_products from qdrant.py
            personalized = qdrant_tool.search_products(
                client=self.client,
                collection_name=PRODUCT_COLLECTION,
                query_vector=user_vector,
                limit=limit * 2, # Fetch more for re-ranking
                vector_name=settings.VECTOR_NAME,
                query_filter=query_filter
            )
            
            logger.info(f"Found {len(personalized)} products after semantic search")
            
            # Ensure brand diversity and limit
            personalized = qdrant_tool.rerank_by_brand_diversity(personalized)[:limit]
            
            return personalized

        except Exception as e:
            logger.error(f"Failed to get recommendations: {str(e)}", exc_info=True)
            return await self.get_trending_products(limit)

    async def get_trending_products(self, limit: int = 4) -> List[Dict[str, Any]]:
        """Fallback for guests or new users."""
        try:
            # Simple fallback: products with highest ratings or highest discounts
            points, _ = self.client.scroll(
                collection_name=PRODUCT_COLLECTION,
                limit=50,
                with_payload=True
            )
            products = [qdrant_tool.map_qdrant_product(p) for p in points]
            
            # Sort by rating and pick random top ones
            trending = sorted(products, key=lambda x: x.get("rating", 0), reverse=True)
            import random
            return random.sample(trending[:20], min(limit, len(trending)))
        except Exception as e:
            logger.error(f"Trending fallback failed: {str(e)}")
            return []

# Singleton instance
recommendation_service = RecommendationService()
