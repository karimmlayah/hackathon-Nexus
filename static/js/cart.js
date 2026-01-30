/**
 * Cart and Favorites Management
 * Django-based local storage integration
 */

// Cart state
let cartState = {
    items: [],
    summary: {
        total_items: 0,
        total_price: 0.0,
        items_count: 0
    },
    favorites: []
};

/**
 * Initialize cart on page load
 */
async function initializeCart() {
    try {
        await loadCartItems();
        await loadFavorites();
        updateCartUI();
    } catch (error) {
        console.error('Error initializing cart:', error);
    }
}

/**
 * Load cart items from API
 */
async function loadCartItems() {
    const token = localStorage.getItem('finfit_token');
    if (!token) return;

    try {
        const response = await fetch('/api/cart/items', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            cartState.items = data.items || [];
            cartState.summary = data.summary || cartState.summary;
        }
    } catch (error) {
        console.error('Error loading cart items:', error);
    }
}

/**
 * Load favorites from API
 */
async function loadFavorites() {
    const token = localStorage.getItem('finfit_token');
    if (!token) return;

    try {
        const response = await fetch('/api/cart/favorites', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            cartState.favorites = data.favorites || [];
        }
    } catch (error) {
        console.error('Error loading favorites:', error);
    }
}

/**
 * Add product to cart
 */
async function addToCart(productId, quantity = 1) {
    const token = localStorage.getItem('finfit_token');
    if (!token) {
        showNotification('Veuillez vous connecter', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/cart/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                product_id: parseInt(productId),
                quantity: quantity
            })
        });

        const data = await response.json();
        
        if (data.success) {
            await loadCartItems();
            updateCartUI();
            showNotification(data.message, 'success');
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Error adding to cart:', error);
        showNotification('Erreur lors de l\'ajout au panier', 'error');
    }
}

/**
 * Remove product from cart
 */
async function removeFromCart(productId) {
    const token = localStorage.getItem('finfit_token');
    if (!token) return;

    try {
        const response = await fetch(`/api/cart/remove/${productId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();
        
        if (data.success) {
            await loadCartItems();
            updateCartUI();
            showNotification(data.message, 'success');
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Error removing from cart:', error);
        showNotification('Erreur lors du retrait', 'error');
    }
}

/**
 * Update cart item quantity
 */
async function updateCartQuantity(productId, quantity) {
    const token = localStorage.getItem('finfit_token');
    if (!token) return;

    try {
        const response = await fetch('/api/cart/update', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                product_id: parseInt(productId),
                quantity: parseInt(quantity)
            })
        });

        const data = await response.json();
        
        if (data.success) {
            await loadCartItems();
            updateCartUI();
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Error updating cart:', error);
        showNotification('Erreur lors de la mise à jour', 'error');
    }
}

/**
 * Add product to favorites
 */
async function addToFavorites(productId) {
    const token = localStorage.getItem('finfit_token');
    if (!token) {
        showNotification('Veuillez vous connecter', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/cart/favorites/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                product_id: parseInt(productId)
            })
        });

        const data = await response.json();
        
        if (data.success) {
            await loadFavorites();
            updateFavoriteButtons();
            showNotification(data.message, 'success');
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Error adding to favorites:', error);
        showNotification('Erreur lors de l\'ajout aux favoris', 'error');
    }
}

/**
 * Remove product from favorites
 */
async function removeFromFavorites(productId) {
    const token = localStorage.getItem('finfit_token');
    if (!token) return;

    try {
        const response = await fetch(`/api/cart/favorites/remove/${productId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();
        
        if (data.success) {
            await loadFavorites();
            updateFavoriteButtons();
            showNotification(data.message, 'success');
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Error removing from favorites:', error);
        showNotification('Erreur lors du retrait', 'error');
    }
}

/**
 * Toggle favorite status
 */
async function toggleFavorite(productId) {
    const isFavorite = cartState.favorites.some(item => item.id === parseInt(productId));
    
    if (isFavorite) {
        await removeFromFavorites(productId);
    } else {
        await addToFavorites(productId);
    }
}

/**
 * Update cart UI elements
 */
function updateCartUI() {
    // Update cart counter in header
    const cartCounter = document.getElementById('cartCounter');
    if (cartCounter) {
        cartCounter.textContent = cartState.summary.total_items || 0;
    }

    // Update cart total in header
    const cartTotal = document.getElementById('cartTotal');
    if (cartTotal) {
        cartTotal.textContent = `${cartState.summary.total_price.toFixed(2)} DT`;
    }

    // Update favorite buttons
    updateFavoriteButtons();
}

/**
 * Update favorite buttons state
 */
function updateFavoriteButtons() {
    const favoriteButtons = document.querySelectorAll('.favorite-btn');
    
    favoriteButtons.forEach(button => {
        const productId = button.getAttribute('data-product-id');
        const isFavorite = cartState.favorites.some(item => item.id === parseInt(productId));
        
        if (isFavorite) {
            button.classList.add('active');
            button.innerHTML = '<i class="fas fa-heart"></i>';
            button.setAttribute('title', 'Retirer des favoris');
        } else {
            button.classList.remove('active');
            button.innerHTML = '<i class="far fa-heart"></i>';
            button.setAttribute('title', 'Ajouter aux favoris');
        }
    });
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.cart-notification');
    existingNotifications.forEach(n => n.remove());

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `cart-notification alert alert-${type} position-fixed top-0 start-50 translate-middle-x mt-3`;
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    notification.innerHTML = `
        <div class="d-flex align-items-center justify-content-between">
            <div class="d-flex align-items-center">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close ms-2" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 3000);
}

/**
 * Format price
 */
function formatPrice(price) {
    return `${parseFloat(price).toFixed(2)} DT`;
}

/**
 * Get cart summary
 */
function getCartSummary() {
    return cartState.summary;
}

/**
 * Get cart items
 */
function getCartItems() {
    return cartState.items;
}

/**
 * Check if product is in favorites
 */
function isFavorite(productId) {
    return cartState.favorites.some(item => item.id === parseInt(productId));
}

// Initialize cart when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeCart);

// Export functions for global use
window.addToCart = addToCart;
window.removeFromCart = removeFromCart;
window.updateCartQuantity = updateCartQuantity;
window.addToFavorites = addToFavorites;
window.removeFromFavorites = removeFromFavorites;
window.toggleFavorite = toggleFavorite;
window.isFavorite = isFavorite;
window.getCartSummary = getCartSummary;
window.getCartItems = getCartItems;
