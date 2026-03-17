from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import models
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user
from .models import Banner, Category, Product

def home(request):
    """Homepage view - displays banners, categories, and new arrivals"""
    # Get active banners ordered by display_order
    banners = Banner.objects.filter(is_active=True).order_by('display_order', '-created_at')
    
    # Get featured categories (top-level categories with images)
    featured_categories = Category.objects.filter(
        parent__isnull=True,
        is_active=True
    ).exclude(image='').order_by('name')
    
    # Get 12 newest products
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at')[:12]
    
    # Get user's wishlist product IDs if authenticated
    user_wishlist_ids = []
    if request.user.is_authenticated:
        from .models import Wishlist
        user_wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
    
    context = {
        'banners': banners,
        'featured_categories': featured_categories,
        'new_arrivals': new_arrivals,
        'user_wishlist_ids': user_wishlist_ids,
    }
    
    return render(request, 'products/home.html', context)

def category_products(request, category_slug):
    """Category products listing view with filtering support"""
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # Get the category by slug
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    
    # Determine if this is a parent category or subcategory
    if category.parent is None:
        # Parent category: get all products from this category and its subcategories
        # Get all subcategory IDs
        subcategory_ids = category.subcategories.filter(is_active=True).values_list('id', flat=True)
        # Get products from parent category and all subcategories
        products = Product.objects.filter(
            is_active=True
        ).filter(
            models.Q(category=category) | models.Q(category_id__in=subcategory_ids)
        )
    else:
        # Subcategory: get only products from this subcategory
        products = Product.objects.filter(
            category=category,
            is_active=True
        )
    
    # Apply filters
    # Price range filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass
    
    # Size filter (multiple selections)
    sizes = request.GET.getlist('size')
    if sizes:
        products = products.filter(sizes__size__in=sizes, sizes__is_available=True).distinct()
    
    # Color filter (multiple selections)
    colors = request.GET.getlist('color')
    if colors:
        products = products.filter(colors__color_name__in=colors, colors__is_available=True).distinct()
    
    # Brand filter (multiple selections)
    brands = request.GET.getlist('brand')
    if brands:
        products = products.filter(brand__in=brands)
    
    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:
        products = products.order_by('-created_at')
    
    # Get available filter options for this category
    # Get all products in category (before filtering) for filter options
    if category.parent is None:
        all_category_products = Product.objects.filter(
            is_active=True
        ).filter(
            models.Q(category=category) | models.Q(category_id__in=subcategory_ids)
        )
    else:
        all_category_products = Product.objects.filter(
            category=category,
            is_active=True
        )
    
    # Get available sizes
    from .models import ProductSize
    available_sizes = ProductSize.objects.filter(
        product__in=all_category_products,
        is_available=True
    ).values_list('size', flat=True).distinct().order_by('size')
    
    # Get available colors
    from .models import ProductColor
    available_colors = ProductColor.objects.filter(
        product__in=all_category_products,
        is_available=True
    ).values_list('color_name', flat=True).distinct().order_by('color_name')
    
    # Get available brands
    available_brands = all_category_products.exclude(
        brand=''
    ).values_list('brand', flat=True).distinct().order_by('brand')
    
    # Get user's wishlist product IDs if authenticated
    user_wishlist_ids = []
    if request.user.is_authenticated:
        from .models import Wishlist
        user_wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
    
    # Pagination - 12 products per page
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Build query string for pagination (preserve filters)
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    query_string = query_params.urlencode()
    
    context = {
        'category': category,
        'products': page_obj,
        'page_obj': page_obj,
        'available_sizes': available_sizes,
        'available_colors': available_colors,
        'available_brands': available_brands,
        'selected_sizes': sizes,
        'selected_colors': colors,
        'selected_brands': brands,
        'min_price': min_price or '',
        'max_price': max_price or '',
        'sort_by': sort_by,
        'query_string': query_string,
        'user_wishlist_ids': user_wishlist_ids,
    }
    
    return render(request, 'products/category_products.html', context)

