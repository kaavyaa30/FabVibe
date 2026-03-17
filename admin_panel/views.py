from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from orders.models import Order
from products.models import Product, Category, Inventory, Banner
from django.contrib.auth import get_user_model

User = get_user_model()

@staff_member_required
def dashboard(request):
    """Admin dashboard view with metrics"""
    # Get date range from request or default to current month
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from and date_to:
        from datetime import datetime
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    else:
        # Default to current month
        today = timezone.now().date()
        date_from = today.replace(day=1)
        date_to = today
    
    # Calculate metrics
    orders_in_range = Order.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    )
    
    # Total sales revenue (only completed orders)
    total_revenue = orders_in_range.filter(
        payment_status='completed'
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')
    
    # Total number of orders
    total_orders = orders_in_range.count()
    
    # Total registered customers (all time)
    total_customers = User.objects.filter(is_staff=False).count()
    
    # New customers in date range
    new_customers = User.objects.filter(
        is_staff=False,
        date_joined__date__gte=date_from,
        date_joined__date__lte=date_to
    ).count()
    
    # Recent orders
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]
    
    # Low stock products
    low_stock_products = Product.objects.filter(
        inventory__lte=10,
        inventory__gt=0,
        is_active=True
    ).order_by('inventory')[:10]
    
    # Out of stock products
    out_of_stock_products = Product.objects.filter(
        inventory=0,
        is_active=True
    ).count()
    
    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_customers': total_customers,
        'new_customers': new_customers,
        'recent_orders': recent_orders,
        'low_stock_products': low_stock_products,
        'out_of_stock_count': out_of_stock_products,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'admin_panel/dashboard.html', context)

@staff_member_required
def product_list(request):
    """Product list view"""
    products = Product.objects.select_related('category').prefetch_related('inventory_items').order_by('-created_at')
    
    # Add search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(brand__icontains=search_query)
        )
    
    context = {
        'products': products,
        'search_query': search_query,
    }
    return render(request, 'admin_panel/product_list.html', context)

@staff_member_required
def product_add(request):
    """Add product view"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.POST.get('name')
            description = request.POST.get('description')
            price = Decimal(request.POST.get('price'))
            category_id = request.POST.get('category')
            brand = request.POST.get('brand', '')
            material = request.POST.get('material', '')
            care_instructions = request.POST.get('care_instructions', '')
            
            # Create product
            from django.utils.text import slugify
            product = Product.objects.create(
                name=name,
                slug=slugify(name),
                description=description,
                price=price,
                category_id=category_id,
                brand=brand,
                material=material,
                care_instructions=care_instructions,
                is_active=True
            )
            
            # Handle sizes and inventory
            sizes = request.POST.getlist('sizes[]')
            quantities = request.POST.getlist('quantities[]')
            
            total_inventory = 0
            for size, quantity in zip(sizes, quantities):
                if size and quantity:
                    qty = int(quantity)
                    Inventory.objects.create(
                        product=product,
                        size=size,
                        quantity=qty
                    )
                    total_inventory += qty
            
            # Update product total inventory
            product.inventory = total_inventory
            product.save()
            
            # Handle image uploads
            images = request.FILES.getlist('images')
            from products.models import ProductImage
            for i, image in enumerate(images):
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_primary=(i == 0)
                )
            
            messages.success(request, f'Product "{product.name}" created successfully.')
            return redirect('admin_panel:product_list')
            
        except Exception as e:
            messages.error(request, f'Error creating product: {str(e)}')
    
    categories = Category.objects.all().order_by('name')
    context = {
        'categories': categories,
        'sizes': ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
    }
    return render(request, 'admin_panel/product_form.html', context)

@staff_member_required
def product_edit(request, product_id):
    """Edit product view"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        try:
            # Update product fields
            product.name = request.POST.get('name')
            product.description = request.POST.get('description')
            product.price = Decimal(request.POST.get('price'))
            product.category_id = request.POST.get('category')
            product.brand = request.POST.get('brand', '')
            product.material = request.POST.get('material', '')
            product.care_instructions = request.POST.get('care_instructions', '')
            product.is_active = request.POST.get('is_active') == 'on'
            product.save()
            
            # Update inventory
            sizes = request.POST.getlist('sizes[]')
            quantities = request.POST.getlist('quantities[]')
            
            # Clear existing inventory
            Inventory.objects.filter(product=product).delete()
            
            total_inventory = 0
            for size, quantity in zip(sizes, quantities):
                if size and quantity:
                    qty = int(quantity)
                    Inventory.objects.create(
                        product=product,
                        size=size,
                        quantity=qty
                    )
                    total_inventory += qty
            
            # Update product total inventory
            product.inventory = total_inventory
            product.save()
            
            # Handle new image uploads
            images = request.FILES.getlist('images')
            from products.models import ProductImage
            for image in images:
                ProductImage.objects.create(
                    product=product,
                    image=image,
                    is_primary=False
                )
            
            messages.success(request, f'Product "{product.name}" updated successfully.')
            return redirect('admin_panel:product_list')
            
        except Exception as e:
            messages.error(request, f'Error updating product: {str(e)}')
    
    categories = Category.objects.all().order_by('name')
    inventories = Inventory.objects.filter(product=product)
    
    context = {
        'product': product,
        'categories': categories,
        'inventories': inventories,
        'sizes': ['XS', 'S', 'M', 'L', 'XL', 'XXL'],
    }
    return render(request, 'admin_panel/product_form.html', context)

