from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import models
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
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
    from .models import ProductImage
    products = products.prefetch_related(
        models.Prefetch('images', queryset=ProductImage.objects.order_by('-is_primary', 'created_at'))
    )
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








# ── Size Recommender ──────────────────────────────────────────────────────────

@require_http_methods(["GET", "POST"])
@login_required
def size_recommender(request):
    from .models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        for field in ('height_cm', 'weight_kg', 'chest_cm', 'waist_cm', 'hips_cm'):
            val = data.get(field)
            setattr(profile, field, int(val) if val else None)
        profile.save()
        return JsonResponse({'success': True, 'recommended_size': profile.recommended_size()})

    return JsonResponse({
        'height_cm': profile.height_cm,
        'weight_kg': profile.weight_kg,
        'chest_cm':  profile.chest_cm,
        'waist_cm':  profile.waist_cm,
        'hips_cm':   profile.hips_cm,
        'recommended_size': profile.recommended_size(),
    })


# ── Complete the Look ─────────────────────────────────────────────────────────

def complete_the_look(request, product_id):
    """Return complementary products for a given product."""
    import random as _random
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cat_slug = product.category.slug.lower()

    # Map category → what to pair with
    PAIR_MAP = {
        'women-dresses':  ['women-heels', 'accessories-bags', 'accessories-sunglasses'],
        'women-tops':     ['women-skirts', 'women-heels', 'accessories-bags'],
        'women-skirts':   ['women-tops', 'women-heels', 'accessories-bags'],
        'men-shirts':     ['men-jeans', 'men-shoes', 'accessories-belts', 'accessories-watches'],
        'men-t-shirts':   ['men-jeans', 'men-shoes', 'accessories-watches'],
        'men-jackets':    ['men-jeans', 'men-shirts', 'men-shoes'],
        'men-jeans':      ['men-shirts', 'men-t-shirts', 'men-shoes', 'accessories-belts'],
        'women-heels':    ['women-dresses', 'women-skirts', 'accessories-bags'],
        'men-shoes':      ['men-jeans', 'men-shirts', 'accessories-belts'],
        'accessories-bags': ['women-dresses', 'women-tops', 'accessories-sunglasses'],
    }
    pair_slugs = PAIR_MAP.get(cat_slug, ['accessories-sunglasses', 'accessories-watches', 'accessories-bags'])

    from .models import Category as Cat
    results = []
    for slug in pair_slugs:
        try:
            cat = Cat.objects.get(slug=slug)
            p = Product.objects.filter(is_active=True, category=cat).order_by('?').first()
            if p:
                img = p.images.filter(is_primary=True).first() or p.images.first()
                results.append({
                    'id': p.id, 'name': p.name, 'price': str(p.price),
                    'slug': p.slug, 'category': cat.name,
                    'image': request.build_absolute_uri(img.image.url) if img else '',
                })
        except Cat.DoesNotExist:
            pass

    return JsonResponse({'success': True, 'products': results})


# ── Recently Viewed ───────────────────────────────────────────────────────────