def product_detail(request, product_slug):
    """Product detail view - displays comprehensive product information"""
    from django.db.models import Avg
    
    # Get the product by slug
    product = get_object_or_404(Product, slug=product_slug, is_active=True)
    
    # Get all product images
    product_images = product.images.all().order_by('-is_primary', 'created_at')
    
    # Get available sizes from Inventory (source of truth), exclude 'One Size'
    from .models import Inventory as InventoryModel
    SIZE_ORDER = {'XS': 0, 'S': 1, 'M': 2, 'L': 3, 'XL': 4, 'XXL': 5}
    raw_sizes = list(
        InventoryModel.objects.filter(product=product, quantity__gt=0)
        .exclude(size='One Size')
        .values_list('size', flat=True)
        .distinct()
    )
    available_sizes = sorted(raw_sizes, key=lambda s: SIZE_ORDER.get(s, 99))
    
    # Get customer reviews and calculate average rating
    reviews = product.reviews.all().select_related('user').order_by('-created_at')
    average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Get similar products from the same category (4+ items)
    similar_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).order_by('-created_at')[:6]
    
    # Check if product is in user's wishlist
    in_wishlist = False
    if request.user.is_authenticated:
        from .models import Wishlist
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()
    
    context = {
        'product': product,
        'product_images': product_images,
        'available_sizes': available_sizes,
        'reviews': reviews,
        'average_rating': average_rating,
        'review_count': reviews.count(),
        'similar_products': similar_products,
        'in_wishlist': in_wishlist,
    }
    
    return render(request, 'products/product_detail.html', context)

def search_products(request):
    """Product search view - displays products matching search query"""
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    query = request.GET.get('q', '').strip()
    products = []
    
    if query:
        # Search in product name and description
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True
        ).order_by('-created_at')
    
    # Get user's wishlist product IDs if authenticated
    user_wishlist_ids = []
    if request.user.is_authenticated:
        from .models import Wishlist
        user_wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
    
    # Pagination - 12 products per page
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'query': query,
        'products': page_obj,
        'page_obj': page_obj,
        'total_results': products.count() if query else 0,
        'user_wishlist_ids': user_wishlist_ids,
    }
    
    return render(request, 'products/search_results.html', context)

def search_suggestions(request):
    """AJAX endpoint for search auto-suggestions"""
    from django.db.models import Q
    
    query = request.GET.get('q', '').strip()
    suggestions = []
    
    if query and len(query) >= 2:  # Only suggest if query is at least 2 characters
        # Get up to 10 product names matching the query
        products = Product.objects.filter(
            name__icontains=query,
            is_active=True
        ).values('id', 'name', 'slug')[:10]
        
        suggestions = list(products)
    
    return JsonResponse({'suggestions': suggestions})

@login_required
def wishlist(request):
    """User wishlist view"""
    return render(request, 'products/wishlist.html')

@login_required
def get_wishlist_items(request):
    """Get wishlist items as JSON"""
    from django.urls import reverse
    from .models import Wishlist
    
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    
    items = []
    for item in wishlist_items:
        product = item.product
        # Get primary image or first image
        image = product.images.filter(is_primary=True).first() or product.images.first()
        image_url = image.image.url if image else 'https://via.placeholder.com/250x250?text=No+Image'
        
        items.append({
            'product_id': product.id,
            'name': product.name,
            'price': str(product.price),
            'image_url': image_url,
            'product_url': reverse('products:product_detail', args=[product.slug]),
            'in_stock': product.is_in_stock(),
            'added_at': item.created_at.isoformat(),
        })
    
    return JsonResponse({'items': items})

