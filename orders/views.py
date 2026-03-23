from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from users.models import Address
from users.forms import AddressForm
from cart.views import get_or_create_cart
from cart.services import PriceCalculator
from .models import Order, OrderItem
from .tasks import (
    send_order_confirmation_email, send_order_confirmation_sms,
    send_order_status_update_email, send_order_status_update_sms,
    send_delivery_otp_email, send_delivery_otp_sms, send_shipped_sms,
)

def _fire(task, *args):
    """Call a Celery task if broker is available, otherwise run in a background thread."""
    import threading
    try:
        task.delay(*args)
    except Exception:
        def _run():
            try:
                task(*args)
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()
from products.inventory_service import InventoryService
from decimal import Decimal


def create_order_from_cart(user, cart, address, payment_method, subtotal, tax, shipping_charge, total, payment_status='pending', wallet_amount=0):
    """Helper function to create an order from cart"""
    import random
    from django.utils import timezone

    # Format address as text
    address_text = f"{address.full_name}\n{address.address_line1}\n"
    if address.address_line2:
        address_text += f"{address.address_line2}\n"
    address_text += f"{address.city}, {address.state} {address.postal_code}\n"
    address_text += f"Phone: {address.phone_number}"

    # Pre-generate delivery OTP
    delivery_otp = str(random.randint(100000, 999999))

    # Create order
    order = Order.objects.create(
        user=user,
        shipping_address=address_text,
        payment_method=payment_method,
        payment_status=payment_status,
        subtotal=subtotal,
        tax=tax,
        shipping_charge=shipping_charge,
        total_amount=total,
        status='pending',
        delivery_otp=delivery_otp,
        otp_sent_at=timezone.now(),
        estimated_delivery_date=(timezone.now() + timezone.timedelta(days=3)).date(),
        wallet_amount_used=Decimal(str(wallet_amount)),
    )
    
    # Create order items from cart items
    order_items = []
    for cart_item in cart.items.all():
        order_item = OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            size=cart_item.size,
            quantity=cart_item.quantity,
            price_at_purchase=cart_item.product.price
        )
        order_items.append(order_item)
    
    # Process inventory decrease
    success, error_msg = InventoryService.process_order_inventory(order_items)
    if not success:
        # If inventory processing fails, delete the order and raise exception
        order.delete()
        raise ValueError(f"Inventory error: {error_msg}")
    
    return order

@login_required
def checkout(request):
    """Checkout view - address selection step"""
    # Get user's cart
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product').all()
    
    # Check if cart is empty
    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart:cart_detail')
    
    # Get price breakdown using PriceCalculator
    coupon_discount = Decimal(str(request.session.get('coupon_discount', 0)))
    calculator = PriceCalculator(cart, coupon_discount=coupon_discount)
    price_breakdown = calculator.get_price_breakdown()
    
    # Get user's saved addresses
    addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')
    
    # Handle address selection
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'select_address':
            address_id = request.POST.get('address_id')
            if address_id:
                # Store selected address in session
                request.session['selected_address_id'] = int(address_id)
                return redirect('orders:order_summary')
            else:
                messages.error(request, 'Please select a shipping address.')
        
        elif action == 'add_address':
            # Handle new address form submission
            form = AddressForm(request.POST)
            if form.is_valid():
                address = form.save(commit=False)
                address.user = request.user
                
                # If this is set as default, unset other defaults
                if address.is_default:
                    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
                
                address.save()
                messages.success(request, 'Address added successfully.')
                
                # Auto-select the newly added address
                request.session['selected_address_id'] = address.id
                return redirect('orders:order_summary')
            else:
                # Re-render with form errors
                context = {
                    'addresses': addresses,
                    'address_form': form,
                    'show_add_form': True,
                    'cart': cart,
                    'cart_items': cart_items,
                    'subtotal': price_breakdown['subtotal'],
                    'tax': price_breakdown['tax'],
                    'shipping': price_breakdown['shipping'],
                    'discount': price_breakdown['discount'],
                    'total': price_breakdown['total'],
                    'coupon_code': request.session.get('coupon_code'),
                }
                return render(request, 'orders/checkout.html', context)
    
    # GET request - show address selection
    address_form = AddressForm()
    show_add_form = request.GET.get('add_new') == 'true'
    
    context = {
        'addresses': addresses,
        'address_form': address_form,
        'show_add_form': show_add_form,
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': price_breakdown['subtotal'],
        'tax': price_breakdown['tax'],
        'shipping': price_breakdown['shipping'],
        'discount': price_breakdown['discount'],
        'total': price_breakdown['total'],
        'coupon_code': request.session.get('coupon_code'),
    }
    return render(request, 'orders/checkout.html', context)

