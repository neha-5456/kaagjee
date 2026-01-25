"""
Kaagjee - Orders Admin Configuration
====================================
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import FormSubmission, Cart, CartItem, Order, OrderItem, Payment


# ========================
# INLINES
# ========================

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'form_submission', 'unit_price', 'added_at']
    can_delete = True


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_title', 'unit_price', 'form_submission', 'created_at']
    can_delete = False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = [
        'payment_id', 'payment_for', 'amount', 'status',
        'razorpay_order_id', 'razorpay_payment_id', 'paid_at'
    ]
    can_delete = False


# ========================
# FORM SUBMISSION
# ========================

@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ['submission_id', 'product', 'user', 'status', 'price_at_submission', 'created_at']
    list_filter = ['status', 'product', 'created_at']
    search_fields = ['submission_id', 'user__phone', 'product__title']
    readonly_fields = ['submission_id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Submission Info', {
            'fields': ('submission_id', 'status', 'product', 'user')
        }),
        ('Form Data', {
            'fields': ('form_data', 'uploaded_files'),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('price_at_submission',)
        }),
        ('Notes', {
            'fields': ('user_notes', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ========================
# CART
# ========================

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_items', 'total_amount', 'updated_at']
    search_fields = ['user__phone']
    readonly_fields = ['total_items', 'total_amount', 'created_at', 'updated_at']
    inlines = [CartItemInline]


# ========================
# ORDER
# ========================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_id', 'user_phone', 'status_badge', 'payment_type',
        'total_amount', 'paid_amount', 'pending_badge', 'created_at'
    ]
    list_filter = ['status', 'payment_type', 'created_at']
    search_fields = ['order_id', 'user__phone', 'user_phone', 'user_email']
    readonly_fields = [
        'order_id', 'paid_amount', 'pending_amount',
        'first_payment_date', 'second_payment_date',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    inlines = [OrderItemInline, PaymentInline]
    
    fieldsets = (
        ('Order Info', {
            'fields': ('order_id', 'user', 'status')
        }),
        ('Payment Details', {
            'fields': (
                'payment_type', 'total_amount', 'paid_amount', 'pending_amount',
                'first_payment_amount', 'first_payment_date',
                'second_payment_amount', 'second_payment_date', 'second_payment_due_date'
            )
        }),
        ('User Details', {
            'fields': ('user_name', 'user_email', 'user_phone')
        }),
        ('Notes', {
            'fields': ('user_notes', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'partial_paid': '#3b82f6',
            'paid': '#10b981',
            'processing': '#8b5cf6',
            'completed': '#059669',
            'cancelled': '#ef4444',
            'refunded': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{}; color:white; padding:4px 12px; border-radius:20px; font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def pending_badge(self, obj):
        if obj.pending_amount > 0:
            return format_html(
                '<span style="background:#fef3c7; color:#92400e; padding:4px 12px; border-radius:20px; font-size:11px;">₹{}</span>',
                obj.pending_amount
            )
        return format_html(
            '<span style="background:#dcfce7; color:#166534; padding:4px 12px; border-radius:20px; font-size:11px;">Paid</span>'
        )
    pending_badge.short_description = 'Pending'


# ========================
# PAYMENT
# ========================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_id', 'order', 'user', 'payment_for',
        'amount_display', 'status_badge', 'paid_at'
    ]
    list_filter = ['status', 'payment_for', 'created_at']
    search_fields = ['payment_id', 'order__order_id', 'user__phone', 'razorpay_payment_id']
    readonly_fields = [
        'payment_id', 'razorpay_order_id', 'razorpay_payment_id',
        'razorpay_signature', 'razorpay_response', 'created_at', 'updated_at', 'paid_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Payment Info', {
            'fields': ('payment_id', 'order', 'user', 'payment_for', 'amount', 'status')
        }),
        ('Razorpay Details', {
            'fields': (
                'razorpay_order_id', 'razorpay_payment_id',
                'razorpay_signature', 'razorpay_response'
            ),
            'classes': ('collapse',)
        }),
        ('Error', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at'),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        return f"₹{obj.amount}"
    amount_display.short_description = 'Amount'
    
    def status_badge(self, obj):
        colors = {
            'created': '#6b7280',
            'pending': '#f59e0b',
            'success': '#10b981',
            'failed': '#ef4444',
            'refunded': '#8b5cf6',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{}; color:white; padding:4px 12px; border-radius:20px; font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
