from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTP, Address

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'phone_number', 'email_verified', 'phone_verified', 'is_staff', 'created_at']
    list_filter = ['email_verified', 'phone_verified', 'is_staff', 'is_superuser', 'created_at']
    search_fields = ['email', 'username', 'phone_number']
    ordering = ['-created_at']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone_number', 'email_verified', 'phone_verified', 'otp_code', 'otp_expiry')}),
    )

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'code']
    ordering = ['-created_at']

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'city', 'state', 'is_default', 'created_at']
    list_filter = ['is_default', 'state', 'created_at']
    search_fields = ['user__email', 'full_name', 'city']
    ordering = ['-created_at']
