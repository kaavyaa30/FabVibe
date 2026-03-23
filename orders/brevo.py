"""
orders/brevo.py — thin re-export for backwards compatibility.

All email logic lives in utils.send_brevo_email.
Existing imports like `from orders.brevo import send_brevo_email` keep working.
"""
from utils import send_brevo_email  # noqa: F401
