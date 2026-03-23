"""
FabVibe — shared email utility.

Core function:
    send_brevo_email(subject, to_email, html_content)
        Reusable for any transactional email — OTPs, order tracking, etc.

Higher-level helpers (build html_content then call send_brevo_email):
    send_otp_email(to_email, to_name, otp)
    send_order_tracking_email(order)
    generate_otp()
"""
import random
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


# ── Core reusable function ────────────────────────────────────────────────────

def send_brevo_email(subject: str, to_email: str, html_content: str,
                     to_name: str = '') -> bool:
    """
    Send a transactional HTML email via the Brevo (Sendinblue) API.

    Args:
        subject:      Email subject line.
        to_email:     Recipient email address.
        html_content: Full HTML body of the email.
        to_name:      Optional recipient display name.

    Returns:
        True on success, False on any failure (errors are logged, never raised).

    Falls back to Django SMTP if BREVO_API_KEY is not configured.

    Usage:
        from utils import send_brevo_email

        send_brevo_email(
            subject='Your OTP',
            to_email='customer@example.com',
            html_content='<p>Your OTP is <b>123456</b></p>',
        )
    """
    api_key = getattr(settings, 'BREVO_API_KEY', '').strip()

    # ── Fallback: no API key → Django SMTP ───────────────────────────────────
    if not api_key:
        logger.warning('[Brevo] BREVO_API_KEY not set — falling back to Django send_mail.')
        try:
            from django.core.mail import send_mail
            from django.utils.html import strip_tags
            send_mail(
                subject=subject,
                message=strip_tags(html_content),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                html_message=html_content,
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error(f'[Brevo fallback] send_mail failed: {e}')
            return False

    # ── Brevo SDK ─────────────────────────────────────────────────────────────
    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException

        # Configure API key
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = api_key

        api = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        # Resolve sender email — prefer BREVO_SENDER_EMAIL, fall back to DEFAULT_FROM_EMAIL
        sender_raw = (
            getattr(settings, 'BREVO_SENDER_EMAIL', '')
            or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@fabvibe.com')
        )
        # Strip display name if present: "FabVibe <addr@x.com>" → "addr@x.com"
        if '<' in sender_raw:
            sender_raw = sender_raw.split('<')[1].rstrip('>')

        email = sib_api_v3_sdk.SendSmtpEmail(
            sender={'name': 'FabVibe', 'email': sender_raw},
            to=[{'email': to_email, 'name': to_name or to_email}],
            subject=subject,
            html_content=html_content,
        )

        api.send_transac_email(email)
        logger.info(f'[Brevo] Sent "{subject}" → {to_email}')
        return True

    except ApiException as e:
        logger.error(f'[Brevo] API error for {to_email}: {e}')
        return False
    except ImportError:
        logger.error('[Brevo] sib-api-v3-sdk not installed. Run: pip install sib-api-v3-sdk')
        return False
    except Exception as e:
        logger.error(f'[Brevo] Unexpected error: {e}')
        return False


# ── Higher-level helpers ──────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Return a random numeric OTP string of *length* digits."""
    return str(random.randint(10 ** (length - 1), 10 ** length - 1))


def send_otp_email(to_email: str, to_name: str, otp: str) -> bool:
    """
    Send a branded OTP email via Brevo.

    Renders templates/orders/emails/delivery_otp.html and calls send_brevo_email.
    """
    from django.template.loader import render_to_string
    html_content = render_to_string('orders/emails/delivery_otp.html', {
        'otp': otp,
        'user_name': to_name,
    })
    return send_brevo_email(
        subject='Your FabVibe Delivery OTP',
        to_email=to_email,
        html_content=html_content,
        to_name=to_name,
    )


def send_order_tracking_email(order) -> bool:
    """
    Send an order status / tracking email via Brevo.

    Args:
        order: orders.models.Order instance
    """
    from django.template.loader import render_to_string
    tracking_url = f"http://172.16.2.168:8000/orders/track-order/{order.id}/"
    html_content = render_to_string('orders/emails/delivery_otp.html', {
        'order': order,
        'user': order.user,
        'otp': order.delivery_otp,
        'tracking_url': tracking_url,
    })
    user_name = order.user.get_full_name() or order.user.email
    return send_brevo_email(
        subject=f'FabVibe Order {order.order_id} — {order.get_status_display()}',
        to_email=order.user.email,
        html_content=html_content,
        to_name=user_name,
    )