@require_http_methods(["POST"])
def track_recently_viewed(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({'ok': True})
    from .models import RecentlyViewed
    from django.utils import timezone
    product = get_object_or_404(Product, id=product_id, is_active=True)
    rv, created = RecentlyViewed.objects.get_or_create(user=request.user, product=product)
    if not created:
        RecentlyViewed.objects.filter(pk=rv.pk).update(viewed_at=timezone.now())
    # Keep only last 20
    old_ids = list(RecentlyViewed.objects.filter(user=request.user).order_by('-viewed_at').values_list('id', flat=True)[20:])
    if old_ids:
        RecentlyViewed.objects.filter(id__in=old_ids).delete()
    return JsonResponse({'ok': True})


@login_required
def get_recently_viewed(request):
    from .models import RecentlyViewed
    items = RecentlyViewed.objects.filter(user=request.user).select_related('product')[:10]
    data = []
    for rv in items:
        p = rv.product
        img = p.images.filter(is_primary=True).first() or p.images.first()
        data.append({
            'id': p.id, 'name': p.name, 'price': str(p.price), 'slug': p.slug,
            'image': request.build_absolute_uri(img.image.url) if img else '',
        })
    return JsonResponse({'products': data})


# ── Stock Alerts ──────────────────────────────────────────────────────────────

@require_http_methods(["POST"])
@login_required
def subscribe_stock_alert(request, product_id):
    import json
    from .models import StockAlert
    product = get_object_or_404(Product, id=product_id, is_active=True)
    data = json.loads(request.body) if request.body else {}
    size = data.get('size', '')
    _, created = StockAlert.objects.get_or_create(user=request.user, product=product, size=size)
    return JsonResponse({'success': True, 'created': created,
                         'message': "You'll be notified when this item is back in stock."})





# ── Virtual Try-On (IDM-VTON via Hugging Face Space) ─────────────────────────

@ensure_csrf_cookie
def photo_tryon_page(request):
    """Render the Virtual Try-On page — clothing items only (no accessories)."""
    CLOTHING_SLUGS = [
        'women-tops', 'women-skirts', 'women-dresses',
        'men-shirts', 'men-t-shirts', 'men-jackets', 'men-jeans',
        'kids-girls', 'kids-boys', 'kids-infants',
    ]
    products = (
        Product.objects.filter(is_active=True, category__slug__in=CLOTHING_SLUGS)
        .prefetch_related('images', 'category')
        .filter(images__isnull=False)
        .distinct()
        .order_by('-created_at')[:60]
    )
    response = render(request, 'products/photo_tryon.html', {'products': products})
    # Prevent bfcache — stops the browser restoring a stale DOM with error banners visible
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response['Pragma'] = 'no-cache'
    return response


@require_http_methods(["POST"])
def photo_tryon_enqueue(request):
    """
    Save the uploaded photo, resolve garment paths, then run the try-on in a
    background thread.  Returns a task_id immediately for polling.

    Uses threading instead of Celery — avoids the Windows worker process issues
    with the filesystem broker.  Task state is stored as a JSON file in
    media/tryon_state/<task_id>.json so the status endpoint can read it.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'login_required'}, status=401)

    import tempfile, os, uuid, json, threading
    from django.conf import settings

    person_file   = request.FILES.get('photo')
    product_slugs = [s.strip() for s in request.POST.getlist('product_slugs') if s.strip()]
    tryon_mode    = request.POST.get('tryon_mode', 'adult')   # 'adult' | 'baby'
    if tryon_mode not in ('adult', 'baby'):
        tryon_mode = 'adult'

    if not person_file:
        return JsonResponse({'success': False, 'error': 'No photo uploaded.'}, status=400)
    if not product_slugs:
        return JsonResponse({'success': False, 'error': 'No garments selected.'}, status=400)
    if len(product_slugs) > 4:
        return JsonResponse({'success': False, 'error': 'Maximum 4 garments per outfit.'}, status=400)

    # Resolve garment infos
    garment_infos = []
    for slug in product_slugs:
        try:
            product = Product.objects.select_related('category').get(slug=slug, is_active=True)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': f'Product "{slug}" not found.'}, status=400)
        img = product.images.filter(is_primary=True).first() or product.images.first()
        if not img:
            return JsonResponse({'success': False, 'error': f'"{product.name}" has no image.'}, status=400)
        path = os.path.join(settings.MEDIA_ROOT, img.image.name)
        if not os.path.exists(path):
            return JsonResponse({'success': False, 'error': f'Image missing for "{product.name}".'}, status=400)
        garment_infos.append({
            'path': path,
            'category_slug': product.category.slug if product.category else '',
            'name': product.name,
            'product_id': product.id,
        })

    # Save person photo to temp file
    suffix = os.path.splitext(person_file.name)[1] or '.jpg'
    tryon_tmp_dir = os.path.join(settings.MEDIA_ROOT, 'tryon_tmp')
    os.makedirs(tryon_tmp_dir, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=tryon_tmp_dir)
    try:
        for chunk in person_file.chunks():
            tmp.write(chunk)
        tmp.close()
    except Exception as e:
        tmp.close()
        try: os.unlink(tmp.name)
        except OSError: pass
        return JsonResponse({'success': False, 'error': f'Could not save photo: {e}'}, status=500)

    # State file — written by the background thread, read by the status endpoint
    task_id   = uuid.uuid4().hex
    state_dir = os.path.join(settings.MEDIA_ROOT, 'tryon_state')
    os.makedirs(state_dir, exist_ok=True)
    state_path = os.path.join(state_dir, f'{task_id}.json')

    def _write_state(data: dict):
        with open(state_path, 'w') as f:
            json.dump(data, f)

    _write_state({'state': 'PENDING', 'label': 'Starting…'})

    user_id = request.user.id

    def _run():
        """Background thread — runs the full try-on chain and writes state updates."""
        import django
        django.db.close_old_connections()   # required for threads on Django

        from .tasks import _save_original, _record_history

        if tryon_mode == 'baby':
            # ── Baby / Kids mode — Stable Diffusion Inpainting ──────────────
            from .baby_tryon_service import run_baby_tryon
            try:
                _write_state({'state': 'PROGRESS', 'step': 1, 'total': 1,
                              'label': 'Loading AI model for baby try-on…'})
                result_local = run_baby_tryon(
                    person_path=tmp.name,
                    garment_infos=garment_infos,
                    write_state=_write_state,
                )
                _write_state({'state': 'PROGRESS', 'step': 1, 'total': 1,
                              'label': 'Finalizing your look…'})
                from .tryon_service import _save_result
                result_rel   = _save_result(result_local, settings.MEDIA_ROOT)
                original_rel = _save_original(tmp.name, settings.MEDIA_ROOT)
                _record_history(user_id, garment_infos[0].get('product_id') if garment_infos else None,
                                original_rel, result_rel)
                _write_state({'state': 'SUCCESS', 'result_url': result_rel})
            except Exception as e:
                msg = str(e)
                if 'interpreter shutdown' in msg.lower() or 'cannot schedule' in msg.lower():
                    msg = 'Server was reloaded during generation. Please try again.'
                _write_state({'state': 'FAILURE', 'error': msg, 'step_failed': 1})
            finally:
                try: os.unlink(tmp.name)
                except OSError: pass
                django.db.close_old_connections()
            return

        # ── Adult mode — IDM-VTON via Hugging Face ───────────────────────────
        from .tryon_service import _call_hf, _get_hf_client, _save_result, filter_and_sort_garments
        import shutil, tempfile as _tmp

        garments = filter_and_sort_garments(garment_infos)
        if not garments:
            _write_state({'state': 'FAILURE',
                          'error': 'No supported clothing items. Accessories are skipped.'})
            return

        total          = len(garments)
        current_person = tmp.name
        intermediates  = []

        try:
            _write_state({'state': 'PROGRESS', 'step': 0, 'total': total,
                          'label': 'Connecting to AI server…'})
            try:
                hf_client = _get_hf_client()
            except RuntimeError as e:
                _write_state({'state': 'FAILURE', 'error': str(e)})
                return

            for step, g in enumerate(garments, start=1):
                _write_state({'state': 'PROGRESS', 'step': step, 'total': total,
                              'label': f"Fitting {g['name']}…"})
                try:
                    result_local = _call_hf(current_person, g['path'],
                                            g['vton_category'], client=hf_client)
                except RuntimeError as e:
                    _write_state({'state': 'FAILURE', 'error': str(e), 'step_failed': step})
                    return

                if step < total:
                    ext = os.path.splitext(result_local)[1] or '.png'
                    t   = _tmp.NamedTemporaryFile(delete=False, suffix=ext)
                    t.close()
                    shutil.copy2(result_local, t.name)
                    intermediates.append(t.name)
                    current_person = t.name
                else:
                    _write_state({'state': 'PROGRESS', 'step': step, 'total': total,
                                  'label': 'Finalizing your look…'})
                    result_rel   = _save_result(result_local, settings.MEDIA_ROOT)
                    original_rel = _save_original(tmp.name, settings.MEDIA_ROOT)
                    _record_history(user_id, garments[0].get('product_id'),
                                    original_rel, result_rel)
                    _write_state({'state': 'SUCCESS', 'result_url': result_rel})

        except Exception as e:
            msg = str(e)
            if 'interpreter shutdown' in msg.lower() or 'cannot schedule' in msg.lower():
                msg = 'Server was reloaded during generation. Please try again.'
            _write_state({'state': 'FAILURE', 'error': msg})
        finally:
            for f in intermediates:
                try: os.unlink(f)
                except OSError: pass
            try: os.unlink(tmp.name)
            except OSError: pass
            django.db.close_old_connections()

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return JsonResponse({'success': True, 'task_id': task_id, 'total': len(garment_infos)})


def photo_tryon_status(request, task_id):
    """
    Poll endpoint — reads the JSON state file written by the background thread.
    """
    import json, os, re
    from django.conf import settings

    # Validate task_id is a hex string to prevent path traversal
    if not re.fullmatch(r'[0-9a-f]{32}', task_id):
        return JsonResponse({'state': 'FAILURE', 'error': 'Invalid task ID.'})

    state_path = os.path.join(settings.MEDIA_ROOT, 'tryon_state', f'{task_id}.json')

    if not os.path.exists(state_path):
        return JsonResponse({'state': 'PENDING', 'label': 'Waiting to start…'})

    try:
        with open(state_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return JsonResponse({'state': 'PENDING', 'label': 'Starting…'})

    state = data.get('state', 'PENDING')

    if state == 'PENDING':
        return JsonResponse({'state': 'PENDING', 'label': data.get('label', 'Waiting…')})

    if state == 'PROGRESS':
        return JsonResponse({
            'state': 'PROGRESS',
            'step':  data.get('step', 0),
            'total': data.get('total', 0),
            'label': data.get('label', 'Processing…'),
        })

    if state == 'SUCCESS':
        full_url = request.build_absolute_uri(settings.MEDIA_URL + data['result_url'])
        # Delete state file — result is now in the response, no need to keep it
        try: os.unlink(state_path)
        except OSError: pass
        return JsonResponse({'state': 'SUCCESS', 'result_url': full_url})

    # FAILURE — delete state file so it can't bleed into future page loads
    try: os.unlink(state_path)
    except OSError: pass
    return JsonResponse({
        'state': 'FAILURE',
        'error': data.get('error', 'Unknown error'),
        'step_failed': data.get('step_failed'),
    })


# ── Try-On History (Virtual Wardrobe) ────────────────────────────────────────

@login_required
def tryon_history(request):
    """Display the logged-in user's Virtual Try-On history, newest first."""
    from .models import TryOnHistory
    records = (
        TryOnHistory.objects
        .filter(user=request.user)
        .select_related('product', 'product__category')
        .order_by('-created_at')
    )
    return render(request, 'products/tryon_history.html', {'records': records})


def get_product_sizes(request, product_id):
    """Return available sizes for a product (used by My Wardrobe add-to-cart)."""
    from .models import Inventory
    sizes = list(
        Inventory.objects.filter(product_id=product_id, quantity__gt=0)
        .exclude(size='One Size')
        .values_list('size', flat=True)
        .distinct()
    )
    SIZE_ORDER = {'XS': 0, 'S': 1, 'M': 2, 'L': 3, 'XL': 4, 'XXL': 5}
    sizes.sort(key=lambda s: SIZE_ORDER.get(s, 99))
    return JsonResponse({'sizes': sizes})


# ── AR Try-On (MediaPipe — fully client-side) ─────────────────────────────────

def ar_tryon(request, product_id):
    """
    Render the live AR try-on page.

    Passes to template:
      product            — the Product instance
      product_image_url  — URL of the primary product image (PNG preferred)
      ar_mode            — 'face' | 'hands' | 'pose'  (which MediaPipe model to load)
      ar_category        — exact keyword used in the JS switch() for landmark mapping
    """
    from django.templatetags.static import static

    product = get_object_or_404(Product, id=product_id, is_active=True)

    cat_slug = product.category.slug if product.category else ''

    # ── Static transparent AR assets (used instead of product photos) ────────
    # Product photos are portraits of people wearing items — not transparent cutouts.
    # For AR overlay we need transparent-background PNGs anchored to landmarks.
    STATIC_AR_ASSETS = {
        'accessories-sunglasses': 'ar_assets/sunglasses.png',
    }

    if cat_slug in STATIC_AR_ASSETS:
        product_image_url = request.build_absolute_uri(static(STATIC_AR_ASSETS[cat_slug]))
    else:
        # Prefer PNG images (transparent background) for clean overlay
        img = (
            product.images.filter(image__endswith='.png', is_primary=True).first()
            or product.images.filter(image__endswith='.png').first()
            or product.images.filter(is_primary=True).first()
            or product.images.first()
        )
        product_image_url = img.image.url if img else ''

    # ── Map category slug → (ar_mode, ar_category keyword) ───────────────────
    # ar_mode     → which MediaPipe solution to load (face / hands / pose)
    # ar_category → the keyword used in the JS switch() for landmark placement
    SLUG_MAP = {
        # Face
        'accessories-sunglasses': ('face',  'sunglasses'),
        'women-earrings':         ('face',  'earrings'),
        'women-necklaces':        ('face',  'necklaces'),
        # Hands
        'accessories-watches':    ('hands', 'watches'),
        'accessories-bags':       ('hands', 'bags'),
        # Pose — upper body
        'women-tops':             ('pose',  'tops'),
        'men-shirts':             ('pose',  'shirts'),
        'men-t-shirts':           ('pose',  't-shirts'),
        'men-jackets':            ('pose',  'jackets'),
        'kids-boys':              ('pose',  'boys'),
        'kids-girls':             ('pose',  'girls'),
        'kids-infants':           ('pose',  'infants'),
        # Pose — dresses
        'women-dresses':          ('pose',  'dresses'),
        # Pose — lower body
        'accessories-belts':      ('pose',  'belts'),
        'women-skirts':           ('pose',  'skirts'),
        'men-jeans':              ('pose',  'jeans'),
        # Pose — footwear
        'men-shoes':              ('pose',  'shoes'),
        'women-heels':            ('pose',  'heels'),
    }

    ar_mode, ar_category = SLUG_MAP.get(cat_slug, ('pose', 'tops'))

    return render(request, 'products/ar_tryon.html', {
        'product':           product,
        'product_image_url': product_image_url,
        'ar_mode':           ar_mode,
        'ar_category':       ar_category,
    })
