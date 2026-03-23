"""
Order signals — auto-send delivery OTP when status → out_for_delivery.

This fires regardless of where the status change happens:
admin panel view, Django admin, management commands, shell, etc.
"""
import logging
from django.db.models.signals import pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(pre_save, sender='orders.Order')
def on_order_status_change(sender, instance, **kwargs):
    """
    When an Order transitions to 'out_for_delivery':
      1. Generate a fresh 6-digit OTP and save it.
      2. Fire send_delivery_otp_email + send_delivery_otp_sms tasks.

    Uses pre_save so we can compare old vs new status.
    The actual DB save happens after this signal returns.
    """
    if not instance.pk:
        return  # new order — nothing to compare

    try:
        old = sender.objects.only('status').get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    if old.status != 'out_for_delivery' and instance.status == 'out_for_delivery':
        # OTP generation and email is handled directly in admin_panel/views.py
        # for admin-triggered changes (synchronous, immediate).
        # This signal only fires for non-admin code paths (e.g. auto_advance_order_to_delivery task).
        # Check if OTP was already set by the caller (admin view sets it before save).
        if instance.delivery_otp:
            logger.info(f'[Signal] Order {instance.order_id} → out_for_delivery. OTP already set by caller, skipping signal email.')
            return

        import random
        from django.utils import timezone

        # Generate OTP inline so it's persisted in the same save() call
        otp = str(random.randint(100000, 999999))
        instance.delivery_otp = otp
        instance.otp_sent_at = timezone.now()
        instance.estimated_delivery_date = timezone.now().date()

        logger.info(
            f'[Signal] Order {instance.order_id} → out_for_delivery. '
            f'OTP generated, queuing email/SMS.'
        )

        # Fire tasks after the current transaction commits so the OTP is readable
        from django.db import transaction

        def _fire_notifications():
            from orders.tasks import send_delivery_otp_email, send_delivery_otp_sms
            try:
                send_delivery_otp_email.delay(instance.pk)
            except Exception as e:
                logger.warning(f'[Signal] Could not queue OTP email: {e}')
                import threading
                threading.Thread(
                    target=send_delivery_otp_email,
                    args=(instance.pk,),
                    daemon=True,
                ).start()

            try:
                send_delivery_otp_sms.delay(instance.pk)
            except Exception as e:
                logger.warning(f'[Signal] Could not queue OTP SMS: {e}')

        transaction.on_commit(_fire_notifications)
