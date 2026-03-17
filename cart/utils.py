"""Cart utility functions"""
from django.db import transaction
from .models import Cart, CartItem


def migrate_session_cart_to_user(request, user):
    """
    Migrate session cart to user's database cart after login.
    
    This function:
    1. Retrieves the session cart (if exists)
    2. Retrieves or creates the user's database cart
    3. Merges session cart items into database cart
    4. Handles duplicate products by combining quantities
    5. Clears the session cart after successful merge
    
    Args:
        request: Django request object with session
        user: Authenticated user object
    
    Returns:
        tuple: (merged_count, total_items) - number of items merged and total items in cart
    """
    # Get session key before it might be cycled
    session_key = request.session.session_key
    
    if not session_key:
        # No session cart exists
        return 0, 0
    
    try:
        # Get session cart
        session_cart = Cart.objects.filter(session_key=session_key).first()
        
        if not session_cart or not session_cart.items.exists():
            # No session cart or empty cart
            return 0, 0
        
        # Get or create user's database cart
        user_cart, created = Cart.objects.get_or_create(user=user)
        
        merged_count = 0
        
        with transaction.atomic():
            # Iterate through session cart items
            for session_item in session_cart.items.all():
                # Check if user cart already has this product+size combination
                existing_item = CartItem.objects.filter(
                    cart=user_cart,
                    product=session_item.product,
                    size=session_item.size
                ).first()
                
                if existing_item:
                    # Merge quantities for duplicate products
                    existing_item.quantity += session_item.quantity
                    existing_item.save()
                else:
                    # Create new item in user cart
                    CartItem.objects.create(
                        cart=user_cart,
                        product=session_item.product,
                        size=session_item.size,
                        quantity=session_item.quantity
                    )
                
                merged_count += 1
            
            # Clear session cart after successful merge
            session_cart.items.all().delete()
            session_cart.delete()
        
        # Return merge statistics
        total_items = user_cart.items.count()
        return merged_count, total_items
        
    except Exception as e:
        # Log error but don't fail login process
        print(f"Error migrating cart: {str(e)}")
        return 0, 0


def get_coupon_info(request):
    """
    Get coupon information from session.
    
    Args:
        request: Django request object with session
    
    Returns:
        dict: Dictionary containing coupon_code, coupon_discount (as Decimal)
    """
    from decimal import Decimal
    
    coupon_code = request.session.get('coupon_code')
    coupon_discount = Decimal(str(request.session.get('coupon_discount', 0)))
    
    return {
        'coupon_code': coupon_code,
        'coupon_discount': coupon_discount
    }
