from django.contrib import admin
from django.utils.html import format_html
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'order', 'amount_display', 'payment_type', 'status_badge', 'created_at']
    list_filter = ['status', 'payment_type', 'created_at']
    search_fields = ['payment_id', 'razorpay_payment_id', 'order__order_number']
    readonly_fields = ['payment_id', 'created_at', 'completed_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Payment Info', {
            'fields': ('payment_id', 'order', 'user', 'amount', 'currency', 'payment_type', 'status')
        }),
        ('Razorpay Details', {
            'fields': ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'payment_response'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        return format_html('<strong>₹{}</strong>', obj.amount)
    amount_display.short_description = 'Amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'success': '#10b981',
            'failed': '#ef4444',
            'refunded': '#6b7280',
        }
        return format_html(
            '<span style="background:{};color:white;padding:4px 12px;border-radius:20px;font-size:11px;">{}</span>',
            colors.get(obj.status, '#6b7280'), obj.get_status_display()
        )
    status_badge.short_description = 'Status'