@login_required
def payment_method_selection(request):
    """Payment method selection view"""
    # Get selected address from session
    address_id = request.session.get('selected_address_id')
    if not address_id:
        messages.warning(request, 'Please select a shipping address.')
        return redirect('orders:checkout')
    
    # Get address
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    # Get cart items
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product').all()
    
    # Check if cart is empty
    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart:cart_detail')
    
    # Calculate price breakdown using PriceCalculator
    coupon_discount = Decimal(str(request.session.get('coupon_discount', 0)))
    calculator = PriceCalculator(cart, coupon_discount=coupon_discount, shipping_address=address)
    price_breakdown = calculator.get_price_breakdown()

    # Build context up front so it's available in both GET and POST error paths
    from wallet.services import get_or_create_wallet
    wallet = get_or_create_wallet(request.user)
    context = {
        'address': address,
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': price_breakdown['subtotal'],
        'tax': price_breakdown['tax'],
        'shipping_charge': price_breakdown['shipping'],
        'discount': price_breakdown['discount'],
        'total': price_breakdown['total'],
        'suppress_global_messages': True,
        'wallet_balance': wallet.balance,
    }

    # Handle payment method selection
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        if payment_method not in ['cod', 'upi', 'card']:
            messages.error(request, 'Please select a valid payment method.')
        else:
            # Handle COD payment
            if payment_method == 'cod':
                try:
                    # Pre-validate inventory before creating order
                    inventory_errors = []
                    for cart_item in cart_items:
                        from products.inventory_service import InventoryService
                        is_available, available_qty = InventoryService.check_availability(
                            cart_item.product, cart_item.size, cart_item.quantity
                        )
                        if not is_available:
                            inventory_errors.append(
                                f"{cart_item.product.name} (Size: {cart_item.size}) — "
                                f"only {available_qty} in stock, you have {cart_item.quantity} in cart"
                            )
                    if inventory_errors:
                        context['inventory_errors'] = inventory_errors
                        return render(request, 'orders/payment_method.html', context)

                    # Create order immediately for COD
                    order = create_order_from_cart(
                        user=request.user,
                        cart=cart,
                        address=address,
                        payment_method='cod',
                        subtotal=price_breakdown['subtotal'],
                        tax=price_breakdown['tax'],
                        shipping_charge=price_breakdown['shipping'],
                        total=price_breakdown['total']
                    )

                    # Send order confirmation notifications asynchronously
                    _fire(send_order_confirmation_email, order.id)
                    _fire(send_order_confirmation_sms, order.id)

                    # Auto-advance to out_for_delivery after ~60s (fast delivery test)
                    from orders.tasks import auto_advance_order_to_delivery
                    _fire(auto_advance_order_to_delivery, order.id)

                    # Clear cart after order creation
                    cart.items.all().delete()

                    # Clear session data
                    if 'selected_address_id' in request.session:
                        del request.session['selected_address_id']

                    # Redirect to order confirmation
                    return redirect('orders:order_confirmation', order_id=order.id)

                except ValueError as e:
                    context['inventory_errors'] = [str(e)]
                    return render(request, 'orders/payment_method.html', context)
            
            # Handle online payment (UPI/Card) — process directly
            else:
                try:
                    # Pre-validate inventory
                    inventory_errors = []
                    for cart_item in cart_items:
                        from products.inventory_service import InventoryService
                        is_available, available_qty = InventoryService.check_availability(
                            cart_item.product, cart_item.size, cart_item.quantity
                        )
                        if not is_available:
                            inventory_errors.append(
                                f"{cart_item.product.name} (Size: {cart_item.size}) — "
                                f"only {available_qty} in stock"
                            )
                    if inventory_errors:
                        context['inventory_errors'] = inventory_errors
                        return render(request, 'orders/payment_method.html', context)

                    # Wallet split payment
                    wallet_deduction = Decimal(str(request.session.get('wallet_deduction', 0)))
                    # Also check POST field (set by JS)
                    post_deduction = Decimal(str(request.POST.get('wallet_deduction', 0) or 0))
                    if post_deduction > 0:
                        wallet_deduction = post_deduction
                    from wallet.services import get_or_create_wallet, debit_wallet_for_order
                    wallet = get_or_create_wallet(request.user)
                    wallet_deduction = min(wallet_deduction, wallet.balance, price_breakdown['total'])

                    order = create_order_from_cart(
                        user=request.user,
                        cart=cart,
                        address=address,
                        payment_method=payment_method,
                        subtotal=price_breakdown['subtotal'],
                        tax=price_breakdown['tax'],
                        shipping_charge=price_breakdown['shipping'],
                        total=price_breakdown['total'],
                        payment_status='completed',
                        wallet_amount=wallet_deduction,
                    )

                    # Debit wallet if used
                    if wallet_deduction > 0:
                        debit_wallet_for_order(request.user, wallet_deduction, order)

                    _fire(send_order_confirmation_email, order.id)
                    _fire(send_order_confirmation_sms, order.id)

                    cart.items.all().delete()

                    for key in ('selected_address_id', 'wallet_deduction'):
                        request.session.pop(key, None)

                    return redirect('orders:order_confirmation', order_id=order.id)

                except ValueError as e:
                    context['inventory_errors'] = [str(e)]
                    return render(request, 'orders/payment_method.html', context)

    return render(request, 'orders/payment_method.html', context)

