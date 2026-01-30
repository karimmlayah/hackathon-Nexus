"""
Save user interactions (search, wishlist, cart, view, purchase) to SQLite (Django).
Used so recommendations can be driven by per-account behaviour stored in user_interactions.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Map API type to Django UserInteraction.INTERACTION_TYPES
TYPE_MAP = {
    "view": "view",
    "click": "click",
    "cart": "add_to_cart",
    "wishlist": "wishlist",
    "purchase": "purchase",
    "search": "search",
}


def save_interaction_to_db(user_email: str, interaction_type: str, product_id: str) -> bool:
    """
    Save one interaction to Django SQLite (user_interactions table).
    Returns True if saved, False if skipped (e.g. user not found).
    """
    try:
        from django.contrib.auth.models import User
        from rag_app.models import UserInteraction, Product
        from rag_app.core.database import get_deterministic_id
        from rag_app.services.cart_service import _get_or_create_product_from_qdrant
    except Exception as e:
        logger.warning("Django not available for interaction storage: %s", e)
        return False

    user = User.objects.filter(email=user_email.strip()).first()
    if not user:
        user = User.objects.filter(username=user_email.strip()).first()
    if not user:
        logger.debug("No Django user for email %s, skip saving interaction", user_email)
        return False

    itype = TYPE_MAP.get((interaction_type or "").strip().lower(), "view")

    if itype == "search":
        UserInteraction.objects.create(
            user=user,
            product=None,
            interaction_type="search",
            metadata={"query": (product_id or "").strip()},
        )
        logger.info("Saved search interaction for %s: query=%s", user_email, (product_id or "")[:50])
        return True

    if not (product_id and str(product_id).strip()):
        return False

    qdrant_id = get_deterministic_id(str(product_id).strip())
    product = Product.objects.filter(qdrant_id=qdrant_id).first()
    if not product:
        product = _get_or_create_product_from_qdrant(qdrant_id)
    if not product:
        logger.debug("Product not found for id=%s (qdrant_id=%s), skip interaction", product_id, qdrant_id)
        return False

    UserInteraction.objects.create(
        user=user,
        product=product,
        interaction_type=itype,
        metadata={},
    )
    logger.info("Saved %s interaction for %s on product %s", itype, user_email, product.name[:50])
    return True
