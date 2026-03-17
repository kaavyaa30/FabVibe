def cart_count(request):
    """
    Context processor to add cart item count and wishlist count to all templates
    """
    cart_count = 0
    wishlist_count = 0
    
    if request.user.is_authenticated:
        # For authenticated users, count from database
        from .models import Cart
        try:
            cart = Cart.objects.get(user=request.user)
            cart_count = cart.items.count()
        except Cart.DoesNotExist:
            cart_count = 0
        
        # Get wishlist count
        from products.models import Wishlist
        try:
            wishlist_count = Wishlist.objects.filter(user=request.user).count()
        except:
            wishlist_count = 0
    else:
        # For guest users, count from session cart
        if request.session.session_key:
            from .models import Cart
            try:
                cart = Cart.objects.get(session_key=request.session.session_key)
                cart_count = cart.items.count()
            except Cart.DoesNotExist:
                cart_count = 0
    
    return {
        'cart_count': cart_count,
        'wishlist_count': wishlist_count
    }