@login_required
def order_summary(request):
    """Order summary view - review before payment"""
    # Get selected address from session
    address_id = request.session.get('selected_address_id')
    if not address_id:
        messages.warning(request, 'Please select a shipping address.')
        return redirect('orders:checkout')
    
    # Get address
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    # Get cart items
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product').all()
    
    # Check if cart is empty
    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart:cart_detail')
    
    # Calculate price breakdown using PriceCalculator
    coupon_discount = Decimal(str(request.session.get('coupon_discount', 0)))
    calculator = PriceCalculator(cart, coupon_discount=coupon_discount, shipping_address=address)
    price_breakdown = calculator.get_price_breakdown()
    
    # Pre-check inventory so user sees errors before reaching payment
    inventory_errors = []
    for cart_item in cart_items:
        from products.inventory_service import InventoryService
        is_available, available_qty = InventoryService.check_availability(
            cart_item.product, cart_item.size, cart_item.quantity
        )
        if not is_available:
            inventory_errors.append(
                f"{cart_item.product.name} (Size: {cart_item.size}) — "
                f"only {available_qty} in stock, you have {cart_item.quantity} in cart"
            )

    context = {
        'address': address,
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': price_breakdown['subtotal'],
        'tax': price_breakdown['tax'],
        'shipping_charge': price_breakdown['shipping'],
        'discount': price_breakdown['discount'],
        'total': price_breakdown['total'],
        'inventory_errors': inventory_errors,
    }
    return render(request, 'orders/order_summary.html', context)

@login_required
def order_history(request):
    """Order history view"""
    # Get all orders for the user
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product').order_by('-created_at')
    
    # Categorize orders as Active or Past
    active_statuses = ['pending', 'processing', 'shipped', 'out_for_delivery']
    active_orders = orders.filter(status__in=active_statuses)
    past_orders = orders.exclude(status__in=active_statuses)
    
    context = {
        'active_orders': active_orders,
        'past_orders': past_orders,
        'all_orders': orders,
    }
    return render(request, 'orders/order_history.html', context)

