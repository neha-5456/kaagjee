"""
CloudServices India - Orders Admin
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, OrderFormSubmission, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_title', 'unit_price', 'total_price']
    fields = ['product_title', 'unit_price', 'quantity', 'total_price', 'payment_option']


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['from_status', 'to_status', 'changed_by', 'created_at']
    fields = ['from_status', 'to_status', 'notes', 'changed_by', 'created_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status_badge', 'total_amount', 'amount_paid', 'payment_status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'customer_name', 'customer_phone', 'user__phone_number']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Order Info', {
            'fields': ('order_number', 'user', 'status')
        }),
        ('Amounts / राशि', {
            'fields': ('subtotal', 'discount', 'total_amount', 'amount_paid')
        }),
        ('Customer Info / ग्राहक जानकारी', {
            'fields': ('customer_name', 'customer_email', 'customer_phone', 'customer_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'partially_paid': '#3b82f6',
            'paid': '#10b981',
            'processing': '#8b5cf6',
            'completed': '#059669',
            'cancelled': '#ef4444',
        }
        return format_html(
            '<span style="background:{};color:white;padding:4px 12px;border-radius:20px;font-size:11px;">{}</span>',
            colors.get(obj.status, '#6b7280'), obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def payment_status(self, obj):
        if obj.is_fully_paid:
            return format_html('<span style="color:#10b981;">✓ Fully Paid</span>')
        elif obj.amount_paid > 0:
            return format_html('<span style="color:#f59e0b;">◐ ₹{} Pending</span>', obj.amount_pending)
        return format_html('<span style="color:#ef4444;">✗ Unpaid</span>')
    payment_status.short_description = 'Payment'


@admin.register(OrderFormSubmission)
class OrderFormSubmissionAdmin(admin.ModelAdmin):
    list_display = ['order_item', 'is_verified', 'verified_by', 'created_at']
    list_filter = ['is_verified', 'created_at']
    readonly_fields = ['form_data', 'form_schema_snapshot', 'created_at']