@require_http_methods(["POST"])
def add_to_wishlist(request, product_id):
    """Add product to wishlist or toggle if already exists"""
    from .models import Wishlist
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Please login to add items to wishlist',
            'redirect': '/users/login/'
        }, status=401)
    
    try:
        # Log the request for debugging
        logger.info(f"Wishlist request from user {request.user.id} for product {product_id}")
        
        product = get_object_or_404(Product, id=product_id, is_active=True)
        wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
        
        if wishlist_item:
            # Toggle: remove if already in wishlist
            wishlist_item.delete()
            logger.info(f"Product {product_id} removed from wishlist for user {request.user.id}")
            return JsonResponse({
                'success': True, 
                'message': 'Product removed from wishlist',
                'in_wishlist': False
            })
        else:
            # Add to wishlist
            Wishlist.objects.create(user=request.user, product=product)
            logger.info(f"Product {product_id} added to wishlist for user {request.user.id}")
            return JsonResponse({
                'success': True, 
                'message': 'Product added to wishlist',
                'in_wishlist': True
            })
    except Product.DoesNotExist:
        logger.error(f"Product {product_id} not found or inactive")
        return JsonResponse({
            'success': False, 
            'message': 'Product not found or unavailable'
        }, status=404)
    except Exception as e:
        logger.error(f"Error adding to wishlist: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False, 
            'message': f'An error occurred: {str(e)}'
        }, status=400)

