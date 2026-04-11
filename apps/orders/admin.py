"""
Kaagjee - Orders Admin Configuration
====================================
"""
from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.urls import reverse
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
    list_display = ['submission_id', 'product', 'user', 'status', 'price_at_submission', 'preview_link', 'created_at']
    list_filter = ['status', 'product', 'created_at']
    search_fields = ['submission_id', 'user__phone', 'product__title']
    readonly_fields = ['submission_id', 'created_at', 'updated_at', 'filled_preview']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Submission Info', {
            'fields': ('submission_id', 'status', 'product', 'user')
        }),
        ('📄 Filled Document Preview', {
            'fields': ('filled_preview',),
        }),
        ('Form Data (Raw JSON)', {
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

    def filled_preview(self, obj):
        import re
        template = obj.product.preview_template if obj.product else ''
        if not template:
            return format_html(
                '<div style="padding:12px;background:#fef3c7;border:1px solid #fbbf24;border-radius:8px;color:#92400e;font-size:13px;">'
                '<i class="fas fa-exclamation-triangle"></i> No preview template set for this product. '
                'Go to <strong>Products → {}</strong> and add a Preview Template.</div>',
                obj.product.title if obj.product else 'product'
            )

        form_data = obj.form_data or {}

        def replacer(match):
            key = match.group(1).strip()
            val = form_data.get(key, '')
            if isinstance(val, list):
                val = ', '.join(str(v) for v in val)
            if val:
                return '<span style="background:#dbeafe;color:#1e40af;padding:1px 5px;border-radius:3px;font-weight:600">' + str(val) + '</span>'
            return '<span style="background:#fecaca;color:#991b1b;padding:1px 5px;border-radius:3px">(' + key + ' - not filled)</span>'

        rendered = re.sub(r'\{\{\s*([\w_]+)\s*\}\}', replacer, template)
        rendered = rendered.replace('\n', '<br>')

        return mark_safe(
            '<div style="background:#fff;border:2px solid #e5e7eb;border-radius:10px;padding:20px 24px;'
            'font-size:13px;line-height:1.8;max-width:700px;font-family:Georgia,serif">'
            '<div style="border-bottom:1px solid #e5e7eb;margin-bottom:14px;padding-bottom:10px;'
            'display:flex;align-items:center;gap:8px">'
            '<span style="background:#4f46e5;color:#fff;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;font-family:sans-serif">PREVIEW</span>'
            '<span style="font-size:12px;color:#6b7280;font-family:sans-serif">' + obj.product.title + ' — submitted by ' + str(obj.user) + '</span>'
            '</div>'
            + rendered +
            '</div>'
        )
    filled_preview.short_description = 'Filled Document Preview'
    filled_preview.allow_tags = True

    def preview_link(self, obj):
        if obj.product and obj.product.preview_template:
            return format_html(
                '<a href="{}" style="background:#4f46e5;color:#fff;padding:3px 10px;border-radius:6px;font-size:11px;font-weight:600;text-decoration:none">'
                '📄 View</a>',
                f'/admin/orders/formsubmission/{obj.id}/change/'
            )
        return format_html('<span style="color:#9ca3af;font-size:11px">No template</span>')
    preview_link.short_description = 'Preview'


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
        'total_amount', 'paid_amount', 'pending_badge', 'performa_download_btn', 'created_at'
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

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<str:order_id>/download-performa/<int:item_id>/',
                 self.admin_site.admin_view(self.download_performa),
                 name='order-download-performa'),
        ]
        return custom_urls + urls

    def download_performa(self, request, order_id, item_id):
        import re
        from django.http import HttpResponse
        try:
            order = Order.objects.get(order_id=order_id)
            item  = OrderItem.objects.select_related('product').get(id=item_id, order=order)
        except (Order.DoesNotExist, OrderItem.DoesNotExist):
            return HttpResponse('Not found', status=404)

        product = item.product
        if not product or not product.preview_template:
            return HttpResponse('No preview template configured.', status=400)

        form_data   = item.form_data or {}
        form_schema = product.form_schema or []

        lookup = dict(form_data)
        for field in form_schema:
            name         = field.get('name', '')
            label        = field.get('label', '')
            performa_key = field.get('performa_key', '').strip()
            value        = form_data.get(name, '') or form_data.get(performa_key, '')
            if name:         lookup[name]         = value
            if performa_key: lookup[performa_key] = value
            if label:
                normalized = re.sub(r'[^\w]+', '_', label.strip()).strip('_').lower()
                lookup[normalized] = value
                lookup[label]      = value

        def replacer(match):
            key = match.group(1).strip()
            val = lookup.get(key, '')
            if isinstance(val, list):
                val = ', '.join(str(v) for v in val)
            return f'<strong style="color:#1e40af">{val}</strong>' if val else f'<span style="color:#dc2626">({key})</span>'

        rendered = re.sub(r'\{\{\s*([\w_ ]+)\s*\}\}', replacer, product.preview_template)
        rendered = rendered.replace('\n', '<br>')

        html = f"""
        <!DOCTYPE html><html><head><meta charset="utf-8">
        <title>Performa - {order.order_id}</title>
        <style>
            body {{ font-family: Georgia, serif; font-size: 14px; padding: 60px; color: #1f2937; line-height: 1.8; }}
            .header {{ text-align: center; border-bottom: 2px solid #1e40af; padding-bottom: 16px; margin-bottom: 30px; }}
            .header h2 {{ color: #1e40af; margin: 0 0 4px; }}
            .meta {{ font-size: 12px; color: #6b7280; }}
            @media print {{ .no-print {{ display: none; }} body {{ padding: 20px; }} }}
        </style></head><body>
        <div class="no-print" style="background:#1e40af;color:#fff;padding:10px 20px;margin:-60px -60px 40px;display:flex;align-items:center;justify-content:space-between">
            <span style="font-weight:700">📄 Performa — {product.title}</span>
            <button onclick="window.print()" style="background:#fff;color:#1e40af;border:none;padding:6px 18px;border-radius:6px;font-weight:700;cursor:pointer">🖨️ Print / Save PDF</button>
        </div>
        <div class="header">
            <h2>{product.title}</h2>
            <div class="meta">Order: {order.order_id} &nbsp;|&nbsp; {order.user_name} &nbsp;|&nbsp; {order.user_phone}</div>
        </div>
        {rendered}
        <div style="margin-top:60px;border-top:1px solid #e5e7eb;padding-top:16px;font-size:12px;color:#9ca3af;text-align:center">
            Order {order.order_id} — {order.created_at.strftime('%d %b %Y')}
        </div>
        </body></html>
        """
        return HttpResponse(html, content_type='text/html')

    def performa_download_btn(self, obj):
        from django.urls import reverse
        buttons = []
        for item in obj.items.all():
            if item.product and item.product.preview_template:
                url = reverse('admin:order-download-performa', args=[obj.order_id, item.id])
                buttons.append(
                    f'<a href="{url}" target="_blank" style="background:#1e40af;color:#fff;padding:4px 12px;'
                    f'border-radius:6px;font-size:11px;font-weight:600;text-decoration:none">'
                    f'📄 Performa</a>'
                )
        return mark_safe(''.join(buttons)) if buttons else '—'
    performa_download_btn.short_description = 'Performa'
    
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
