from django.contrib import admin
from .models import Cart, CartItem, Coupon

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at']
    search_fields = ['user__email']
    ordering = ['-updated_at']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'size', 'quantity', 'created_at']
    list_filter = ['size', 'created_at']
    search_fields = ['cart__user__email', 'product__name']
    ordering = ['-created_at']

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'valid_from', 'valid_to', 'is_active', 'used_count']
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_to']
    search_fields = ['code']
    ordering = ['-created_at']