@login_required
def order_detail(request, order_id):
    """Order detail view"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.select_related('product').all()
    
    # Check if order is eligible for return/exchange (within 7 days of delivery)
    can_return = False
    if order.status == 'delivered' and order.delivered_at:
        from datetime import timedelta
        from django.utils import timezone
        days_since_delivery = (timezone.now() - order.delivered_at).days
        can_return = days_since_delivery <= 7
    
    context = {
        'order': order,
        'order_items': order_items,
        'can_return': can_return,
    }
    return render(request, 'orders/order_detail.html', context)

def track_order(request, order_id):
    """Order tracking view — public via email link, login required for other users' orders."""
    if request.user.is_authenticated:
        order = get_object_or_404(Order, id=order_id, user=request.user)
    else:
        # Allow unauthenticated access via direct link (e.g. from email)
        order = get_object_or_404(Order, id=order_id)

    # Define status progression
    status_steps = [
        {'key': 'pending',           'label': 'Order Placed'},
        {'key': 'processing',        'label': 'Processing'},
        {'key': 'shipped',           'label': 'Shipped'},
        {'key': 'out_for_delivery',  'label': 'Out for Delivery'},
        {'key': 'delivered',         'label': 'Delivered'},
    ]

    # Mark completed / current steps
    status_order = ['pending', 'processing', 'shipped', 'out_for_delivery', 'delivered']
    progress_pct = 0
    pct_map = {'pending': 10, 'processing': 30, 'shipped': 55, 'out_for_delivery': 80, 'delivered': 100}
    try:
        current_index = status_order.index(order.status)
        progress_pct  = pct_map.get(order.status, 0)
        for i, step in enumerate(status_steps):
            step['completed'] = i <= current_index
            step['current']   = i == current_index
    except ValueError:
        for step in status_steps:
            step['completed'] = False
            step['current']   = False

    context = {
        'order':        order,
        'status_steps': status_steps,
        'progress_pct': progress_pct,
    }
    return render(request, 'orders/track_order.html', context)

