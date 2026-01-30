"""
Cart Service for Django-based cart management
Local database storage instead of cloud-only. Cart and favorites are linked to the connected user.
"""
from typing import List, Dict, Any, Optional
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
import logging

from rag_app.models import Cart, CartItem, Product, Favorite, UserInteraction

logger = logging.getLogger(__name__)


def _get_or_create_product_from_qdrant(qdrant_id: int) -> Optional[Product]:
    """
    Fetch product from Qdrant by point id and create/update Django Product.
    So cart and favorites can add items even if Product is not yet in Django.
    """
    try:
        from rag_app.core.database import get_qdrant_client
        from rag_app.core.config import settings
        client = get_qdrant_client()
        collection_name = settings.COLLECTION_NAME
        points = client.retrieve(
            collection_name=collection_name,
            ids=[qdrant_id],
            with_payload=True,
            with_vectors=False,
        )
        if not points or not points[0].payload:
            return None
        payload = points[0].payload
        raw_price = payload.get("price") or payload.get("final_price") or 0
        try:
            price = Decimal(str(raw_price).replace(",", "")) if raw_price else Decimal("0")
        except Exception:
            price = Decimal("0")
        try:
            raw_orig = payload.get("initial_price")
            original_price = Decimal(str(raw_orig).replace(",", "")) if raw_orig is not None else price
        except Exception:
            original_price = price
        product, created = Product.objects.update_or_create(
            qdrant_id=qdrant_id,
            defaults={
                "name": payload.get("name") or payload.get("title") or "Product",
                "title": payload.get("title") or payload.get("name") or "",
                "description": (payload.get("description") or "")[:2000],
                "price": price,
                "original_price": original_price,
                "currency": str(payload.get("currency", "USD"))[:10],
                "image_url": (payload.get("image_url") or payload.get("image") or "")[:1000],
                "category": str(payload.get("category", ""))[:100],
                "rating": min(Decimal(str(payload.get("rating", 0))), Decimal("5.00")),
                "availability": str(payload.get("availability", "In Stock"))[:100],
                "url": (payload.get("url") or payload.get("product_url") or "")[:1000],
                "discount_percentage": int(payload.get("discount_percentage") or 0),
            },
        )
        return product
    except Exception as e:
        logger.warning("Could not sync product %s from Qdrant: %s", qdrant_id, e)
        return None


