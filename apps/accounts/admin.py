"""
CloudServices India - Accounts Admin
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, OTP, UserAddress


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['phone_number', 'full_name', 'email', 'role', 'is_verified', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'is_verified', 'is_staff']
    search_fields = ['phone_number', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        ('Login Info', {'fields': ('phone_number', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'avatar')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_verified')}),
        ('Groups', {'fields': ('groups', 'user_permissions'), 'classes': ('collapse',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2', 'role'),
        }),
    )
    
    filter_horizontal = ('groups', 'user_permissions')


# @admin.register(OTP)
# class OTPAdmin(admin.ModelAdmin):
#     list_display = ['phone_number', 'purpose', 'otp_code', 'is_verified', 'attempts', 'expires_at', 'created_at']
#     list_filter = ['purpose', 'is_verified']
#     search_fields = ['phone_number']
#     readonly_fields = ['otp_code', 'created_at']


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'address_type', 'city', 'state', 'pincode', 'is_default']
    list_filter = ['address_type', 'is_default', 'state']
    search_fields = ['user__phone_number', 'full_name', 'city', 'pincode']
