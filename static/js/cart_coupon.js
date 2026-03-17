// Coupon functionality for cart
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
    
    // Apply coupon
    const applyCouponBtn = document.getElementById('apply-coupon-btn');
    if (applyCouponBtn) {
        applyCouponBtn.addEventListener('click', function() {
            const couponCode = document.getElementById('coupon-code').value.trim();
            const errorDiv = document.getElementById('coupon-error');
            
            if (!couponCode) {
                errorDiv.textContent = 'Please enter a coupon code';
                errorDiv.style.display = 'block';
                return;
            }
            
            errorDiv.style.display = 'none';
            applyCouponBtn.disabled = true;
            applyCouponBtn.textContent = 'Applying...';
            
            fetch('/cart/apply-coupon/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({ code: couponCode })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Reload page to show applied coupon
                    location.reload();
                } else {
                    errorDiv.textContent = data.error || 'Failed to apply coupon';
                    errorDiv.style.display = 'block';
                    applyCouponBtn.disabled = false;
                    applyCouponBtn.textContent = 'Apply';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                errorDiv.textContent = 'An error occurred while applying the coupon';
                errorDiv.style.display = 'block';
                applyCouponBtn.disabled = false;
                applyCouponBtn.textContent = 'Apply';
            });
        });
        
        // Allow Enter key to apply coupon
        document.getElementById('coupon-code').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                applyCouponBtn.click();
            }
        });
    }
    
    // Remove coupon
    const removeCouponBtn = document.getElementById('remove-coupon-btn');
    if (removeCouponBtn) {
        removeCouponBtn.addEventListener('click', function() {
            if (!confirm('Are you sure you want to remove this coupon?')) {
                return;
            }
            
            fetch('/cart/remove-coupon/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Reload page to show removed coupon
                    location.reload();
                } else {
                    alert(data.error || 'Failed to remove coupon');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while removing the coupon');
            });
        });
    }
});