@login_required
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist"""
    from .models import Wishlist
    
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, id=product_id)
            wishlist_item = Wishlist.objects.filter(
                user=request.user,
                product=product
            )
            
            if wishlist_item.exists():
                wishlist_item.delete()
                return JsonResponse({'success': True, 'message': 'Product removed from wishlist'})
            else:
                return JsonResponse({'success': False, 'message': 'Product not in wishlist'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)


def dashboard(request):
    """Public-facing e-commerce dashboard with order and inventory metrics"""
    from django.db.models import Sum, Count, Q
    from orders.models import Order, ReturnRequest
    from .models import Product, Inventory

    # --- Order Metrics ---
    total_shipped = Order.objects.filter(status__in=['shipped', 'out_for_delivery']).count()
    total_delivered = Order.objects.filter(status='delivered').count()
    total_new_orders = Order.objects.filter(status='pending').count()
    total_processing = Order.objects.filter(status='processing').count()
    total_cancelled = Order.objects.filter(status='cancelled').count()

    # Returns
    total_returned = ReturnRequest.objects.filter(status__in=['approved', 'completed']).count()

    # Damaged: use cancelled orders as proxy (no dedicated damaged field in model)
    total_damaged = 0  # placeholder — no 'damaged' status in current model

    # --- Live Order Tracking (last 20 active orders) ---
    live_orders = Order.objects.select_related('user').filter(
        status__in=['pending', 'processing', 'shipped', 'out_for_delivery']
    ).order_by('-created_at')[:20]

    # --- Inventory ---
    LOW_STOCK_THRESHOLD = 10
    REORDER_TARGET = 50

    # Products with stock info
    inventory_items = Inventory.objects.select_related('product', 'product__category').order_by(
        'quantity', 'product__name'
    )

    # Current stock summary
    total_in_stock = Product.objects.filter(is_active=True, inventory__gt=0).count()
    total_out_of_stock = Product.objects.filter(is_active=True, inventory=0).count()
    low_stock_items = inventory_items.filter(quantity__gt=0, quantity__lte=LOW_STOCK_THRESHOLD)
    out_of_stock_items = inventory_items.filter(quantity=0)

    # Replenishment: items that need restocking (below threshold)
    replenishment_items = inventory_items.filter(quantity__lte=LOW_STOCK_THRESHOLD).select_related('product')
    # Calculate how much to order for each
    replenishment_data = []
    for item in replenishment_items:
        needed = max(0, REORDER_TARGET - item.quantity)
        replenishment_data.append({
            'product': item.product.name,
            'category': item.product.category.name,
            'size': item.size,
            'current_qty': item.quantity,
            'needed': needed,
        })

    context = {
        'total_shipped': total_shipped,
        'total_delivered': total_delivered,
        'total_new_orders': total_new_orders,
        'total_processing': total_processing,
        'total_cancelled': total_cancelled,
        'total_returned': total_returned,
        'total_damaged': total_damaged,
        'live_orders': live_orders,
        'total_in_stock': total_in_stock,
        'total_out_of_stock': total_out_of_stock,
        'low_stock_items': low_stock_items,
        'out_of_stock_items': out_of_stock_items,
        'replenishment_data': replenishment_data,
        'low_stock_count': low_stock_items.count(),
        'replenishment_count': len(replenishment_data),
    }
    return render(request, 'products/dashboard.html', context)


def remove_background(request):
    """Proxy view: calls remove.bg API and returns PNG with transparent background.
    Accepts either an uploaded file (image_file) or a local path (image_url).
    Sends raw image bytes to remove.bg so localhost URLs work fine.
    """
    import requests as req
    import base64
    import os
    from django.conf import settings

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    api_key = settings.REMOVEBG_API_KEY

    # Try to get raw image bytes — prefer uploaded file, fall back to local path
    image_bytes = None

    if request.FILES.get('image_file'):
        image_bytes = request.FILES['image_file'].read()
    else:
        image_url = request.POST.get('image_url', '')
        if not image_url:
            return JsonResponse({'error': 'No image provided'}, status=400)

        # Convert URL to local filesystem path
        # e.g. http://localhost:8000/media/products/foo.jpg → MEDIA_ROOT/products/foo.jpg
        from urllib.parse import urlparse
        parsed = urlparse(image_url)
        url_path = parsed.path  # e.g. /media/products/foo.jpg

        # Strip MEDIA_URL prefix to get relative path inside MEDIA_ROOT
        media_url = settings.MEDIA_URL  # e.g. '/media/'
        if url_path.startswith(media_url):
            rel_path = url_path[len(media_url):]
            local_path = os.path.join(settings.MEDIA_ROOT, rel_path)
            if os.path.exists(local_path):
                with open(local_path, 'rb') as f:
                    image_bytes = f.read()

        # If still no bytes (e.g. static file or external URL), fetch via requests
        if image_bytes is None:
            try:
                r = req.get(image_url, timeout=15)
                if r.status_code == 200:
                    image_bytes = r.content
            except Exception:
                pass

    if not image_bytes:
        return JsonResponse({'error': 'Could not load image'}, status=400)

    try:
        response = req.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': ('image.png', image_bytes)},
            data={'size': 'auto'},
            headers={'X-Api-Key': api_key},
            timeout=30
        )
        if response.status_code == 200:
            img_b64 = base64.b64encode(response.content).decode('utf-8')
            return JsonResponse({'success': True, 'image': f'data:image/png;base64,{img_b64}'})
        else:
            error_detail = response.text[:200] if response.text else str(response.status_code)
            return JsonResponse({'success': False, 'error': f'remove.bg: {error_detail}'}, status=200)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=200)





@require_http_methods(["POST"])
def submit_review(request, product_id):
    """Submit or update a product review"""
    from .models import Review
    import json

    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Please login to submit a review'}, status=401)

    try:
        data = json.loads(request.body)
        rating = int(data.get('rating', 0))
        comment = data.get('comment', '').strip()

        if not (1 <= rating <= 5):
            return JsonResponse({'success': False, 'error': 'Rating must be between 1 and 5'}, status=400)
        if not comment:
            return JsonResponse({'success': False, 'error': 'Review comment is required'}, status=400)

        product = get_object_or_404(Product, id=product_id, is_active=True)

        review, created = Review.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={'rating': rating, 'comment': comment}
        )

        return JsonResponse({
            'success': True,
            'created': created,
            'review': {
                'user': request.user.get_full_name() or request.user.email,
                'rating': review.rating,
                'comment': review.comment,
                'date': review.created_at.strftime('%b %d, %Y'),
            }
        })
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_product_reviews(request, product_id):
    """Fetch reviews for a product as JSON"""
    from .models import Review
    from django.db.models import Avg

    product = get_object_or_404(Product, id=product_id, is_active=True)
    reviews = Review.objects.filter(product=product).select_related('user').order_by('-created_at')
    avg = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    data = {
        'average_rating': round(avg, 1),
        'review_count': reviews.count(),
        'reviews': [
            {
                'user': r.user.get_full_name() or r.user.email,
                'rating': r.rating,
                'comment': r.comment,
                'date': r.created_at.strftime('%b %d, %Y'),
            }
            for r in reviews
        ]
    }
    return JsonResponse(data)
