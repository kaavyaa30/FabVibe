/**
 * Wishlist functionality for FabVibe
 * Handles adding/removing products from wishlist with AJAX
 */

function toggleWishlist(productId, buttonElement) {
    // Check if user is authenticated
    const isAuthenticated = document.body.dataset.userAuthenticated === 'true';
    
    if (!isAuthenticated) {
        // Redirect to login page with next parameter
        const currentUrl = window.location.pathname;
        window.location.href = `/users/login/?next=${encodeURIComponent(currentUrl)}`;
        return;
    }
    
    const icon = buttonElement.querySelector('i');
    const isInWishlist = icon.classList.contains('fas');
    
    // Disable button during request
    buttonElement.disabled = true;
    
    // Get CSRF token
    const csrfToken = getCookie('csrftoken');
    
    if (!csrfToken) {
        console.error('CSRF token not found');
        showToast('Security token missing. Please refresh the page and try again.', 'error');
        buttonElement.disabled = false;
        return;
    }
    
    fetch(`/products/wishlist/add/${productId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        // Handle 401 Unauthorized (not logged in)
        if (response.status === 401) {
            return response.json().then(data => {
                if (data.redirect) {
                    window.location.href = data.redirect;
                } else {
                    throw new Error('Please login to add items to wishlist');
                }
            });
        }
        
        // Check if response is ok
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.message || `HTTP error! status: ${response.status}`);
            }).catch(err => {
                // If JSON parsing fails, throw generic error
                throw new Error(`Server error: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data && data.success) {
            // Toggle icon based on response
            if (data.in_wishlist) {
                icon.classList.remove('far');
                icon.classList.add('fas');
                buttonElement.classList.add('active');
            } else {
                icon.classList.remove('fas');
                icon.classList.add('far');
                buttonElement.classList.remove('active');
            }
            
            // Show brief success message
            showToast(data.message, 'success');
        } else if (data && !data.success) {
            showToast(data.message || 'Failed to update wishlist', 'error');
        }
    })
    .catch(error => {
        console.error('Wishlist error:', error);
        showToast(error.message || 'An error occurred. Please try again.', 'error');
    })
    .finally(() => {
        buttonElement.disabled = false;
    });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showToast(message, type = 'success') {
    // Remove any existing toasts
    const existingToast = document.querySelector('.wishlist-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Create a simple toast notification
    const toast = document.createElement('div');
    toast.className = 'wishlist-toast';
    toast.textContent = message;
    
    const backgroundColor = type === 'success' ? '#27ae60' : '#e74c3c';
    
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: ${backgroundColor};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 9999;
        animation: slideIn 0.3s ease;
        max-width: 300px;
        font-weight: 500;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// Add CSS animations
if (!document.getElementById('wishlist-animations')) {
    const style = document.createElement('style');
    style.id = 'wishlist-animations';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        .wishlist-btn {
            position: relative;
            transition: all 0.3s ease;
        }
        
        .wishlist-btn:hover {
            transform: scale(1.1);
        }
        
        .wishlist-btn.active i {
            color: #dc3545;
        }
    `;
    document.head.appendChild(style);
}