@login_required
def request_return(request, order_id):
    """Request return view"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if order is eligible for return
    if order.status != 'delivered' or not order.delivered_at:
        messages.error(request, 'This order is not eligible for return.')
        return redirect('orders:order_detail', order_id=order_id)
    
    from datetime import timedelta
    from django.utils import timezone
    days_since_delivery = (timezone.now() - order.delivered_at).days
    
    if days_since_delivery > 7:
        messages.error(request, 'Return period has expired. Returns are only allowed within 7 days of delivery.')
        return redirect('orders:order_detail', order_id=order_id)
    
    # Check if return request already exists
    from orders.models import ReturnRequest
    existing_return = ReturnRequest.objects.filter(order=order).first()
    if existing_return:
        messages.info(request, f'A return request already exists for this order. Status: {existing_return.get_status_display()}')
        return redirect('orders:order_detail', order_id=order_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            messages.error(request, 'Please provide a reason for the return.')
        else:
            # Create return request
            return_request = ReturnRequest.objects.create(
                order=order,
                reason=reason,
                status='pending'
            )
            
            messages.success(request, 'Return request submitted successfully. We will review it shortly.')
            
            # TODO: Send notification to admin
            
            return redirect('orders:order_detail', order_id=order_id)
    
    context = {
        'order': order,
        'days_remaining': 7 - days_since_delivery,
    }
    return render(request, 'orders/request_return.html', context)

@login_required
def request_exchange(request, order_id):
    """Request exchange view"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if order is eligible for exchange
    if order.status != 'delivered' or not order.delivered_at:
        messages.error(request, 'This order is not eligible for exchange.')
        return redirect('orders:order_detail', order_id=order_id)
    
    from datetime import timedelta
    from django.utils import timezone
    days_since_delivery = (timezone.now() - order.delivered_at).days
    
    if days_since_delivery > 7:
        messages.error(request, 'Exchange period has expired. Exchanges are only allowed within 7 days of delivery.')
        return redirect('orders:order_detail', order_id=order_id)
    
    # Check if exchange request already exists
    from orders.models import ExchangeRequest
    existing_exchange = ExchangeRequest.objects.filter(order=order).first()
    if existing_exchange:
        messages.info(request, f'An exchange request already exists for this order. Status: {existing_exchange.get_status_display()}')
        return redirect('orders:order_detail', order_id=order_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            messages.error(request, 'Please provide a reason for the exchange.')
        else:
            # Create exchange request
            exchange_request = ExchangeRequest.objects.create(
                order=order,
                reason=reason,
                status='pending'
            )
            
            messages.success(request, 'Exchange request submitted successfully. We will review it shortly.')
            
            # TODO: Send notification to admin
            
            return redirect('orders:order_detail', order_id=order_id)
    
    context = {
        'order': order,
        'days_remaining': 7 - days_since_delivery,
    }
    return render(request, 'orders/request_exchange.html', context)

@login_required
def download_invoice(request, order_id):
    """Download invoice view"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Only allow invoice download for delivered orders
    if order.status != 'delivered':
        messages.error(request, 'Invoice is only available for delivered orders.')
        return redirect('orders:order_detail', order_id=order_id)
    
    # Generate PDF invoice
    from django.template.loader import render_to_string
    from django.http import HttpResponse
    try:
        from weasyprint import HTML
        import tempfile
        
        # Render HTML template
        order_items = order.items.select_related('product').all()
        html_string = render_to_string('orders/invoice_template.html', {
            'order': order,
            'order_items': order_items,
        })
        
        # Generate PDF
        html = HTML(string=html_string)
        result = html.write_pdf()
        
        # Create response
        response = HttpResponse(result, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.pdf"'
        
        return response
        
    except ImportError:
        # WeasyPrint not installed, return simple text invoice
        order_items = order.items.select_related('product').all()
        
        invoice_text = f"""
INVOICE
=======

Order ID: {order.order_id}
Order Date: {order.created_at.strftime('%B %d, %Y')}
Delivery Date: {order.delivered_at.strftime('%B %d, %Y') if order.delivered_at else 'N/A'}

Customer: {order.user.get_full_name() or order.user.username}
Shipping Address:
{order.shipping_address}

Items:
------
"""
        for item in order_items:
            invoice_text += f"{item.product.name} (Size: {item.size}) x {item.quantity} - ₹{item.price_at_purchase * item.quantity}\n"
        
        invoice_text += f"""
------
Subtotal: ₹{order.subtotal}
Tax: ₹{order.tax}
Shipping: ₹{order.shipping_charge}
Discount: ₹{order.discount}
------
Total: ₹{order.total_amount}

Payment Method: {order.get_payment_method_display()}
Payment Status: {order.get_payment_status_display()}

Thank you for shopping with FabVibe!
"""
        
        response = HttpResponse(invoice_text, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.txt"'
        
        return response


@login_required
def order_confirmation(request, order_id):
    """Order confirmation page"""
    # Get order
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Get order items
    order_items = order.items.select_related('product').all()
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'orders/order_confirmation.html', context)


@login_required
def cancel_order(request, order_id):
    """Cancel a pending/processing order and refund to wallet."""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status not in ('pending', 'processing'):
        messages.error(request, 'Only pending or processing orders can be cancelled.')
        return redirect('orders:order_detail', order_id=order_id)

    if request.method == 'POST':
        from django.utils import timezone
        order.status = 'cancelled'
        order.save(update_fields=['status', 'updated_at'])

        # Refund to wallet if payment was completed
        if order.payment_status == 'completed':
            try:
                from wallet.services import refund_to_wallet
                refund_to_wallet(order, reason="Cancellation refund")
                messages.success(request, f'Order cancelled. ₹{order.total_amount} refunded to your wallet.')
            except Exception:
                messages.success(request, 'Order cancelled successfully.')
        else:
            messages.success(request, 'Order cancelled successfully.')

        return redirect('orders:order_detail', order_id=order_id)

    return render(request, 'orders/cancel_order.html', {'order': order})


def confirm_delivery(request, order_id):
    """
    Delivery agent OTP confirmation view.
    Accessible without login (delivery agent uses it on-site).
    """
    order = get_object_or_404(Order, id=order_id)

    if order.otp_verified:
        return render(request, 'orders/confirm_delivery.html', {
            'order': order,
            'already_verified': True,
        })

    error = None
    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        if entered_otp == order.delivery_otp and order.delivery_otp:
            from django.utils import timezone
            order.otp_verified = True
            order.status = 'delivered'
            order.delivered_at = timezone.now()
            order.save(update_fields=['otp_verified', 'status', 'delivered_at'])

            # Award cashback to wallet
            try:
                from wallet.services import award_cashback
                award_cashback(order)
            except Exception:
                pass

            # Send delivered SMS/email
            _fire(send_order_status_update_email, order.id)
            _fire(send_order_status_update_sms, order.id)

            messages.success(request, f'🎉 Order {order.order_id} delivered successfully! Thank you for shopping with FabVibe.')
            return redirect('orders:track_order', order_id=order.id)
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            return redirect('orders:track_order', order_id=order.id)


@login_required
def send_delivery_otp_view(request, order_id):
    """
    Manually resend the delivery OTP for an order.
    Generates a fresh OTP, saves it to the order and the session,
    then sends it via Brevo.

    POST  /orders/send-otp/<order_id>/
    Returns JSON: {success, message}
    """
    from django.http import JsonResponse
    from django.utils import timezone
    from utils import generate_otp, send_otp_email

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required.'}, status=405)

    # Generate fresh OTP
    otp = generate_otp()
    order.delivery_otp = otp
    order.otp_sent_at = timezone.now()
    order.save(update_fields=['delivery_otp', 'otp_sent_at'])

    # Also store in session as a quick reference
    request.session[f'delivery_otp_{order.order_id}'] = otp

    user_name = request.user.get_full_name() or request.user.email
    ok = send_otp_email(
        to_email=request.user.email,
        to_name=user_name,
        otp=otp,
    )

    if ok:
        return JsonResponse({'success': True, 'message': f'OTP sent to {request.user.email}.'})
    return JsonResponse({'success': False, 'message': 'Could not send OTP. Please try again.'}, status=500)


def deliver_order(request):
    """
    Delivery executive portal — no login required.
    Executive enters Order ID + customer OTP.
    On match: order → delivered, cashback awarded, customer notified.
    URL: /orders/deliver/
    """
    from django.utils import timezone

    result  = None   # 'success' | 'error' | 'already'
    order   = None
    error   = None

    if request.method == 'POST':
        raw_id  = request.POST.get('order_id', '').strip().upper()
        entered = request.POST.get('otp', '').strip()

        # Look up by order_id string (e.g. "ORD-ABCD1234")
        try:
            order = Order.objects.select_related('user').get(order_id=raw_id)
        except Order.DoesNotExist:
            error = f'Order "{raw_id}" not found. Please check the Order ID and try again.'
            return render(request, 'orders/deliver_order.html', {'error': error})

        if order.otp_verified or order.status == 'delivered':
            result = 'already'
        elif not order.delivery_otp:
            error = 'No OTP has been generated for this order yet.'
        elif entered != order.delivery_otp:
            error = 'Incorrect OTP. Please ask the customer to check their email and try again.'
        else:
            # ✅ OTP matches — mark delivered
            order.otp_verified = True
            order.status       = 'delivered'
            order.delivered_at = timezone.now()
            order.save(update_fields=['otp_verified', 'status', 'delivered_at', 'updated_at'])

            # Award cashback
            try:
                from wallet.services import award_cashback
                award_cashback(order)
            except Exception:
                pass

            # Notify customer
            _fire(send_order_status_update_email, order.id)
            _fire(send_order_status_update_sms,   order.id)

            result = 'success'

    return render(request, 'orders/deliver_order.html', {
        'result': result,
        'order':  order,
        'error':  error,
    })
