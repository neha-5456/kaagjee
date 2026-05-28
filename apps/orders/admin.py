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
    readonly_fields = ['submission_id', 'created_at', 'updated_at', 'filled_preview', 'print_performa_btn']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Submission Info', {
            'fields': ('submission_id', 'status', 'product', 'user')
        }),
        ('📄 Filled Document Preview', {
            'fields': ('print_performa_btn', 'filled_preview',),
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

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:submission_id>/print-performa/',
                 self.admin_site.admin_view(self.print_performa_view),
                 name='submission-print-performa'),
        ]
        return custom_urls + urls

    def print_performa_view(self, request, submission_id):
        import re, json
        from django.http import HttpResponse
        try:
            obj = FormSubmission.objects.select_related('product', 'user').get(id=submission_id)
        except FormSubmission.DoesNotExist:
            return HttpResponse('Not found', status=404)

        product = obj.product
        if not product or not product.preview_template:
            return HttpResponse('No preview template configured.', status=400)

        form_data   = obj.form_data or {}
        form_schema = product.form_schema or []
        
        # Debug: Log form data
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[Admin Preview] FormSubmission {obj.submission_id}: form_data keys = {list(form_data.keys())}")
        if form_data and 'registration_number' in form_data:
            logger.info(f"[Admin Preview] Found registration_number = {form_data.get('registration_number')}")

        lookup = dict(form_data)
        def collect(fields):
            for field in (fields or []):
                name         = field.get('name', '')
                label        = field.get('label', '')
                performa_key = field.get('performa_key', '').strip()
                value        = form_data.get(name, '') or (form_data.get(performa_key, '') if performa_key else '')
                if name:         lookup[name]         = value
                if performa_key: lookup[performa_key] = value
                if label:
                    normalized = re.sub(r'[^\w]+', '_', label.strip()).strip('_').lower()
                    lookup[normalized] = value
                    lookup[label]      = value
                for opt in (field.get('options') or []):
                    collect(opt.get('nested_fields') or [])
        collect(form_schema)

        def replacer(match):
            key = match.group(1).strip()
            val = lookup.get(key, '')
            if isinstance(val, list):
                val = ', '.join(str(v) for v in val)
            return f'<strong style="color:#1e40af">{val}</strong>' if val else f'<span style="color:#dc2626">({key})</span>'

        def render_html(html):
            return re.sub(r'\{\{\s*([\w_ ]+)\s*\}\}', replacer, html)

        pages = []
        try:
            parsed = json.loads(product.preview_template)
            if isinstance(parsed, list):
                pages = parsed
        except (ValueError, TypeError):
            pass
        if not pages:
            pages = [{'title': 'Page 1', 'template': product.preview_template}]

        pages_html = ''
        for i, page in enumerate(pages):
            is_last = (i == len(pages) - 1)
            page_break = '' if is_last else 'page-break-after: always;'
            content = render_html(page.get('template', ''))
            title = page.get('title', f'Page {i+1}')
            pages_html += f'<div style="{page_break}"><div class="no-print" style="font-size:11px;color:#6b7280;margin-bottom:6px;font-family:sans-serif">📄 {title}</div>{content}</div>'

        html = f"""
        <!DOCTYPE html><html><head><meta charset="utf-8">
        <title>Performa - {obj.submission_id}</title>
        <style>
            @page {{
                margin: 20mm 15mm;
                @top-left   {{ content: ''; }}
                @top-center {{ content: ''; }}
                @top-right  {{ content: ''; }}
                @bottom-left   {{ content: ''; }}
                @bottom-center {{ content: ''; }}
                @bottom-right  {{ content: ''; }}
            }}
            * {{ box-sizing: border-box; }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 13px;
                color: #1f2937;
                line-height: 1.6;
                margin: 0;
                padding: 0;
            }}
            h1 {{ font-size: 20px; font-weight: 700; margin: 10px 0 6px; }}
            h2 {{ font-size: 17px; font-weight: 700; margin: 8px 0 5px; }}
            h3 {{ font-size: 15px; font-weight: 700; margin: 6px 0 4px; }}
            p  {{ margin: 0; padding: 0; min-height: 1.6em; }}
            strong, b {{ font-weight: 700; }}
            em, i     {{ font-style: italic; }}
            u         {{ text-decoration: underline; }}
            s         {{ text-decoration: line-through; }}
            a         {{ color: #2563eb; text-decoration: underline; }}
            .ql-align-center  {{ text-align: center; }}
            .ql-align-right   {{ text-align: right; }}
            .ql-align-justify {{ text-align: justify; }}
            .ql-indent-1 {{ padding-left: 3em; }}
            .ql-indent-2 {{ padding-left: 6em; }}
            .ql-indent-3 {{ padding-left: 9em; }}
            .ql-indent-4 {{ padding-left: 12em; }}
            .ql-indent-5 {{ padding-left: 15em; }}
            ol, ul {{ padding-left: 1.5em; margin: 4px 0; }}
            li {{ margin: 2px 0; }}
            li.ql-indent-1 {{ padding-left: 3em; }}
            li.ql-indent-2 {{ padding-left: 6em; }}
            table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
            td, th {{ border: 1px solid #d1d5db; padding: 6px 10px; }}
            th {{ background: #f1f5f9; font-weight: 600; }}
            @media print {{
                .no-print {{ display: none !important; }}
                html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            }}
        </style></head><body>
        <div class="no-print" style="background:#4f46e5;color:#fff;padding:10px 20px;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between;font-family:sans-serif">
            <span style="font-weight:700">📄 {product.title} &nbsp;|&nbsp; {len(pages)} page(s) &nbsp;|&nbsp; {obj.user}</span>
            <button onclick="window.print()" style="background:#fff;color:#4f46e5;border:none;padding:6px 18px;border-radius:6px;font-weight:700;cursor:pointer">🖨️ Print / Save PDF</button>
        </div>
        {pages_html}
        </body></html>
        """
        return HttpResponse(html, content_type='text/html')

    def print_performa_btn(self, obj):
        if not obj.pk or not obj.product or not obj.product.preview_template:
            return format_html('<span style="color:#9ca3af;font-size:12px">No template configured</span>')
        url = f'/admin/orders/formsubmission/{obj.pk}/print-performa/'
        return format_html(
            '<a href="{}" target="_blank" style="background:#4f46e5;color:#fff;padding:8px 20px;'
            'border-radius:8px;font-size:13px;font-weight:700;text-decoration:none;display:inline-block">'
            '🖨️ Print / Save PDF (All Pages)</a>', url
        )
    print_performa_btn.short_description = 'Print Performa'

    def filled_preview(self, obj):
        import re, json
        template = obj.product.preview_template if obj.product else ''
        if not template:
            return format_html(
                '<div style="padding:12px;background:#fef3c7;border:1px solid #fbbf24;border-radius:8px;color:#92400e;font-size:13px;">'
                'No preview template set for this product.</div>'
            )

        form_data = obj.form_data or {}

        def replacer(match):
            key = match.group(1).strip()
            val = form_data.get(key, '')
            if isinstance(val, list):
                val = ', '.join(str(v) for v in val)
            if val:
                return '<span style="background:#dbeafe;color:#1e40af;padding:1px 5px;border-radius:3px;font-weight:600">' + str(val) + '</span>'
            return '<span style="background:#fecaca;color:#991b1b;padding:1px 5px;border-radius:3px">(' + key + ')</span>'

        def render_html(html):
            rendered = re.sub(r'\{\{\s*([\w_ ]+)\s*\}\}', replacer, html)
            return rendered.replace('\n', '<br>')

        # Parse pages
        pages = []
        try:
            parsed = json.loads(template)
            if isinstance(parsed, list):
                pages = parsed
        except (ValueError, TypeError):
            pass

        if pages:
            pages_html = ''
            for i, page in enumerate(pages):
                title = page.get('title', f'Page {i+1}')
                content = render_html(page.get('template', ''))
                pages_html += (
                    f'<div style="margin-bottom:24px;border:2px solid #e5e7eb;border-radius:10px;overflow:hidden">'
                    f'<div style="background:#4f46e5;color:#fff;padding:8px 16px;font-size:12px;font-weight:700;font-family:sans-serif">'
                    f'📄 {title}</div>'
                    f'<div style="padding:20px 24px;font-size:13px;line-height:1.8;font-family:Georgia,serif">{content}</div>'
                    f'</div>'
                )
            header = (
                f'<div style="margin-bottom:16px;display:flex;align-items:center;gap:8px">'
                f'<span style="background:#4f46e5;color:#fff;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;font-family:sans-serif">PREVIEW — {len(pages)} PAGES</span>'
                f'<span style="font-size:12px;color:#6b7280;font-family:sans-serif">{obj.product.title} — {obj.user}</span>'
                f'</div>'
            )
            return mark_safe(f'<div style="max-width:750px">{header}{pages_html}</div>')
        else:
            # Single page fallback
            rendered = render_html(template)
            return mark_safe(
                '<div style="background:#fff;border:2px solid #e5e7eb;border-radius:10px;padding:20px 24px;'
                'font-size:13px;line-height:1.8;max-width:700px;font-family:Georgia,serif">'
                + rendered + '</div>'
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
        import re, json
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

        # Build lookup from form_data + schema keys (with nested field support)
        lookup = dict(form_data)
        def collect(fields):
            for field in (fields or []):
                name         = field.get('name', '')
                label        = field.get('label', '')
                performa_key = field.get('performa_key', '').strip()
                value        = form_data.get(name, '') or (form_data.get(performa_key, '') if performa_key else '')
                if name:         lookup[name]         = value
                if performa_key: lookup[performa_key] = value
                if label:
                    normalized = re.sub(r'[^\w]+', '_', label.strip()).strip('_').lower()
                    lookup[normalized] = value
                    lookup[label]      = value
                for opt in (field.get('options') or []):
                    collect(opt.get('nested_fields') or [])
        collect(form_schema)

        def replacer(match):
            key = match.group(1).strip()
            val = lookup.get(key, '')
            if isinstance(val, list):
                val = ', '.join(str(v) for v in val)
            return f'<strong style="color:#1e40af">{val}</strong>' if val else f'<span style="color:#dc2626">({key})</span>'

        def render_html(html):
            return re.sub(r'\{\{\s*([\w_ ]+)\s*\}\}', replacer, html)

        # Parse pages
        pages = []
        try:
            parsed = json.loads(product.preview_template)
            if isinstance(parsed, list):
                pages = parsed
        except (ValueError, TypeError):
            pass
        if not pages:
            pages = [{'title': 'Page 1', 'template': product.preview_template}]

        # Build pages HTML with print page-break
        pages_html = ''
        for i, page in enumerate(pages):
            is_last = (i == len(pages) - 1)
            page_break = '' if is_last else 'page-break-after: always;'
            content = render_html(page.get('template', ''))
            title = page.get('title', f'Page {i+1}')
            pages_html += f'''
            <div style="{page_break}">
                <div class="page-title no-print" style="font-size:11px;color:#6b7280;margin-bottom:8px;font-family:sans-serif">
                    📄 {title}
                </div>
                {content}
            </div>
            '''

        html = f"""
        <!DOCTYPE html><html><head><meta charset="utf-8">
        <title>Performa - {order.order_id}</title>
        <style>
            @page {{
                margin: 20mm 15mm;
                /* Remove browser-added URL and date/time from print header/footer */
                @top-left   {{ content: ''; }}
                @top-center {{ content: ''; }}
                @top-right  {{ content: ''; }}
                @bottom-left   {{ content: ''; }}
                @bottom-center {{ content: ''; }}
                @bottom-right  {{ content: ''; }}
            }}
            * {{ box-sizing: border-box; }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 13px;
                color: #1f2937;
                line-height: 1.6;
                margin: 0;
                padding: 0;
            }}
            h1 {{ font-size: 20px; font-weight: 700; margin: 10px 0 6px; }}
            h2 {{ font-size: 17px; font-weight: 700; margin: 8px 0 5px; }}
            h3 {{ font-size: 15px; font-weight: 700; margin: 6px 0 4px; }}
            p  {{ margin: 0; padding: 0; min-height: 1.6em; }}
            strong, b {{ font-weight: 700; }}
            em, i     {{ font-style: italic; }}
            u         {{ text-decoration: underline; }}
            s         {{ text-decoration: line-through; }}
            a         {{ color: #2563eb; text-decoration: underline; }}
            .ql-align-center  {{ text-align: center; }}
            .ql-align-right   {{ text-align: right; }}
            .ql-align-justify {{ text-align: justify; }}
            .ql-indent-1 {{ padding-left: 3em; }}
            .ql-indent-2 {{ padding-left: 6em; }}
            .ql-indent-3 {{ padding-left: 9em; }}
            .ql-indent-4 {{ padding-left: 12em; }}
            .ql-indent-5 {{ padding-left: 15em; }}
            ol, ul {{ padding-left: 1.5em; margin: 4px 0; }}
            li {{ margin: 2px 0; }}
            li.ql-indent-1 {{ padding-left: 3em; }}
            li.ql-indent-2 {{ padding-left: 6em; }}
            table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
            td, th {{ border: 1px solid #d1d5db; padding: 6px 10px; }}
            th {{ background: #f1f5f9; font-weight: 600; }}
            @media print {{
                .no-print {{ display: none !important; }}
                /* Force browser to hide its own header/footer */
                html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            }}
        </style></head><body>
        <div class="no-print" style="background:#1e40af;color:#fff;padding:10px 20px;margin-bottom:30px;display:flex;align-items:center;justify-content:space-between;font-family:sans-serif">
            <span style="font-weight:700">📄 {product.title} &nbsp;|&nbsp; {len(pages)} page(s)</span>
            <button onclick="window.print()" style="background:#fff;color:#1e40af;border:none;padding:6px 18px;border-radius:6px;font-weight:700;cursor:pointer">🖨️ Print / Save PDF</button>
        </div>
        <div class="no-print" style="text-align:center;margin-bottom:20px;font-family:sans-serif;font-size:12px;color:#6b7280">
            Order: <strong>{order.order_id}</strong> &nbsp;|&nbsp; {order.user_name} &nbsp;|&nbsp; {order.user_phone} &nbsp;|&nbsp; {order.created_at.strftime('%d %b %Y')}
        </div>
        {pages_html}
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
