"""
Django management command to sync products from Qdrant to local database
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from qdrant_client import QdrantClient
from qdrant_client.http import models
import logging

from rag_app.core.database import get_qdrant_client
from rag_app.core.config import settings
from rag_app.models import Product

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync products from Qdrant to local Django database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='Number of products to sync (default: 1000)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync all products (delete existing)'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        force = options['force']
        
        self.stdout.write('🔄 Starting product sync from Qdrant...')
        
        try:
            # Get Qdrant client
            client = get_qdrant_client()
            
            # Clear existing products if force
            if force:
                self.stdout.write('🗑️  Clearing existing products...')
                Product.objects.all().delete()
            
            # Fetch products from Qdrant
            self.stdout.write(f'📦 Fetching {limit} products from Qdrant...')
            
            points, _ = client.scroll(
                collection_name=settings.COLLECTION_NAME,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            self.stdout.write(f'✅ Found {len(points)} products in Qdrant')
            
            # Sync to Django
            synced_count = 0
            updated_count = 0
            
            with transaction.atomic():
                for point in points:
                    payload = point.payload
                    
                    # Extract product data
                    product_data = self.extract_product_data(payload, point.id)
                    
                    if not product_data:
                        continue
                    
                    # Create or update product
                    product, created = Product.objects.update_or_create(
                        qdrant_id=product_data['qdrant_id'],
                        defaults=product_data
                    )
                    
                    if created:
                        synced_count += 1
                    else:
                        updated_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Sync completed!\n'
                    f'   New products: {synced_count}\n'
                    f'   Updated products: {updated_count}\n'
                    f'   Total in database: {Product.objects.count()}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Sync failed: {str(e)}')
            )
            logger.error(f'Product sync error: {e}', exc_info=True)

    def extract_product_data(self, payload: dict, qdrant_id: int) -> dict:
        """Extract product data from Qdrant payload"""
        try:
            # Extract and clean price
            raw_price = payload.get("price") or payload.get("final_price") or 0
            try:
                price = float(str(raw_price).replace(",", "").replace("DT", "").strip())
            except (ValueError, TypeError):
                price = 0.0
            
            # Extract discount
            discount = 0
            discount_raw = payload.get("discount") or payload.get("discount_percentage")
            if discount_raw:
                try:
                    # Handle various discount formats
                    discount_str = str(discount_raw).replace('%', '').replace('-', '').replace('$', '').strip()
                    discount = int(discount_str) if discount_str else 0
                except (ValueError, TypeError):
                    discount = 0
            
            return {
                'qdrant_id': int(qdrant_id),
                'name': payload.get("name") or payload.get("title") or "Unknown Product",
                'title': payload.get("title") or "",
                'description': payload.get("description", "")[:1000],
                'price': price,
                'original_price': price,  # Will be updated if discount applied
                'currency': payload.get("currency", "USD"),
                'image_url': payload.get("image_url") or payload.get("image") or "",
                'category': payload.get("category", "General"),
                'rating': float(payload.get("rating", 4.5)),
                'availability': payload.get("availability", "In Stock"),
                'url': payload.get("url") or payload.get("product_url") or "",
                'discount_percentage': discount
            }
            
        except Exception as e:
            logger.error(f'Error extracting product data: {e}')
            return None