class CartService:
    """Service for managing user carts and favorites (linked to connected user)"""
    
    def __init__(self):
        pass
    
    def get_or_create_cart(self, user: User) -> Cart:
        """Get or create user's cart"""
        cart, created = Cart.objects.get_or_create(user=user)
        return cart
    
    def add_to_cart(self, user: User, product_id: int, quantity: int = 1) -> Dict[str, Any]:
        """Add product to user's cart (product synced from Qdrant if needed)"""
        try:
            with transaction.atomic():
                # Get or create cart
                cart = self.get_or_create_cart(user)
                
                # Get or create product (sync from Qdrant if not in Django)
                try:
                    product = Product.objects.get(qdrant_id=product_id)
                except Product.DoesNotExist:
                    product = _get_or_create_product_from_qdrant(product_id)
                    if not product:
                        return {"success": False, "message": "Produit non trouvé"}
                
                # Add or update cart item
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    defaults={'quantity': quantity}
                )
                
                if not created:
                    cart_item.quantity += quantity
                    cart_item.save()
                
                # Track interaction
                UserInteraction.objects.create(
                    user=user,
                    product=product,
                    interaction_type='add_to_cart',
                    metadata={'quantity': quantity}
                )
                
                logger.info(f"Added {product.name} to cart for {user.email}")
                
                return {
                    'success': True,
                    'message': f'{product.name} ajouté au panier',
                    'cart_total': cart.total_items,
                    'cart_price': float(cart.total_price)
                }
                
        except Product.DoesNotExist:
            return {
                'success': False,
                'message': 'Produit non trouvé'
            }
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            return {
                'success': False,
                'message': 'Erreur lors de l\'ajout au panier'
            }
    
    def remove_from_cart(self, user: User, product_id: int) -> Dict[str, Any]:
        """Remove product from user's cart"""
        try:
            with transaction.atomic():
                cart = self.get_or_create_cart(user)
                product = Product.objects.get(qdrant_id=product_id)
                
                try:
                    cart_item = CartItem.objects.get(cart=cart, product=product)
                    cart_item.delete()
                    
                    return {
                        'success': True,
                        'message': f'{product.name} retiré du panier',
                        'cart_total': cart.total_items,
                        'cart_price': float(cart.total_price)
                    }
                except CartItem.DoesNotExist:
                    return {
                        'success': False,
                        'message': 'Produit non trouvé dans le panier'
                    }
                    
        except Product.DoesNotExist:
            return {
                'success': False,
                'message': 'Produit non trouvé'
            }
        except Exception as e:
            logger.error(f"Error removing from cart: {e}")
            return {
                'success': False,
                'message': 'Erreur lors du retrait du panier'
            }
    
    def update_cart_quantity(self, user: User, product_id: int, quantity: int) -> Dict[str, Any]:
        """Update quantity of item in cart"""
        try:
            with transaction.atomic():
                cart = self.get_or_create_cart(user)
                product = Product.objects.get(qdrant_id=product_id)
                
                if quantity <= 0:
                    return self.remove_from_cart(user, product_id)
                
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    defaults={'quantity': quantity}
                )
                
                if not created:
                    cart_item.quantity = quantity
                    cart_item.save()
                
                return {
                    'success': True,
                    'message': 'Quantité mise à jour',
                    'cart_total': cart.total_items,
                    'cart_price': float(cart.total_price)
                }
                
        except Product.DoesNotExist:
            return {
                'success': False,
                'message': 'Produit non trouvé'
            }
        except Exception as e:
            logger.error(f"Error updating cart quantity: {e}")
            return {
                'success': False,
                'message': 'Erreur lors de la mise à jour'
            }
    
    def get_cart_items(self, user: User) -> List[Dict[str, Any]]:
        """Get all items in user's cart"""
        try:
            cart = self.get_or_create_cart(user)
            items = []
            
            for cart_item in cart.items.select_related('product').all():
                items.append({
                    'id': cart_item.product.qdrant_id,
                    'name': cart_item.product.name,
                    'title': cart_item.product.title,
                    'price': float(cart_item.product.current_price),
                    'original_price': float(cart_item.product.price),
                    'image': cart_item.product.image_url,
                    'category': cart_item.product.category,
                    'rating': float(cart_item.product.rating),
                    'quantity': cart_item.quantity,
                    'subtotal': float(cart_item.subtotal),
                    'discount': cart_item.product.discount_percentage,
                    'added_at': cart_item.added_at.isoformat()
                })
            
            return items
            
        except Exception as e:
            logger.error(f"Error getting cart items: {e}")
            return []
    
    def clear_cart(self, user: User) -> Dict[str, Any]:
        """Clear all items from user's cart"""
        try:
            with transaction.atomic():
                cart = self.get_or_create_cart(user)
                cart.items.all().delete()
                
                return {
                    'success': True,
                    'message': 'Panier vidé'
                }
                
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            return {
                'success': False,
                'message': 'Erreur lors du vidage du panier'
            }
    
    def add_to_favorites(self, user: User, product_id: int) -> Dict[str, Any]:
        """Add product to user's favorites (product synced from Qdrant if needed)"""
        try:
            try:
                product = Product.objects.get(qdrant_id=product_id)
            except Product.DoesNotExist:
                product = _get_or_create_product_from_qdrant(product_id)
                if not product:
                    return {"success": False, "message": "Produit non trouvé"}
            
            favorite, created = Favorite.objects.get_or_create(
                user=user,
                product=product
            )
            
            if created:
                # Track interaction
                UserInteraction.objects.create(
                    user=user,
                    product=product,
                    interaction_type='wishlist'
                )
                
                return {
                    'success': True,
                    'message': f'{product.name} ajouté aux favoris'
                }
            else:
                return {
                    'success': False,
                    'message': 'Produit déjà dans les favoris'
                }
                
        except Product.DoesNotExist:
            return {
                'success': False,
                'message': 'Produit non trouvé'
            }
        except Exception as e:
            logger.error(f"Error adding to favorites: {e}")
            return {
                'success': False,
                'message': 'Erreur lors de l\'ajout aux favoris'
            }
    
    def remove_from_favorites(self, user: User, product_id: int) -> Dict[str, Any]:
        """Remove product from user's favorites"""
        try:
            product = Product.objects.get(qdrant_id=product_id)
            
            try:
                favorite = Favorite.objects.get(user=user, product=product)
                favorite.delete()
                
                return {
                    'success': True,
                    'message': f'{product.name} retiré des favoris'
                }
            except Favorite.DoesNotExist:
                return {
                    'success': False,
                    'message': 'Produit non trouvé dans les favoris'
                }
                
        except Product.DoesNotExist:
            return {
                'success': False,
                'message': 'Produit non trouvé'
            }
        except Exception as e:
            logger.error(f"Error removing from favorites: {e}")
            return {
                'success': False,
                'message': 'Erreur lors du retrait des favoris'
            }
    
    def get_favorites(self, user: User) -> List[Dict[str, Any]]:
        """Get all user's favorite products"""
        try:
            favorites = []
            
            for favorite in user.favorites.select_related('product').all():
                product = favorite.product
                favorites.append({
                    'id': product.qdrant_id,
                    'name': product.name,
                    'title': product.title,
                    'price': float(product.current_price),
                    'original_price': float(product.price),
                    'image': product.image_url,
                    'category': product.category,
                    'rating': float(product.rating),
                    'discount': product.discount_percentage,
                    'added_at': favorite.added_at.isoformat()
                })
            
            return favorites
            
        except Exception as e:
            logger.error(f"Error getting favorites: {e}")
            return []
    
    def is_favorite(self, user: User, product_id: int) -> bool:
        """Check if product is in user's favorites"""
        try:
            product = Product.objects.get(qdrant_id=product_id)
            return Favorite.objects.filter(user=user, product=product).exists()
        except Product.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error checking favorite: {e}")
            return False
    
    def get_cart_summary(self, user: User) -> Dict[str, Any]:
        """Get cart summary information"""
        try:
            cart = self.get_or_create_cart(user)
            
            return {
                'total_items': cart.total_items,
                'total_price': float(cart.total_price),
                'items_count': cart.items.count()
            }
            
        except Exception as e:
            logger.error(f"Error getting cart summary: {e}")
            return {
                'total_items': 0,
                'total_price': 0.0,
                'items_count': 0
            }


# Singleton instance
cart_service = CartService()
