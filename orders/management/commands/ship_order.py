"""
Management command to mark an order as shipped and trigger OTP email.
Usage: python manage.py ship_order <order_id_or_pk>
Example: python manage.py ship_order 18
         python manage.py ship_order ORD-0F66B92E
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Mark an order as shipped and send OTP email to customer'

    def add_arguments(self, parser):
        parser.add_argument('order_ref', type=str,
                            help='Order PK (integer) or order_id string')

    def handle(self, *args, **options):
        from orders.models import Order
        from orders.tasks import send_delivery_otp_sms

        ref = options['order_ref']
        try:
            if ref.isdigit():
                order = Order.objects.get(pk=int(ref))
            else:
                order = Order.objects.get(order_id=ref)
        except Order.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Order "{ref}" not found.'))
            return

        if order.status == 'delivered':
            self.stderr.write(self.style.WARNING(f'Order {order.order_id} is already delivered.'))
            return

        old_status = order.status
        order.status = 'shipped'
        order.estimated_delivery_date = (timezone.now() + timezone.timedelta(days=3)).date()
        order.save(update_fields=['status', 'estimated_delivery_date'])

        self.stdout.write(f'Order {order.order_id}: {old_status} → shipped')
        self.stdout.write(f'Estimated delivery: {order.estimated_delivery_date}')
        self.stdout.write('Sending OTP via SMS...')

        try:
            result = send_delivery_otp_sms(order.id)
            self.stdout.write(self.style.SUCCESS(f'SMS: {result}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'SMS failed: {e}'))

        # Print OTP to console for easy testing
        order.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Done! OTP for testing: {order.delivery_otp}'
            f'\n  Track URL: http://localhost:8000/orders/track-order/{order.id}/'
            f'\n  Confirm delivery: http://localhost:8000/orders/confirm-delivery/{order.id}/'
        ))
