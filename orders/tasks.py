from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def send_sms(phone_number, message):
    """
    Send message using configured backend.
    Supported: 'whatsapp', 'fast2sms', 'twilio', 'console'
    """
    backend = getattr(settings, 'SMS_BACKEND', 'console')

    # ── WhatsApp via Meta Cloud API (free 1000 msgs/month) ──────────────────
    if backend == 'whatsapp':
        try:
            import requests as req
            # Normalize to E.164 — strip spaces/dashes, ensure +91 prefix for India
            number = str(phone_number).strip().replace(' ', '').replace('-', '')
            if not number.startswith('+'):
                number = '+91' + number.lstrip('0')

            url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
            headers = {
                'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
                'Content-Type': 'application/json',
            }
            payload = {
                'messaging_product': 'whatsapp',
                'to': number,
                'type': 'text',
                'text': {'body': message},
            }
            resp = req.post(url, headers=headers, json=payload, timeout=10)
            result = resp.json()
            if resp.status_code == 200 and result.get('messages'):
                print(f"WhatsApp sent to {number}: {result['messages'][0]['id']}")
                return True
            else:
                print(f"WhatsApp error: {result}")
                return False
        except Exception as e:
            print(f"WhatsApp failed: {e}")
            return False

    # ── Fast2SMS (Indian numbers) ────────────────────────────────────────────
    elif backend == 'fast2sms':
        try:
            import requests as req
            number = str(phone_number).strip().lstrip('+').lstrip('91')[-10:]
            resp = req.post(
                'https://www.fast2sms.com/dev/bulkV2',
                headers={'authorization': settings.FAST2SMS_API_KEY},
                data={'route': 'q', 'message': message, 'language': 'english',
                      'flash': 0, 'numbers': number},
                timeout=10,
            )
            result = resp.json()
            if result.get('return'):
                return True
            print(f"Fast2SMS error: {result}")
            return False
        except Exception as e:
            print(f"Fast2SMS failed: {e}")
            return False

    # ── Twilio ───────────────────────────────────────────────────────────────
    elif backend == 'twilio':
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(body=message, from_=settings.TWILIO_PHONE_NUMBER, to=phone_number)
            return True
        except Exception as e:
            print(f"Twilio SMS failed: {e}")
            return False

    # ── Console (development) ────────────────────────────────────────────────
    else:
        print(f"[WhatsApp/SMS → {phone_number}]\n{message}\n")
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
def send_delivery_otp_email(order_id):
    """
    Send delivery OTP via Brevo when order moves to 'out_for_delivery'.
    Generates a fresh 6-digit OTP, saves it to the order, then emails it.
    """
    from orders.models import Order
    from orders.brevo import send_brevo_email
    from django.utils import timezone
    import random

    try:
        order = Order.objects.select_related('user').get(id=order_id)

        # Generate OTP and set 1-day delivery window (out for delivery = today)
        otp = str(random.randint(100000, 999999))
        order.delivery_otp = otp
        order.otp_sent_at = timezone.now()
        order.estimated_delivery_date = timezone.now().date()
        order.save(update_fields=['delivery_otp', 'otp_sent_at', 'estimated_delivery_date'])

        tracking_url = f"http://172.16.2.168:8000/orders/track-order/{order.id}/"
        context = {
            'order': order,
            'user': order.user,
            'otp': otp,
            'tracking_url': tracking_url,
        }
        subject = f'Your Delivery OTP for Order {order.order_id} — FabVibe'
        html_message = render_to_string('orders/emails/delivery_otp.html', context)

        user_name = order.user.get_full_name() or order.user.email
        ok = send_brevo_email(
            to_email=order.user.email,
            to_name=user_name,
            subject=subject,
            html_content=html_message,
        )

        if ok:
            logger.info(f'[OTP email] Sent to {order.user.email} for order {order.order_id}')
        else:
            logger.error(f'[OTP email] Failed for order {order.order_id}')

        return f"Delivery OTP email {'sent' if ok else 'FAILED'} for {order.user.email}"

    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        logger.exception(f'[OTP email] Unexpected error for order {order_id}')
        return f"Delivery OTP email failed: {str(e)}"


@shared_task
def send_delivery_otp_sms(order_id):
    """
    Send delivery OTP + tracking link via SMS when order is dispatched.
    Generates OTP if not already set.
    """
    from orders.models import Order
    from django.utils import timezone
    import random

    try:
        order = Order.objects.select_related('user').get(id=order_id)

        # Generate OTP if not already done
        if not order.delivery_otp:
            otp = str(random.randint(100000, 999999))
            order.delivery_otp = otp
            order.otp_sent_at = timezone.now()
            if not order.estimated_delivery_date:
                order.estimated_delivery_date = (timezone.now() + timezone.timedelta(days=3)).date()
            order.save(update_fields=['delivery_otp', 'otp_sent_at', 'estimated_delivery_date'])

        tracking_url = f"http://172.16.2.168:8000/orders/track-order/{order.id}/"
        message = (
            f"FabVibe: Your order {order.order_id} has been dispatched!\n"
            f"Delivery OTP: {order.delivery_otp}\n"
            f"Share this OTP with the delivery agent on arrival.\n"
            f"Track your order: {tracking_url}"
        )

        phone_number = getattr(order.user, 'phone_number', None)
        if phone_number:
            send_sms(phone_number, message)
            return f"OTP + tracking SMS sent to {phone_number}"
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


@shared_task
def auto_advance_order_to_delivery(order_id):
    """
    Fast-delivery test task.
    Called right after COD order creation — waits ~90 s then moves the order
    through: pending → processing → out_for_delivery.
    The out_for_delivery transition fires the signal which generates the OTP
    and sends the Brevo email automatically.
    """
    import time
    from orders.models import Order

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return f"Order {order_id} not found"

    # Only advance if still in initial state
    if order.status not in ('pending', 'processing'):
        return f"Order {order_id} already at {order.status}, skipping auto-advance"

    # pending → processing (immediate)
    if order.status == 'pending':
        order.status = 'processing'
        order.save(update_fields=['status', 'updated_at'])
        logger.info(f"[auto-advance] Order {order.order_id} → processing")

    # Wait 60 seconds
    time.sleep(60)

    # Reload in case it was cancelled/updated externally
    order.refresh_from_db()
    if order.status != 'processing':
        return f"Order {order_id} status changed externally to {order.status}, stopping"

    # processing → out_for_delivery
    # This triggers the pre_save signal in orders/signals.py which:
    #   1. Generates the delivery OTP
    #   2. Queues send_delivery_otp_email + send_delivery_otp_sms
    order.status = 'out_for_delivery'
    order.save()
    logger.info(f"[auto-advance] Order {order.order_id} → out_for_delivery (OTP email queued by signal)")

    return f"Order {order.order_id} advanced to out_for_delivery"
