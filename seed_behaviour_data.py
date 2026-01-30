"""
Generate static behaviour data (clicks, favourites, purchases) and insert into SQLite (Django).
Uses rag_app.db in the project repo: auth_user, products, user_interactions.

Run from project root (with .env for Qdrant if syncing products):
  python seed_behaviour_data.py

No data is written to Qdrant; all behaviour is stored in local SQLite.
"""
import os
import sys
import random
import logging
from decimal import Decimal

# Project root
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
RAG_APP = os.path.join(ROOT, "rag_app")
if RAG_APP not in sys.path:
    sys.path.insert(0, RAG_APP)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Synthetic users (emails)
SYNTHETIC_USERS = [
    "alice@example.com",
    "bob@example.com",
    "carol@example.com",
    "dave@example.com",
    "eve@example.com",
    "frank@example.com",
    "grace@example.com",
    "henry@example.com",
    "iris@example.com",
    "jack@example.com",
]

# Interaction types and weights (Django UserInteraction.INTERACTION_TYPES)
INTERACTION_WEIGHTS = {
    "view": 0.45,
    "click": 0.15,
    "wishlist": 0.20,
    "add_to_cart": 0.15,
    "purchase": 0.05,
}
INTERACTION_TYPES = list(INTERACTION_WEIGHTS.keys())


def _weighted_choice():
    r = random.random()
    for itype, w in INTERACTION_WEIGHTS.items():
        r -= w
        if r <= 0:
            return itype
    return "view"


def setup_django():
    """Configure Django to use rag_app.db (same as app.py)."""
    import django
    from django.conf import settings
    if getattr(settings, "configured", False):
        return
    settings.configure(
        DEBUG=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": os.path.join(ROOT, "rag_app.db"),
            }
        },
        INSTALLED_APPS=["django.contrib.auth", "django.contrib.contenttypes", "rag_app"],
        SECRET_KEY="django-insecure-rag-app-cart-favorites",
        USE_TZ=True,
    )
    django.setup()


def ensure_users():
    """Create synthetic Django users if they don't exist."""
    from django.contrib.auth.models import User
    created = 0
    for email in SYNTHETIC_USERS:
        if not User.objects.filter(email=email).exists():
            User.objects.create_user(
                username=email,
                email=email,
                password="seed-demo-no-login",
                first_name=email.split("@")[0].capitalize(),
            )
            created += 1
    if created:
        logger.info("Created %d synthetic users in auth_user", created)
    return list(User.objects.filter(email__in=SYNTHETIC_USERS))


def fetch_and_sync_products(limit=500):
    """
    Scroll Qdrant product collection and sync into Django Product table (SQLite).
    Returns list of Django Product instances for seeding interactions.
    """
    from rag_app.core.database import get_qdrant_client
    from rag_app.core.config import settings
    from rag_app.models import Product

    client = get_qdrant_client()
    collection_name = settings.COLLECTION_NAME
    product_list = []
    next_offset = None
    batch_size = 256
    while len(product_list) < limit:
        points, next_offset = client.scroll(
            collection_name=collection_name,
            offset=next_offset,
            limit=batch_size,
            with_payload=True,
            with_vectors=False,
        )
        if not points:
            break
        for p in points:
            qdrant_id = int(p.id)
            payload = p.payload or {}
            try:
                price = float(payload.get("price") or payload.get("final_price") or 0)
            except (TypeError, ValueError):
                price = 0.0
            try:
                orig = payload.get("initial_price") or payload.get("original_price") or payload.get("listed_price")
                original_price = float(orig) if orig is not None else None
            except (TypeError, ValueError):
                original_price = None
            prod, _ = Product.objects.update_or_create(
                qdrant_id=qdrant_id,
                defaults={
                    "name": (payload.get("name") or payload.get("title") or f"Product {qdrant_id}")[:500],
                    "title": (payload.get("title") or payload.get("name") or "")[:500],
                    "description": (payload.get("description") or "")[:2000],
                    "price": Decimal(str(price)),
                    "original_price": Decimal(str(original_price)) if original_price is not None else None,
                    "currency": str(payload.get("currency", "USD"))[:10],
                    "image_url": (payload.get("image_url") or payload.get("image") or "")[:1000],
                    "category": str(payload.get("category", ""))[:100],
                    "rating": min(Decimal(str(payload.get("rating", 0))), Decimal("5.00")),
                    "availability": str(payload.get("availability", "In Stock"))[:100],
                    "url": (payload.get("url") or "")[:1000],
                    "discount_percentage": int(payload.get("discount_percentage") or 0),
                },
            )
            product_list.append(prod)
            if len(product_list) >= limit:
                break
        if next_offset is None:
            break
    logger.info("Synced %d products to SQLite (products table)", len(product_list))
    return product_list


def seed_interactions(users, products, interactions_per_user=25):
    """Create UserInteraction records in SQLite (user_interactions table)."""
    from rag_app.models import UserInteraction

    created = 0
    for user in users:
        chosen = random.sample(products, min(interactions_per_user, len(products)))
        for product in chosen:
            itype = _weighted_choice()
            UserInteraction.objects.create(
                user=user,
                product=product,
                interaction_type=itype,
                metadata={},
            )
            created += 1
    logger.info("Created %d UserInteraction rows in SQLite (user_interactions)", created)


def main():
    interactions_per_user = int(os.environ.get("SEED_INTERACTIONS_PER_USER", "25"))
    max_products = int(os.environ.get("SEED_MAX_PRODUCTS", "500"))

    logger.info("Setting up Django (rag_app.db)...")
    setup_django()

    logger.info("Ensuring synthetic users exist in auth_user...")
    users = ensure_users()
    if not users:
        logger.error("No users found. Run run_django_migrate.py first.")
        return

    logger.info("Fetching products from Qdrant and syncing to SQLite (products table)...")
    try:
        products = fetch_and_sync_products(limit=max_products)
    except Exception as e:
        logger.error("Failed to sync products (is Qdrant reachable?): %s", e)
        # Fallback: use existing Django products only
        from rag_app.models import Product
        products = list(Product.objects.all()[:max_products])
        if not products:
            logger.error("No products in SQLite. Populate Qdrant and run again, or add products manually.")
            return
        logger.info("Using %d existing products from SQLite", len(products))

    if not products:
        logger.error("No products available. Ensure Qdrant has products or run sync.")
        return

    logger.info("Seeding %d users with ~%d interactions each into user_interactions...", len(users), interactions_per_user)
    seed_interactions(users, products, interactions_per_user=interactions_per_user)

    logger.info("Done. All behaviour data is in SQLite: rag_app.db (auth_user, products, user_interactions).")


if __name__ == "__main__":
    main()
