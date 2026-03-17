// Cart update functionality with price recalculation
document.addEventListener('DOMContentLoaded', function() {
    // CSRF token helper
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
    const csrftoken = getCookie('csrftoken');
    
    // Update price breakdown in UI
    function updatePriceBreakdown(data) {
        // Update subtotal
        document.querySelectorAll('.cart-subtotal').forEach(el => {
            el.textContent = `₹${data.cart_total.toFixed(2)}`;
        });
        
        // Update tax
        if (data.tax !== undefined) {
            document.querySelectorAll('.cart-tax').forEach(el => {
                el.textContent = `₹${data.tax.toFixed(2)}`;
            });
        }
        
        // Update shipping
        if (data.shipping !== undefined) {
            document.querySelectorAll('.cart-shipping').forEach(el => {
                if (data.shipping > 0) {
                    el.innerHTML = `₹${data.shipping.toFixed(2)}`;
                } else {
                    el.innerHTML = '<span class="text-success fw-bold">FREE</span>';
                }
            });
        }
        
        // Update discount
        if (data.discount !== undefined && data.discount > 0) {
            document.querySelectorAll('.coupon-discount').forEach(el => {
                el.textContent = `-₹${data.discount.toFixed(2)}`;
            });
        }
        
        // Update final total
        if (data.final_total !== undefined) {
            document.querySelectorAll('.final-total').forEach(el => {
                el.textContent = `₹${data.final_total.toFixed(2)}`;
            });
        }
    }
    
    // Show toast notification
    function showToast(message, type = 'success') {
        const existingToast = document.querySelector('.cart-toast');
        if (existingToast) {
            existingToast.remove();
        }
        
        const toast = document.createElement('div');
        toast.className = 'cart-toast';
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
        }, 2000);
    }
    
    // Update cart item quantity
    function updateCartItem(itemId, quantity, button, originalQty) {
        button.disabled = true;

        fetch(`/cart/update/${itemId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin',
            body: JSON.stringify({ quantity: quantity })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `HTTP error! status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Update item subtotal
                const cartItem = document.querySelector(`.cart-item[data-item-id="${itemId}"]`);
                if (cartItem) {
                    cartItem.querySelector('.item-subtotal').textContent = `₹${data.item_subtotal.toFixed(2)}`;
                }
                
                // Update price breakdown
                updatePriceBreakdown(data);
                
                // Update cart count in header
                const cartBadge = document.querySelector('.navbar .badge');
                if (cartBadge && data.cart_count !== undefined) {
                    cartBadge.textContent = data.cart_count;
                }
                
                showToast('Cart updated successfully', 'success');
            } else {
                showToast(data.error || 'Failed to update cart', 'error');
                // Revert quantity to original
                const cartItem = document.querySelector(`.cart-item[data-item-id="${itemId}"]`);
                if (cartItem) {
                    cartItem.querySelector('.quantity-input').value = originalQty;
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast(error.message || 'An error occurred while updating the cart', 'error');
            // Revert quantity to original
            const cartItem = document.querySelector(`.cart-item[data-item-id="${itemId}"]`);
            if (cartItem) {
                cartItem.querySelector('.quantity-input').value = originalQty;
            }
        })
        .finally(() => {
            button.disabled = false;
        });
    }
    
    // Remove cart item
    function removeCartItem(itemId, button) {
        if (!confirm('Are you sure you want to remove this item?')) {
            return;
        }
        
        // Disable button during request
        button.disabled = true;
        
        fetch(`/cart/remove/${itemId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || `HTTP error! status: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Remove the cart item
                const cartItem = document.querySelector(`.cart-item[data-item-id="${itemId}"]`);
                if (cartItem) {
                    cartItem.style.animation = 'fadeOut 0.3s ease';
                    setTimeout(() => {
                        cartItem.remove();
                    }, 300);
                }
                
                // Update price breakdown
                updatePriceBreakdown(data);
                
                // Update cart count in header
                const cartBadge = document.querySelector('.navbar .badge');
                if (cartBadge) {
                    if (data.cart_count > 0) {
                        cartBadge.textContent = data.cart_count;
                    } else {
                        cartBadge.remove();
                    }
                }
                
                showToast('Item removed from cart', 'success');
                
                // If cart is empty, reload page to show empty message
                if (data.cart_count === 0) {
                    setTimeout(() => {
                        location.reload();
                    }, 1000);
                }
            } else {
                showToast(data.error || 'Failed to remove item', 'error');
                button.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast(error.message || 'An error occurred while removing the item', 'error');
            button.disabled = false;
        });
    }
    
    // Increase quantity buttons
    document.querySelectorAll('.increase-qty').forEach(button => {
        button.addEventListener('click', function() {
            const cartItem = this.closest('[data-item-id]');
            const itemId = cartItem.dataset.itemId;
            const input = cartItem.querySelector('.quantity-input');
            const currentQty = parseInt(input.value);
            const newQty = currentQty + 1;
            input.value = newQty;
            updateCartItem(itemId, newQty, this, currentQty);
        });
    });

    // Decrease quantity buttons
    document.querySelectorAll('.decrease-qty').forEach(button => {
        button.addEventListener('click', function() {
            const cartItem = this.closest('[data-item-id]');
            const itemId = cartItem.dataset.itemId;
            const input = cartItem.querySelector('.quantity-input');
            const currentQty = parseInt(input.value);
            if (currentQty > 1) {
                const newQty = currentQty - 1;
                input.value = newQty;
                updateCartItem(itemId, newQty, this, currentQty);
            } else {
                showToast('Minimum quantity is 1', 'error');
            }
        });
    });
    
    // Remove item buttons
    document.querySelectorAll('.remove-item').forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            removeCartItem(itemId, this);
        });
    });
});

// Add CSS animations
if (!document.getElementById('cart-animations')) {
    const style = document.createElement('style');
    style.id = 'cart-animations';
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
        
        @keyframes fadeOut {
            from {
                opacity: 1;
                transform: scale(1);
            }
            to {
                opacity: 0;
                transform: scale(0.9);
            }
        }
    `;
    document.head.appendChild(style);
}
