"""
Cart and Favorites API Endpoints
Django-based local storage
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from rag_app.services.cart_service import cart_service
from rag_app.core.auth import get_current_user
from rag_app.models import Favorite

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cart", tags=["cart"])

class CartRequest(BaseModel):
    product_id: int
    quantity: int = 1

class CartResponse(BaseModel):
    success: bool
    message: str
    cart_total: Optional[int] = None
    cart_price: Optional[float] = None

class CartItemResponse(BaseModel):
    id: int
    name: str
    title: Optional[str]
    price: float
    original_price: float
    image: Optional[str]
    category: Optional[str]
    rating: float
    quantity: int
    subtotal: float
    discount: int
    added_at: str

class CartListResponse(BaseModel):
    success: bool
    items: List[CartItemResponse]
    summary: Dict[str, Any]

@router.post("/add")
async def add_to_cart(
    request: CartRequest, 
    current_user: dict = Depends(get_current_user)
) -> CartResponse:
    """Add product to cart"""
    try:
        # Convert email to Django User (you'll need to implement this mapping)
        from django.contrib.auth.models import User
        try:
            django_user = User.objects.get(email=current_user.get("email"))
        except User.DoesNotExist:
            # Create Django user if doesn't exist (auth is via token)
            django_user = User.objects.create_user(
                username=current_user.get("email"),
                email=current_user.get("email"),
                password="unused-token-auth",
            )
            django_user.set_unusable_password()
            django_user.save()
        
        result = cart_service.add_to_cart(
            user=django_user,
            product_id=request.product_id,
            quantity=request.quantity
        )
        
        return CartResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in add_to_cart API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/remove/{product_id}")
async def remove_from_cart(
    product_id: int,
    current_user: dict = Depends(get_current_user)
) -> CartResponse:
    """Remove product from cart"""
    try:
        from django.contrib.auth.models import User
        django_user = User.objects.get(email=current_user.get("email"))
        
        result = cart_service.remove_from_cart(
            user=django_user,
            product_id=product_id
        )
        
        return CartResponse(**result)
        
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error in remove_from_cart API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/update")
async def update_cart_quantity(
    request: CartRequest,
    current_user: dict = Depends(get_current_user)
) -> CartResponse:
    """Update cart item quantity"""
    try:
        from django.contrib.auth.models import User
        django_user = User.objects.get(email=current_user.get("email"))
        
        result = cart_service.update_cart_quantity(
            user=django_user,
            product_id=request.product_id,
            quantity=request.quantity
        )
        
        return CartResponse(**result)
        
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error in update_cart_quantity API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/items")
async def get_cart_items(
    current_user: dict = Depends(get_current_user)
) -> CartListResponse:
    """Get all cart items"""
    try:
        from django.contrib.auth.models import User
        django_user = User.objects.get(email=current_user.get("email"))
        
        items = cart_service.get_cart_items(user=django_user)
        summary = cart_service.get_cart_summary(user=django_user)
        
        return CartListResponse(
            success=True,
            items=[CartItemResponse(**item) for item in items],
            summary=summary
        )
        
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error in get_cart_items API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/clear")
async def clear_cart(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Clear all items from cart"""
    try:
        from django.contrib.auth.models import User
        django_user = User.objects.get(email=current_user.get("email"))
        
        result = cart_service.clear_cart(user=django_user)
        
        return result
        
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error in clear_cart API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/summary")
async def get_cart_summary(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get cart summary"""
    try:
        from django.contrib.auth.models import User
        django_user = User.objects.get(email=current_user.get("email"))
        
        summary = cart_service.get_cart_summary(user=django_user)
        
        return {
            "success": True,
            "summary": summary
        }
        
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error in get_cart_summary API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Favorites endpoints
@router.post("/favorites/add")
async def add_to_favorites(
    request: CartRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Add product to favorites"""
    try:
        from django.contrib.auth.models import User
        django_user = User.objects.get(email=current_user.get("email"))
        
        result = cart_service.add_to_favorites(
            user=django_user,
            product_id=request.product_id
        )
        
        return result
        
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error in add_to_favorites API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/favorites/remove/{product_id}")
async def remove_from_favorites(
    product_id: int,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Remove product from favorites"""
    try:
        from django.contrib.auth.models import User
        django_user = User.objects.get(email=current_user.get("email"))
        
        result = cart_service.remove_from_favorites(
            user=django_user,
            product_id=product_id
        )
        
        return result
        
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error in remove_from_favorites API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/favorites")
async def get_favorites(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all favorite products"""
    try:
        from django.contrib.auth.models import User
        django_user = User.objects.get(email=current_user.get("email"))
        
        favorites = cart_service.get_favorites(user=django_user)
        
        return {
            "success": True,
            "favorites": favorites
        }
        
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error in get_favorites API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/favorites/clear")
async def clear_favorites(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Clear all favorites"""
    try:
        from django.contrib.auth.models import User
        django_user = User.objects.get(email=current_user.get("email"))
        
        # Delete all favorites for this user
        Favorite.objects.filter(user=django_user).delete()
        
        return {
            "success": True,
            "message": "Favoris vidés avec succès"
        }
        
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error in clear_favorites API: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