@staff_member_required
def product_delete(request, product_id):
    """Delete product view"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully.')
        return redirect('admin_panel:product_list')
    
    return render(request, 'admin_panel/product_confirm_delete.html', {'product': product})

@staff_member_required
def category_list(request):
    """Category list view"""
    categories = Category.objects.prefetch_related('subcategories').order_by('name')
    
    # Separate parent categories and subcategories for display
    parent_categories = categories.filter(parent__isnull=True)
    
    context = {
        'categories': parent_categories,
    }
    return render(request, 'admin_panel/category_list.html', context)

@staff_member_required
def category_add(request):
    """Add category view"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            parent_id = request.POST.get('parent')
            description = request.POST.get('description', '')
            
            # Check if category name already exists
            if Category.objects.filter(name=name).exists():
                messages.error(request, f'Category "{name}" already exists.')
                return redirect('admin_panel:category_add')
            
            # Create category
            from django.utils.text import slugify
            category = Category.objects.create(
                name=name,
                slug=slugify(name),
                parent_id=parent_id if parent_id else None,
                description=description,
                is_active=True
            )
            
            # Handle image upload
            if 'image' in request.FILES:
                category.image = request.FILES['image']
                category.save()
            
            category_type = "Subcategory" if parent_id else "Category"
            messages.success(request, f'{category_type} "{category.name}" created successfully.')
            return redirect('admin_panel:category_list')
            
        except Exception as e:
            messages.error(request, f'Error creating category: {str(e)}')
    
    # Get parent categories for subcategory creation
    parent_categories = Category.objects.filter(parent__isnull=True).order_by('name')
    
    context = {
        'parent_categories': parent_categories,
    }
    return render(request, 'admin_panel/category_form.html', context)

