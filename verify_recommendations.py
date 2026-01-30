import asyncio
import httpx
import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000"
TEST_USER = "test_verify@example.com"

async def verify_recommendations():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Get some products to interact with
        logger.info("Fetching products for verification...")
        resp = await client.get(f"{API_BASE}/products?limit=10")
        data = resp.json()
        products = data.get("products", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        
        if not products:
            logger.error(f"No products found to interact with. Response: {data}")
            return

        target_product = products[0]
        # Qdrant IDs can be ints
        prod_id = target_product.get("id")
        prod_name = target_product.get("name") or target_product.get("title")
        logger.info(f"Targeting product: {prod_name} (ID: {prod_id})")

        # 2. Simulate interaction
        logger.info(f"Simulating 'view' interaction for {TEST_USER}...")
        resp = await client.post(f"{API_BASE}/api/interactions", json={
            "user_email": TEST_USER,
            "type": "view",
            "product_id": str(prod_id)
        })
        logger.info(f"Interaction result: {resp.json()}")

        # Wait for background task to finish (Qdrant update)
        logger.info("Waiting for profile update...")
        await asyncio.sleep(3)

        # 3. Fetch recommendations
        logger.info(f"Fetching recommendations for {TEST_USER}...")
        resp = await client.get(f"{API_BASE}/api/recommendations?user_email={TEST_USER}&limit=2")
        rec_data = resp.json()
        
        logger.info(f"Recommendations for {TEST_USER}:")
        if rec_data.get("success"):
            for i, p in enumerate(rec_data.get("products", [])):
                logger.info(f"  {i+1}. {p.get('name')} ({p.get('price')})")
        else:
            logger.error("Failed to fetch recommendations.")

        # 4. Simulate purchase to test budget convergence
        logger.info(f"Simulating 'purchase' interaction for {TEST_USER}...")
        resp = await client.post(f"{API_BASE}/api/interactions", json={
            "user_email": TEST_USER,
            "type": "purchase",
            "product_id": str(prod_id)
        })
        await asyncio.sleep(2)
        
        logger.info("Verification complete.")

if __name__ == "__main__":
    asyncio.run(verify_recommendations())
