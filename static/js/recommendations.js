/**
 * Recommendations Module
 * Handles loading and displaying personalized product recommendations
 * Uses collaborative filtering based on similar users
 */

/**
 * Load personalized recommendations for the logged-in user
 */
async function loadRecommendations() {
    console.log('📊 Loading personalized recommendations...');

    // Check if user is logged in
    const token = localStorage.getItem('finfit_token');
    const storedUser = localStorage.getItem('finfit_user');

    if (!token || !storedUser) {
        console.log('⚠️ User not logged in, showing message');
        showRecommendationsMessage('Veuillez vous connecter pour voir les recommandations personnalisées');
        return;
    }

    try {
        const userData = JSON.parse(storedUser);
        const userEmail = userData.email;

        if (!userEmail) {
            console.warn('No user email found');
            showRecommendationsMessage('Erreur: email utilisateur non trouvé');
            return;
        }

        // Show loading state
        showRecommendationsLoading();

        // Fetch recommendations from API
        const response = await fetch(`/api/recommendations/${encodeURIComponent(userEmail)}?limit=8&include_explanation=true`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        console.log('✅ Recommendations loaded:', data);

        if (data.success && data.recommendations && data.recommendations.length > 0) {
            // Display recommendations
            displayRecommendations(data.recommendations);
            
            // Show AI explanation
            showAIExplanation(data.strategy, data.recommendations.length);
        } else {
            // No recommendations available
            showRecommendationsMessage('Explorez plus de produits pour recevoir des recommandations personnalisées!');
        }

    } catch (error) {
        console.error('❌ Error loading recommendations:', error);
        showRecommendationsMessage('Impossible de charger les recommandations pour le moment.');
    }
}

function showRecommendationsLoading() {
    const loading = document.getElementById('recommendationsLoading');
    const grid = document.getElementById('recommendationsGrid');
    const noRecs = document.getElementById('noRecommendations');
    const aiContainer = document.getElementById('aiAnswerContainer-recommendations');
    
    if (loading) loading.style.display = 'block';
    if (grid) grid.style.display = 'none';
    if (noRecs) noRecs.style.display = 'none';
    if (aiContainer) aiContainer.classList.add('d-none');
}

function showRecommendationsMessage(message) {
    const loading = document.getElementById('recommendationsLoading');
    const grid = document.getElementById('recommendationsGrid');
    const noRecs = document.getElementById('noRecommendations');
    const aiContainer = document.getElementById('aiAnswerContainer-recommendations');
    
    if (loading) loading.style.display = 'none';
    if (grid) grid.style.display = 'none';
    if (noRecs) {
        noRecs.style.display = 'block';
        noRecs.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-info-circle fa-3x text-muted mb-3"></i>
                <p class="text-muted">${message}</p>
                <button class="btn btn-primary mt-2" onclick="loadTab('tab-all', null)">
                    <i class="fas fa-shopping-bag me-2"></i>Découvrir tous les produits
                </button>
            </div>
        `;
    }
    if (aiContainer) aiContainer.classList.add('d-none');
}

function showAIExplanation(strategy, count) {
    const aiContainer = document.getElementById('aiAnswerContainer-recommendations');
    const aiText = document.getElementById('aiAnswerText-recommendations');
    
    if (!aiContainer || !aiText) return;
    
    const strategyMessages = {
        'hybrid (personal + collaborative)': `J'ai analysé vos préférences et trouvé ${count} produits qui correspondent à vos goûts et à ceux d'utilisateurs similaires.`,
        'personal (cold start)': `Basé sur vos premières interactions, je vous recommande ces ${count} produits pour commencer.`,
        'trending (fallback)': `Je vous présente ${count} produits populaires qui pourraient vous intéresser.`
    };
    
    const message = strategyMessages[strategy] || `Voici ${count} produits recommandés pour vous.`;
    
    aiText.innerHTML = message;
    aiContainer.classList.remove('d-none');
}

/**
 * Display recommendations in the grid
 */
function displayRecommendations(recommendations) {
    const recommendationsGrid = document.getElementById('recommendationsGrid');
    const loading = document.getElementById('recommendationsLoading');
    const noRecs = document.getElementById('noRecommendations');

    if (!recommendationsGrid) {
        console.error('Recommendations grid element not found');
        return;
    }

    // Hide loading and no recommendations, show grid
    if (loading) loading.style.display = 'none';
    if (noRecs) noRecs.style.display = 'none';
    recommendationsGrid.style.display = 'flex';
    recommendationsGrid.innerHTML = '';

    recommendations.forEach((product, index) => {
        const productCard = createRecommendationCard(product, index);
        recommendationsGrid.appendChild(productCard);
    });
}

/**
 * Create a product card for recommendations
 */
function createRecommendationCard(product, index) {
    const col = document.createElement('div');
    col.className = 'col-md-6 col-lg-4 col-xl-3 wow fadeInUp';
    col.setAttribute('data-wow-delay', `${0.1 + (index * 0.1)}s`);

    // Extract product details with better image handling
    const productId = product.id || product.product_id || '';
    const productName = product.name || product.title || 'Unknown Product';
    const productPrice = product.price || 'N/A';
    
    // Better image handling - try multiple sources (image_url, image, image_urls[0])
    let productImage = '/static/img/placeholder.png';
    const rawUrl = (product.image_url && product.image_url.trim()) || (product.image && product.image.trim()) || (product.image_urls && product.image_urls[0]);
    if (rawUrl && String(rawUrl).trim() && String(rawUrl) !== '/static/img/placeholder.png') {
        productImage = typeof rawUrl === 'string' ? rawUrl.trim() : String(rawUrl);
    }
    
    const productCategory = product.category || 'General';
    const productRating = product.rating || 4.5;
    const productUrl = product.url || product.product_url || `single.html?id=${productId}`;
    
    // Better explanation handling
    let explanation = 'Recommandé pour vous';
    if (product.explanation && product.explanation !== 'Recommandé pour vous') {
        explanation = product.explanation;
    } else if (product.sources && product.sources.includes('collaborative')) {
        explanation = 'Les utilisateurs similaires ont aimé ce produit';
    } else if (product.sources && product.sources.includes('personal')) {
        explanation = 'Basé sur vos préférences personnelles';
    } else if (product.sources && product.sources.includes('trending')) {
        explanation = 'Produit populaire tendance';
    }

    // Calculate discount percentage if available
    let discountBadge = '';
    if (product.discount || product.discount_percentage) {
        const discount = product.discount || product.discount_percentage;
        discountBadge = `
            <div class="product-item-offer bg-danger rounded text-white position-absolute" 
                 style="top: 10px; right: 10px; padding: 5px 10px; font-size: 0.85rem; font-weight: bold;">
                ${discount}% OFF
            </div>
        `;
    }

    // Recommendation badge
    const sources = product.sources || [];
    let badgeIcon = 'fa-star';
    let badgeColor = 'bg-primary';
    let badgeText = 'Recommandé';

    if (sources.includes('collaborative')) {
        badgeIcon = 'fa-users';
        badgeColor = 'bg-success';
        badgeText = 'Aimé par d\'autres';
    } else if (sources.includes('personal')) {
        badgeIcon = 'fa-heart';
        badgeColor = 'bg-info';
        badgeText = 'Pour vous';
    }

    col.innerHTML = `
        <div class="product-item-inner-item border h-100 rounded position-relative">
            ${discountBadge}
            <div class="product-item-inner-item-img position-relative" style="height: 200px; overflow: hidden;">
                <img src="${productImage}" 
                     class="img-fluid w-100 h-100" 
                     alt="${productName}"
                     style="object-fit: contain; padding: 10px;"
                     onerror="this.src='/static/img/placeholder.png'; console.log('Image failed:', '${productImage}');">
                <div class="product-item-inner-item-icon">
                    <a href="#" onclick="trackProductViewAndClick('${productId}', '${productName.replace(/'/g, "\\'")}'); return false;" class="btn btn-sm btn-primary rounded-circle">
                        <i class="fa fa-eye"></i>
                    </a>
                </div>
            </div>
            <div class="product-item-inner-item-content text-center p-4">
                <span class="badge ${badgeColor} mb-2">
                    <i class="fas ${badgeIcon} me-1"></i>${badgeText}
                </span>
                <p class="fs-6 text-muted mb-1">${productCategory}</p>
                <a href="#" onclick="trackProductViewAndClick('${productId}', '${productName.replace(/'/g, "\\'")}'); return false;" class="d-block h5 mb-3 text-dark text-decoration-none" 
                   style="min-height: 48px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                    ${productName}
                </a>
                <div class="d-flex justify-content-center mb-2">
                    ${generateStarRating(productRating)}
                    <span class="text-muted ms-2">(${productRating})</span>
                </div>
                <p class="fs-5 fw-bold text-primary mb-2">${productPrice}</p>
                <div class="bg-light rounded p-2 mb-3" style="min-height: 50px;">
                    <p class="text-muted small mb-0">
                        <i class="fas fa-info-circle me-1 text-primary"></i>
                        <strong>Pourquoi ce produit ?</strong><br>
                        ${explanation}
                    </p>
                </div>
                <div class="d-flex justify-content-center gap-2">
                    <button class="btn btn-primary rounded-pill px-3" onclick="addToCartAndTrack('${productId}', '${productName}')">
                        <i class="fas fa-shopping-cart me-1"></i> Ajouter
                    </button>
                    <button class="btn btn-outline-danger rounded-pill px-3" onclick="addToWishlistAndTrack('${productId}', '${productName}')">
                        <i class="fas fa-heart"></i>
                    </button>
                </div>
            </div>
        </div>
    `;

    return col;
}

/**
 * Generate star rating HTML
 */
function generateStarRating(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

    let starsHTML = '';

    // Full stars
    for (let i = 0; i < fullStars; i++) {
        starsHTML += '<i class="fas fa-star text-warning"></i>';
    }

    // Half star
    if (hasHalfStar) {
        starsHTML += '<i class="fas fa-star-half-alt text-warning"></i>';
    }

    // Empty stars
    for (let i = 0; i < emptyStars; i++) {
        starsHTML += '<i class="far fa-star text-warning"></i>';
    }

    return starsHTML;
}

/**
 * Track product interaction
 */
async function trackInteraction(productId, interactionType, productName = '') {
    const token = localStorage.getItem('finfit_token');
    const storedUser = localStorage.getItem('finfit_user');

    if (!token || !storedUser) {
        return; // User not logged in
    }

    try {
        const userData = JSON.parse(storedUser);
        const userEmail = userData.email;

        await fetch('/api/track/' + interactionType, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                product_id: productId,
                metadata: { product_name: productName }
            })
        });

        console.log(`✅ Tracked ${interactionType} for product ${productId}`);
    } catch (error) {
        console.error(`Error tracking ${interactionType}:`, error);
    }
}

/**
 * Track product view and navigate
 */
async function trackProductViewAndClick(productId, productName) {
    await trackInteraction(productId, 'view', productName);
    await trackInteraction(productId, 'click', productName);
    window.location.href = `single.html?id=${productId}`;
}

/**
 * Add to cart with tracking
 */
async function addToCartAndTrack(productId, productName) {
    await trackInteraction(productId, 'add-to-cart', productName);
    
    // Use the cart service
    await addToCart(productId);
}

/**
 * Add to wishlist with tracking
 */
async function addToWishlistAndTrack(productId, productName) {
    await trackInteraction(productId, 'wishlist', productName);
    
    // Use the cart service
    await addToFavorites(productId);
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} position-fixed top-0 start-50 translate-middle-x mt-3`;
    notification.style.zIndex = '9999';
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-check-circle me-2"></i>
            ${message}
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

/**
 * Track product view for recommendations
 */
async function trackProductView(productId) {
    await trackInteraction(productId, 'view');
}

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        loadRecommendations,
        trackProductView
    };
}