@staff_member_required
def category_edit(request, category_id):
    """Edit category view"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            parent_id = request.POST.get('parent')
            description = request.POST.get('description', '')
            
            # Check if new name conflicts with existing category (excluding current)
            if Category.objects.filter(name=name).exclude(id=category_id).exists():
                messages.error(request, f'Category "{name}" already exists.')
                return redirect('admin_panel:category_edit', category_id=category_id)
            
            # Update category
            category.name = name
            category.parent_id = parent_id if parent_id else None
            category.description = description
            category.is_active = request.POST.get('is_active') == 'on'
            
            # Handle image upload
            if 'image' in request.FILES:
                category.image = request.FILES['image']
            
            category.save()
            
            messages.success(request, f'Category "{category.name}" updated successfully.')
            return redirect('admin_panel:category_list')
            
        except Exception as e:
            messages.error(request, f'Error updating category: {str(e)}')
    
    # Get parent categories (excluding self and descendants)
    parent_categories = Category.objects.filter(parent__isnull=True).exclude(id=category_id).order_by('name')
    
    context = {
        'category': category,
        'parent_categories': parent_categories,
    }
    return render(request, 'admin_panel/category_form.html', context)

@staff_member_required
def category_delete(request, category_id):
    """Delete category view"""
    category = get_object_or_404(Category, id=category_id)
    
    # Check if category has products
    if category.products.exists():
        messages.error(request, f'Cannot delete category "{category.name}" because it has associated products. Please reassign or delete the products first.')
        return redirect('admin_panel:category_list')
    
    # Check if category has subcategories
    if category.subcategories.exists():
        messages.error(request, f'Cannot delete category "{category.name}" because it has subcategories. Please delete subcategories first.')
        return redirect('admin_panel:category_list')
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted successfully.')
        return redirect('admin_panel:category_list')
    
    return render(request, 'admin_panel/category_confirm_delete.html', {'category': category})

@staff_member_required
def order_list(request):
    """Order list view"""
    orders = Order.objects.select_related('user').prefetch_related('items__product').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        from datetime import datetime
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        from datetime import datetime
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        orders = orders.filter(created_at__date__lte=date_to)
    
    # Search by order ID or customer
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'admin_panel/order_list.html', context)

@staff_member_required
def order_detail(request, order_id):
    """Order detail view"""
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.select_related('product').all()
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'admin_panel/order_detail.html', context)

@staff_member_required
def update_order_status(request, order_id):
    """Update order status"""
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        tracking_number = request.POST.get('tracking_number', '')
        
        if new_status in dict(Order.STATUS_CHOICES):
            old_status = order.status
            order.status = new_status
            
            # Update tracking number if provided
            if tracking_number:
                order.tracking_number = tracking_number
            
            # Set delivered_at timestamp if status is delivered
            if new_status == 'delivered' and not order.delivered_at:
                order.delivered_at = timezone.now()
            
            order.save()
            
            # Send notification to customer
            from orders.tasks import send_order_status_update_email, send_order_status_update_sms
            send_order_status_update_email(order.id)
            send_order_status_update_sms(order.id)

            # Trigger OTP when out for delivery
            if new_status == 'out_for_delivery':
                from orders.tasks import send_delivery_otp_sms
                send_delivery_otp_sms(order.id)

            # Trigger shipped SMS with tracking link
            if new_status == 'shipped':
                from orders.tasks import send_shipped_sms
                send_shipped_sms(order.id)
            
            messages.success(request, f'Order status updated from {old_status} to {new_status}.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Status updated successfully'})
        else:
            messages.error(request, 'Invalid status.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Invalid status'})
    
    return redirect('admin_panel:order_detail', order_id=order_id)

@staff_member_required
def banner_list(request):
    """Banner list view"""
    banners = Banner.objects.all().order_by('display_order', '-created_at')
    
    context = {
        'banners': banners,
    }
    return render(request, 'admin_panel/banner_list.html', context)

@staff_member_required
def banner_add(request):
    """Add banner view"""
    if request.method == 'POST':
        try:
            title = request.POST.get('title')
            link_url = request.POST.get('link_url', '')
            display_order = int(request.POST.get('display_order', 0))
            is_active = request.POST.get('is_active') == 'on'
            
            # Create banner
            banner = Banner.objects.create(
                title=title,
                link_url=link_url,
                display_order=display_order,
                is_active=is_active
            )
            
            # Handle image upload
            if 'image' in request.FILES:
                banner.image = request.FILES['image']
                banner.save()
            else:
                messages.error(request, 'Banner image is required.')
                banner.delete()
                return redirect('admin_panel:banner_add')
            
            messages.success(request, f'Banner "{banner.title}" created successfully.')
            return redirect('admin_panel:banner_list')
            
        except Exception as e:
            messages.error(request, f'Error creating banner: {str(e)}')
    
    # Get next display order
    last_banner = Banner.objects.order_by('-display_order').first()
    next_order = (last_banner.display_order + 1) if last_banner else 1
    
    context = {
        'next_order': next_order,
    }
    return render(request, 'admin_panel/banner_form.html', context)

@staff_member_required
def banner_edit(request, banner_id):
    """Edit banner view"""
    banner = get_object_or_404(Banner, id=banner_id)
    
    if request.method == 'POST':
        try:
            banner.title = request.POST.get('title')
            banner.link_url = request.POST.get('link_url', '')
            banner.display_order = int(request.POST.get('display_order', 0))
            banner.is_active = request.POST.get('is_active') == 'on'
            
            # Handle image upload
            if 'image' in request.FILES:
                banner.image = request.FILES['image']
            
            banner.save()
            
            messages.success(request, f'Banner "{banner.title}" updated successfully.')
            return redirect('admin_panel:banner_list')
            
        except Exception as e:
            messages.error(request, f'Error updating banner: {str(e)}')
    
    context = {
        'banner': banner,
    }
    return render(request, 'admin_panel/banner_form.html', context)

@staff_member_required
def banner_delete(request, banner_id):
    """Delete banner view"""
    banner = get_object_or_404(Banner, id=banner_id)
    
    if request.method == 'POST':
        banner_title = banner.title
        banner.delete()
        messages.success(request, f'Banner "{banner_title}" deleted successfully.')
        return redirect('admin_panel:banner_list')
    
    return render(request, 'admin_panel/banner_confirm_delete.html', {'banner': banner})

@staff_member_required
def user_list(request):
    """User list view"""
    users = User.objects.filter(is_staff=False).order_by('-date_joined')
    
    # Filter by registration date
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        from datetime import datetime
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        users = users.filter(date_joined__date__gte=date_from)
    if date_to:
        from datetime import datetime
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        users = users.filter(date_joined__date__lte=date_to)
    
    # Search by name, email, or phone
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    context = {
        'users': users,
        'search_query': search_query,
    }
    return render(request, 'admin_panel/user_list.html', context)

@staff_member_required
def user_detail(request, user_id):
    """User detail view"""
    user = get_object_or_404(User, id=user_id, is_staff=False)
    
    # Get user's orders
    orders = Order.objects.filter(user=user).order_by('-created_at')
    
    # Calculate user statistics
    total_orders = orders.count()
    total_spent = orders.filter(payment_status='completed').aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')
    
    context = {
        'customer': user,
        'orders': orders,
        'total_orders': total_orders,
        'total_spent': total_spent,
    }
    return render(request, 'admin_panel/user_detail.html', context)
