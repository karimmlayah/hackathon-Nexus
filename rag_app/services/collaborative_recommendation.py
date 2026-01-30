"""
Enhanced Recommendation Service with Collaborative Filtering
Combines existing user profile system with collaborative filtering
"""
from typing import List, Dict, Any, Optional
import logging
import numpy as np
from datetime import datetime
from qdrant_client.http import models

from rag_app.core.database import get_qdrant_client, get_deterministic_id
from rag_app.core.config import settings
from rag_app.core import qdrant_ops as qdrant_tool

logger = logging.getLogger(__name__)

USER_COLLECTION = "users"
PRODUCT_COLLECTION = settings.COLLECTION_NAME

# Weights for hybrid recommendation
WEIGHT_PERSONAL = 0.40  # Based on user's own profile
WEIGHT_COLLABORATIVE = 0.60  # Based on similar users

class CollaborativeRecommendationService:
    """Enhanced recommendation service with collaborative filtering"""
    
    def __init__(self):
        self.client = get_qdrant_client()
    
    async def get_recommendations_with_collaborative(
        self,
        user_email: str,
        limit: int = 6,
        include_explanation: bool = True,
        budget_max: Optional[float] = None,
        budget_min: Optional[float] = None,
        availability: Optional[bool] = None,
        payment_method: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Constraint-aware recommendations:
        - User behavior (clicks, cart, favorites, purchases) from Qdrant users collection
        - Constraints: budget (affordability), availability, payment (optional)
        - Hybrid: personal + collaborative filtering for higher engagement (CTR, add-to-cart)
        """
        try:
            # Get user profile from Qdrant users collection
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
                logger.info(f"No profile for {user_email}, using trending products")
                return await self._get_trending_products(limit, budget_max=budget_max, budget_min=budget_min, availability=availability)
            
            user_profile = user_points[0]
            user_vector = user_profile.vector
            user_payload = user_profile.payload
            
            # Constraint overrides from request (constraint-aware)
            constraints = {
                "budget_max": budget_max,
                "budget_min": budget_min,
                "availability": availability,
                "payment_method": payment_method,
            }
            
            # Check interaction count
            interaction_count = len(user_payload.get("interactions", []))
            
            if interaction_count < 3:
                logger.info(f"Cold start for {user_email} ({interaction_count} interactions)")
                return await self._get_personal_recommendations(user_profile, limit, constraints=constraints)
            
            logger.info(f"Hybrid recommendations for {user_email} ({interaction_count} interactions)")
            
            personal_recs = await self._get_personal_recommendations(user_profile, limit * 2, constraints=constraints)
            collaborative_recs = await self._get_collaborative_recommendations(
                user_email,
                user_vector,
                limit * 2
            )
            
            # Apply budget constraint to collaborative results (constraint compliance)
            if budget_max is not None:
                collaborative_recs = [r for r in collaborative_recs if float(r.get("price") or 0) <= budget_max]
            if budget_min is not None:
                collaborative_recs = [r for r in collaborative_recs if float(r.get("price") or 0) >= budget_min]
            
            combined_recs = self._combine_recommendations(
                personal_recs,
                collaborative_recs,
                user_payload
            )
            
            if include_explanation:
                for rec in combined_recs:
                    rec["explanation"] = self._generate_explanation(rec)
            
            return combined_recs[:limit]
            
        except Exception as e:
            logger.error(f"Error in collaborative recommendations: {e}", exc_info=True)
            return await self._get_trending_products(limit, budget_max=budget_max, budget_min=budget_min, availability=availability)
    
    async def _get_personal_recommendations(
        self,
        user_profile: Any,
        limit: int,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Constraint-aware: user profile + optional budget/availability overrides."""
        try:
            user_vector = user_profile.vector
            budget = user_profile.payload.get("budget", {})
            constraints = constraints or {}
            
            # Constraint-aware: request overrides take precedence (budget/affordability)
            price_min = constraints.get("budget_min")
            if price_min is None:
                price_min = budget.get("min", 0)
            price_max = constraints.get("budget_max")
            if price_max is None:
                price_max = budget.get("max", 1000000)
            
            must_conditions = [
                models.FieldCondition(
                    key="price",
                    range=models.Range(
                        gte=max(0, float(price_min) * 0.5),
                        lte=float(price_max) * 2.0 if price_max else 1e9
                    )
                )
            ]
            if constraints.get("availability") is True:
                must_conditions.append(
                    models.FieldCondition(
                        key="availability",
                        match=models.MatchValue(value="In Stock")
                    )
                )
            query_filter = models.Filter(must=must_conditions)
            
            # Vector search
            personalized = qdrant_tool.search_products(
                client=self.client,
                collection_name=PRODUCT_COLLECTION,
                query_vector=user_vector,
                limit=limit,
                vector_name=settings.VECTOR_NAME,
                query_filter=query_filter
            )
            
            # Add source tag
            for rec in personalized:
                rec["recommendation_source"] = "personal"
                rec["personal_score"] = rec.get("score", 0.5)
            
            return personalized
            
        except Exception as e:
            logger.error(f"Error in personal recommendations: {e}")
            return []
    
    async def _get_collaborative_recommendations(
        self,
        user_email: str,
        user_vector: List[float],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get recommendations based on similar users"""
        try:
            # 1. Find similar users using vector search
            similar_users = self.client.search(
                collection_name=USER_COLLECTION,
                query_vector=user_vector,
                limit=21,  # +1 because current user will be in results
                with_payload=True
            )
            
            # Filter out current user
            similar_users = [
                u for u in similar_users
                if u.payload.get("user_email") != user_email
            ][:20]
            
            if not similar_users:
                logger.warning(f"No similar users found for {user_email}")
                return []
            
            logger.info(f"Found {len(similar_users)} similar users for {user_email}")
            
            # 2. Collect products liked by similar users
            product_scores = {}  # product_id -> {score, count, similarity_sum}
            
            for similar_user in similar_users:
                similarity_score = similar_user.score
                interactions = similar_user.payload.get("interactions", [])
                
                # Weight interactions by type
                for interaction in interactions[-10:]:  # Last 10 interactions
                    product_id = interaction.get("id")
                    interaction_type = interaction.get("type", "view")
                    
                    # Weight by interaction type
                    type_weight = {
                        "purchase": 1.0,
                        "cart": 0.7,
                        "wishlist": 0.5,
                        "view": 0.2
                    }.get(interaction_type, 0.1)
                    
                    # Combined score: similarity * interaction_weight
                    score = similarity_score * type_weight
                    
                    if product_id not in product_scores:
                        product_scores[product_id] = {
                            "score": 0,
                            "count": 0,
                            "similarity_sum": 0
                        }
                    
                    product_scores[product_id]["score"] += score
                    product_scores[product_id]["count"] += 1
                    product_scores[product_id]["similarity_sum"] += similarity_score
            
            # 3. Get product details and create recommendations
            recommendations = []
            
            for product_id, data in product_scores.items():
                try:
                    # Get product from Qdrant
                    pid = get_deterministic_id(product_id)
                    product_points = self.client.retrieve(
                        collection_name=PRODUCT_COLLECTION,
                        ids=[pid],
                        with_payload=True
                    )
                    
                    if not product_points:
                        continue
                    
                    product = qdrant_tool.map_qdrant_product(product_points[0])
                    
                    # Calculate final score
                    avg_similarity = data["similarity_sum"] / data["count"]
                    popularity = data["count"] / len(similar_users)
                    final_score = (data["score"] / data["count"]) * (1 + popularity)
                    
                    product["recommendation_source"] = "collaborative"
                    product["collaborative_score"] = final_score
                    product["liked_by_similar_users"] = data["count"]
                    product["avg_user_similarity"] = avg_similarity
                    product["score"] = final_score
                    
                    recommendations.append(product)
                    
                except Exception as e:
                    logger.error(f"Error processing product {product_id}: {e}")
                    continue
            
            # Sort by score
            recommendations.sort(key=lambda x: x.get("score", 0), reverse=True)
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error in collaborative filtering: {e}", exc_info=True)
            return []
    
    def _combine_recommendations(
        self,
        personal_recs: List[Dict],
        collaborative_recs: List[Dict],
        user_payload: Dict
    ) -> List[Dict]:
        """Combine personal and collaborative recommendations with weighted scoring"""
        
        # Get already viewed products
        viewed_products = {
            interaction.get("id")
            for interaction in user_payload.get("interactions", [])
        }
        
        # Combine recommendations
        product_map = {}
        
        # Add personal recommendations
        for rec in personal_recs:
            product_id = rec.get("id")
            if product_id in viewed_products:
                continue
            
            product_map[product_id] = rec.copy()
            product_map[product_id]["final_score"] = rec.get("personal_score", 0.5) * WEIGHT_PERSONAL
            product_map[product_id]["sources"] = ["personal"]
        
        # Add collaborative recommendations
        for rec in collaborative_recs:
            product_id = rec.get("id")
            if product_id in viewed_products:
                continue
            
            if product_id in product_map:
                # Product appears in both - boost score
                product_map[product_id]["final_score"] += rec.get("collaborative_score", 0.5) * WEIGHT_COLLABORATIVE
                product_map[product_id]["sources"].append("collaborative")
                product_map[product_id]["liked_by_similar_users"] = rec.get("liked_by_similar_users", 0)
            else:
                product_map[product_id] = rec.copy()
                product_map[product_id]["final_score"] = rec.get("collaborative_score", 0.5) * WEIGHT_COLLABORATIVE
                product_map[product_id]["sources"] = ["collaborative"]
        
        # Convert to list and sort
        combined = list(product_map.values())
        combined.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        
        return combined
    
    def _generate_explanation(self, recommendation: Dict) -> str:
        """Generate explanation for why this product is recommended"""
        sources = recommendation.get("sources", [])
        
        if "collaborative" in sources and "personal" in sources:
            liked_by = recommendation.get("liked_by_similar_users", 0)
            return f"Correspond à vos goûts et aimé par {liked_by} utilisateurs similaires"
        elif "collaborative" in sources:
            liked_by = recommendation.get("liked_by_similar_users", 0)
            return f"Aimé par {liked_by} utilisateurs avec des goûts similaires"
        elif "personal" in sources:
            return "Basé sur vos préférences et historique"
        else:
            return "Recommandé pour vous"
    
    async def _get_trending_products(
        self,
        limit: int,
        budget_max: Optional[float] = None,
        budget_min: Optional[float] = None,
        availability: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Fallback: get trending/popular products (constraint-aware)."""
        try:
            points, _ = self.client.scroll(
                collection_name=PRODUCT_COLLECTION,
                limit=100,
                with_payload=True
            )
            products = [qdrant_tool.map_qdrant_product(p) for p in points]

            # Constraint-aware: filter by budget
            if budget_max is not None:
                products = [p for p in products if float(p.get("price") or 0) <= budget_max]
            if budget_min is not None:
                products = [p for p in products if float(p.get("price") or 0) >= budget_min]
            if availability is True:
                products = [p for p in products if (p.get("availability") or "").lower() in ("in stock", "in_stock", "available")]

            # Sort by rating
            trending = sorted(products, key=lambda x: x.get("rating", 0), reverse=True)

            # Add explanation
            for product in trending[:limit]:
                product["explanation"] = "Produit populaire"
                product["sources"] = ["trending"]

            return trending[:limit]

        except Exception as e:
            logger.error(f"Error getting trending products: {e}")
            return []

# Singleton instance
collaborative_recommendation_service = CollaborativeRecommendationService()
