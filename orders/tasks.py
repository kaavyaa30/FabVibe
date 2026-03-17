from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_sms(phone_number, message):
    """
    Send SMS using configured SMS backend
    """
    if settings.SMS_BACKEND == 'twilio':
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            return True
        except Exception as e:
            print(f"SMS sending failed: {e}")
            return False
    else:
        # Console backend for development
        print(f"SMS to {phone_number}: {message}")
        return True


@shared_task
def send_order_confirmation_email(order_id):
    """
    Send order confirmation email asynchronously
    """
    from orders.models import Order
    
    try:
        order = Order.objects.select_related('user').prefetch_related('items__product').get(id=order_id)
        
        # Prepare email context
        context = {
            'order': order,
            'order_items': order.items.all(),
            'user': order.user,
        }
        
        # Render email template
        subject = f'Order Confirmation - {order.order_id}'
        html_message = render_to_string('orders/emails/order_confirmation.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Email sent successfully to {order.user.email}"
    
    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        return f"Email sending failed: {str(e)}"


@shared_task
def send_order_confirmation_sms(order_id):
    """
    Send order confirmation SMS asynchronously
    """
    from orders.models import Order
    
    try:
        order = Order.objects.select_related('user').get(id=order_id)
        
        # Prepare SMS message
        message = (
            f"FabVibe: Your order {order.order_id} has been placed successfully! "
            f"Total: ₹{order.total_amount}. "
            f"Estimated delivery: 5-7 business days. "
            f"Track your order at fabvibe.com/orders"
        )
        
        # Send SMS
        phone_number = order.user.phone_number
        if phone_number:
            send_sms(phone_number, message)
            return f"SMS sent successfully to {phone_number}"
        else:
            return "No phone number available"
    
    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        return f"SMS sending failed: {str(e)}"


@shared_task
def send_order_status_update_email(order_id):
    """
    Send order status update email asynchronously
    """
    from orders.models import Order
    
    try:
        order = Order.objects.select_related('user').get(id=order_id)
        
        # Prepare email context
        context = {
            'order': order,
            'user': order.user,
        }
        
        # Render email template
        subject = f'Order Status Update - {order.order_id}'
        html_message = render_to_string('orders/emails/order_status_update.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f"Status update email sent to {order.user.email}"
    
    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        return f"Email sending failed: {str(e)}"


@shared_task
def send_order_status_update_sms(order_id):
    """
    Send order status update SMS asynchronously
    """
    from orders.models import Order
    
    try:
        order = Order.objects.select_related('user').get(id=order_id)
        
        # Prepare SMS message based on status
        status_messages = {
            'processing': f"FabVibe: Your order {order.order_id} is being processed.",
            'shipped': f"FabVibe: Your order {order.order_id} has been shipped! Track: {order.tracking_number}",
            'out_for_delivery': f"FabVibe: Your order {order.order_id} is out for delivery today!",
            'delivered': f"FabVibe: Your order {order.order_id} has been delivered. Thank you for shopping with us!",
            'cancelled': f"FabVibe: Your order {order.order_id} has been cancelled.",
        }
        
        message = status_messages.get(order.status, f"FabVibe: Order {order.order_id} status updated to {order.get_status_display()}")
        
        # Send SMS
        phone_number = order.user.phone_number
        if phone_number:
            send_sms(phone_number, message)
            return f"Status update SMS sent to {phone_number}"
        else:
            return "No phone number available"
    
    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        return f"SMS sending failed: {str(e)}"


@shared_task
def send_delivery_otp_sms(order_id):
    """
    Generate OTP and send SMS when order is out for delivery
    """
    from orders.models import Order
    from django.utils import timezone
    import random

    try:
        order = Order.objects.select_related('user').get(id=order_id)

        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        order.delivery_otp = otp
        order.otp_sent_at = timezone.now()
        order.save(update_fields=['delivery_otp', 'otp_sent_at'])

        message = (
            f"FabVibe: Your order {order.order_id} is out for delivery! "
            f"Your delivery OTP is {otp}. "
            f"Share this with the delivery agent to confirm receipt."
        )

        phone_number = order.user.phone_number
        if phone_number:
            send_sms(phone_number, message)
            return f"OTP SMS sent to {phone_number}"
        else:
            return "No phone number available"

    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        return f"OTP SMS failed: {str(e)}"


@shared_task
def send_shipped_sms(order_id):
    """
    Send SMS with tracking link when order is shipped
    """
    from orders.models import Order

    try:
        order = Order.objects.select_related('user').get(id=order_id)

        tracking_info = f" Tracking: {order.tracking_number}." if order.tracking_number else ""
        est_delivery = ""
        if order.estimated_delivery_date:
            from django.utils import timezone
            days_left = (order.estimated_delivery_date - timezone.now().date()).days
            if days_left > 0:
                est_delivery = f" Expected delivery in {days_left} day(s)."

        message = (
            f"FabVibe: Your order {order.order_id} has been shipped!{tracking_info}{est_delivery} "
            f"Track at: fabvibe.com/orders/track-order/{order.id}/"
        )

        phone_number = order.user.phone_number
        if phone_number:
            send_sms(phone_number, message)
            return f"Shipped SMS sent to {phone_number}"
        else:
            return "No phone number available"

    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        return f"Shipped SMS failed: {str(e)}"
