import random
import logging
from django.contrib import admin
from django.utils import timezone
from .models import Order, OrderItem, ReturnRequest, ExchangeRequest

logger = logging.getLogger(__name__)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ['product', 'size', 'quantity', 'price_at_purchase']
    autocomplete_fields = ['product']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'user', 'status', 'payment_status', 'total_amount', 'created_at']
    list_filter = ['status', 'payment_status', 'payment_method', 'created_at']
    search_fields = ['order_id', 'user__email']
    readonly_fields = ['order_id', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'user', 'status', 'payment_method', 'payment_status')
        }),
        ('Shipping', {
            'fields': ('shipping_address', 'tracking_number', 'estimated_delivery_date', 'delivered_at')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'tax', 'shipping_charge', 'discount', 'total_amount', 'coupon_code', 'wallet_amount_used')
        }),
        ('Delivery Verification', {
            'fields': ('delivery_otp', 'otp_verified', 'otp_sent_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        """Override to send delivery OTP email when status → out_for_delivery."""
        is_out_for_delivery = (
            change  # existing order, not a new one
            and 'status' in form.changed_data
            and obj.status == 'out_for_delivery'
        )

        if is_out_for_delivery:
            # Generate and attach OTP before saving
            otp = str(random.randint(100000, 999999))
            obj.delivery_otp = otp
            obj.otp_sent_at = timezone.now()
            obj.estimated_delivery_date = timezone.now().date()

        super().save_model(request, obj, form, change)

        if is_out_for_delivery:
            self._send_otp_email(request, obj)

    def _send_otp_email(self, request, order):
        try:
            from utils import send_brevo_email
            from django.template.loader import render_to_string
            tracking_url = f"http://172.16.2.168:8000/orders/track-order/{order.id}/"
            html = render_to_string('orders/emails/delivery_otp.html', {
                'order': order,
                'user': order.user,
                'otp': order.delivery_otp,
                'tracking_url': tracking_url,
            })
            ok = send_brevo_email(
                subject=f'Your Delivery OTP for Order {order.order_id} — FabVibe',
                to_email=order.user.email,
                html_content=html,
                to_name=order.user.get_full_name() or order.user.email,
            )
            if ok:
                self.message_user(request, f'OTP email sent to {order.user.email}.')
            else:
                self.message_user(request, 'Status saved but OTP email failed — check email config.', level='warning')
        except Exception as e:
            logger.error(f'[OrderAdmin] OTP email error for {order.order_id}: {e}')
            self.message_user(request, f'Status saved but OTP email error: {e}', level='warning')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'size', 'quantity', 'price_at_purchase']
    search_fields = ['order__order_id', 'product__name']
    ordering = ['-order__created_at']


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__order_id', 'reason']
    ordering = ['-created_at']


@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__order_id', 'reason']
    ordering = ['-created_at']
