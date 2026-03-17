from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from decimal import Decimal
from .models import Cart, CartItem
from .services import PriceCalculator
from products.models import Product, Inventory
import json

def get_or_create_cart(request):
    """Get or create cart for authenticated or guest user"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # For guest users, use session
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart

def cart_detail(request):
    """Shopping cart detail view"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product').all()
    
    # Get coupon info from session
    coupon_code = request.session.get('coupon_code')
    coupon_discount = Decimal(str(request.session.get('coupon_discount', 0)))
    
    # Use PriceCalculator for price breakdown
    calculator = PriceCalculator(cart, coupon_discount=coupon_discount)
    price_breakdown = calculator.get_price_breakdown()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'cart_total': price_breakdown['subtotal'],
        'tax': price_breakdown['tax'],
        'shipping': price_breakdown['shipping'],
        'coupon_code': coupon_code,
        'coupon_discount': price_breakdown['discount'],
        'final_total': price_breakdown['total'],
    }
    return render(request, 'cart/cart_detail.html', context)

@require_POST
def add_to_cart(request, product_id):
    """Add product to cart with size and quantity"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Add to cart request for product {product_id} from user {request.user.id if request.user.is_authenticated else 'guest'}")
        
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Get size and quantity from POST data
        try:
            data = json.loads(request.body)
            logger.info(f"Request data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)
        
        size = data.get('size')
        try:
            quantity = int(data.get('quantity', 1))
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid quantity: {data.get('quantity')}")
            return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)
        
        if not size:
            logger.warning("Size not provided")
            return JsonResponse({'success': False, 'error': 'Size is required'}, status=400)
        
        if quantity < 1:
            logger.warning(f"Invalid quantity: {quantity}")
            return JsonResponse({'success': False, 'error': 'Quantity must be at least 1'}, status=400)
        
        # Check inventory availability
        try:
            inventory = Inventory.objects.get(product=product, size=size)
            logger.info(f"Inventory found: {inventory.quantity} items available")
            
            if not inventory.is_in_stock():
                logger.warning(f"Product {product_id} size {size} is out of stock")
                return JsonResponse({'success': False, 'error': 'Product is out of stock'}, status=400)
            
            if inventory.quantity < quantity:
                logger.warning(f"Insufficient inventory: requested {quantity}, available {inventory.quantity}")
                return JsonResponse({
                    'success': False, 
                    'error': f'Only {inventory.quantity} items available in stock'
                }, status=400)
        except Inventory.DoesNotExist:
            logger.error(f"Inventory not found for product {product_id} size {size}")
            return JsonResponse({'success': False, 'error': 'Size not available'}, status=400)
        
        # Get or create cart
        cart = get_or_create_cart(request)
        logger.info(f"Cart ID: {cart.id}")
        
        # Add or update cart item
        with transaction.atomic():
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                size=size,
                defaults={'quantity': quantity}
            )
            
            if not created:
                # Update existing item quantity
                new_quantity = cart_item.quantity + quantity
                if inventory.quantity < new_quantity:
                    logger.warning(f"Cannot add more: requested total {new_quantity}, available {inventory.quantity}")
                    return JsonResponse({
                        'success': False,
                        'error': f'Cannot add more. Only {inventory.quantity} items available in stock'
                    }, status=400)
                cart_item.quantity = new_quantity
                cart_item.save()
                logger.info(f"Updated cart item {cart_item.id} quantity to {new_quantity}")
            else:
                logger.info(f"Created new cart item {cart_item.id}")
        
        # Get updated cart count
        cart_count = cart.items.count()
        
        # Calculate updated price breakdown
        calculator = PriceCalculator(cart)
        price_breakdown = calculator.get_price_breakdown()
        
        logger.info(f"Successfully added to cart. Cart count: {cart_count}")
        
        return JsonResponse({
            'success': True,
            'message': 'Product added to cart',
            'cart_count': cart_count,
            'cart_total': float(price_breakdown['subtotal']),
            'tax': float(price_breakdown['tax']),
            'shipping': float(price_breakdown['shipping']),
            'final_total': float(price_breakdown['total'])
        })
        
    except Product.DoesNotExist:
        logger.error(f"Product {product_id} not found or inactive")
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in add_to_cart: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'}, status=500)

@require_POST
def update_cart_item(request, item_id):
    """Update cart item quantity with recalculation"""
    try:
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        # Get new quantity from POST data
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))
        
        if quantity < 1:
            return JsonResponse({'success': False, 'error': 'Quantity must be at least 1'}, status=400)
        
        # Check inventory availability
        try:
            inventory = Inventory.objects.get(product=cart_item.product, size=cart_item.size)
            if not inventory.is_in_stock():
                return JsonResponse({'success': False, 'error': 'Product is out of stock'}, status=400)
            if inventory.quantity < quantity:
                return JsonResponse({
                    'success': False,
                    'error': f'Only {inventory.quantity} items available in stock'
                }, status=400)
        except Inventory.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Size not available'}, status=400)
        
        # Update quantity
        with transaction.atomic():
            cart_item.quantity = quantity
            cart_item.save()
        
        # Recalculate totals using PriceCalculator
        item_subtotal = cart_item.get_subtotal()
        cart_count = cart.items.count()
        
        # Get coupon discount from session
        coupon_discount = Decimal(str(request.session.get('coupon_discount', 0)))
        calculator = PriceCalculator(cart, coupon_discount=coupon_discount)
        price_breakdown = calculator.get_price_breakdown()
        
        return JsonResponse({
            'success': True,
            'message': 'Cart updated',
            'item_subtotal': float(item_subtotal),
            'cart_total': float(price_breakdown['subtotal']),
            'tax': float(price_breakdown['tax']),
            'shipping': float(price_breakdown['shipping']),
            'discount': float(price_breakdown['discount']),
            'final_total': float(price_breakdown['total']),
            'cart_count': cart_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
def remove_from_cart(request, item_id):
    """Remove cart item with recalculation"""
    try:
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        # Delete the item
        with transaction.atomic():
            cart_item.delete()
        
        # Recalculate totals using PriceCalculator
        cart_count = cart.items.count()
        
        # Get coupon discount from session
        coupon_discount = Decimal(str(request.session.get('coupon_discount', 0)))
        calculator = PriceCalculator(cart, coupon_discount=coupon_discount)
        price_breakdown = calculator.get_price_breakdown()
        
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart',
            'cart_total': float(price_breakdown['subtotal']),
            'tax': float(price_breakdown['tax']),
            'shipping': float(price_breakdown['shipping']),
            'discount': float(price_breakdown['discount']),
            'final_total': float(price_breakdown['total']),
            'cart_count': cart_count
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
def apply_coupon(request):
    """Apply coupon code to cart"""
    try:
        data = json.loads(request.body)
        coupon_code = data.get('code', '').strip().upper()
        
        if not coupon_code:
            return JsonResponse({'success': False, 'error': 'Please enter a coupon code'}, status=400)
        
        # Check if coupon already applied
        if 'coupon_code' in request.session:
            return JsonResponse({'success': False, 'error': 'A coupon is already applied. Remove it first to apply a different one.'}, status=400)
        
        # Get coupon from database
        try:
            from .models import Coupon
            coupon = Coupon.objects.get(code=coupon_code)
        except Coupon.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid coupon code'}, status=400)
        
        # Validate coupon
        if not coupon.is_valid():
            from django.utils import timezone
            now = timezone.now()
            
            if not coupon.is_active:
                return JsonResponse({'success': False, 'error': 'This coupon is no longer active'}, status=400)
            elif now < coupon.valid_from:
                return JsonResponse({'success': False, 'error': 'This coupon is not yet valid'}, status=400)
            elif now > coupon.valid_to:
                return JsonResponse({'success': False, 'error': 'This coupon has expired'}, status=400)
            elif coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
                return JsonResponse({'success': False, 'error': 'This coupon has reached its usage limit'}, status=400)
        
        # Get cart and calculate discount
        cart = get_or_create_cart(request)
        cart_total = cart.get_total()
        
        # Check minimum purchase amount
        if cart_total < coupon.min_purchase_amount:
            return JsonResponse({
                'success': False, 
                'error': f'Minimum purchase amount of ${coupon.min_purchase_amount} required'
            }, status=400)
        
        # Calculate discount
        if coupon.discount_type == 'percentage':
            discount = (cart_total * coupon.discount_value) / 100
            # Apply max discount cap if set
            if coupon.max_discount_amount:
                discount = min(discount, coupon.max_discount_amount)
        else:  # fixed
            discount = coupon.discount_value
        
        # Ensure discount doesn't exceed cart total
        discount = min(discount, cart_total)
        
        # Store coupon in session
        request.session['coupon_code'] = coupon.code
        request.session['coupon_discount'] = float(discount)
        
        # Calculate new total using PriceCalculator
        calculator = PriceCalculator(cart, coupon_discount=discount)
        price_breakdown = calculator.get_price_breakdown()
        
        return JsonResponse({
            'success': True,
            'message': 'Coupon applied successfully',
            'discount': float(discount),
            'cart_total': float(price_breakdown['subtotal']),
            'tax': float(price_breakdown['tax']),
            'shipping': float(price_breakdown['shipping']),
            'final_total': float(price_breakdown['total']),
            'coupon_code': coupon.code
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
def remove_coupon(request):
    """Remove applied coupon"""
    try:
        # Check if coupon is applied
        if 'coupon_code' not in request.session:
            return JsonResponse({'success': False, 'error': 'No coupon applied'}, status=400)
        
        # Remove coupon from session
        del request.session['coupon_code']
        del request.session['coupon_discount']
        
        # Get cart total using PriceCalculator
        cart = get_or_create_cart(request)
        calculator = PriceCalculator(cart)
        price_breakdown = calculator.get_price_breakdown()
        
        return JsonResponse({
            'success': True,
            'message': 'Coupon removed',
            'cart_total': float(price_breakdown['subtotal']),
            'tax': float(price_breakdown['tax']),
            'shipping': float(price_breakdown['shipping']),
            'final_total': float(price_breakdown['total'])
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
