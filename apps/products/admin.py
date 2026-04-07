"""
CloudServices India - Product Admin
===================================
Features:
1. Cascading Dropdown: Category → Subcategory
2. Cascading Dropdown: State → City
3. Visual Form Builder
4. Rich Text Editor
"""
from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.urls import path, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django import forms
from .models import Product, ProductImage, ProductFAQ
from apps.locations.models import State, City
from apps.categories.models import Category, Subcategory


# ========================
# CUSTOM FORM
# ========================

class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'available_states': forms.SelectMultiple(attrs={'class': 'custom-multi-select'}),
            'available_cities': forms.SelectMultiple(attrs={'class': 'custom-multi-select'}),
        }


# ========================
# INLINE MODELS
# ========================

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'display_order']


class ProductFAQInline(admin.TabularInline):
    model = ProductFAQ
    extra = 1
    fields = ['question', 'answer', 'display_order', 'is_active']


# ========================
# PRODUCT ADMIN
# ========================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ['title', 'category', 'status_badge', 'price_display', 'form_fields_badge',
                    'orders_count', 'duplicate_btn', 'created_at']
    list_filter = ['status', 'category', 'is_pan_india']
    list_editable = []
    search_fields = ['title', 'short_description']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ProductImageInline, ProductFAQInline]
    save_on_top = True
    actions = ['duplicate_selected']
    
    fieldsets = (
        ('📝 Basic Information', {
            'fields': ('title', 'slug', 'short_description', 'description', 'featured_image', 'youtube_link'),
        }),
        ('📁 Category', {
            'fields': ('category', 'subcategory'),
            'description': '<div style="background:#dcfce7;padding:10px;border-radius:8px;margin-bottom:15px;"><strong>💡 Tip:</strong> First select Category, then Subcategory will be automatically filtered!</div>'
        }),
        ('📍 Location', {
            'fields': ('is_pan_india', 'available_states', 'available_cities'),
            'description': '<div style="background:#fef3c7;padding:10px;border-radius:8px;margin-bottom:15px;"><strong>💡 Tip:</strong> First select State, then City will be automatically filtered!</div>'
        }),
        ('💰 Pricing', {
            'fields': ('full_price', 'half_price', 'original_price', 'allow_half_payment'),
        }),
        ('📋 Form Builder', {
            'fields': ('form_title', 'form_description', 'form_schema'),
            'description': '<div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:15px;border-radius:8px;margin-bottom:15px;"><strong>⭐ Visual Form Builder neeche hai!</strong></div>'
        }),
        ('📄 Preview Template', {
            'fields': ('is_preview_enabled', 'preview_template',),
            'description': '<div style="background:linear-gradient(135deg,#0ea5e9,#6366f1);color:white;padding:15px;border-radius:8px;margin-bottom:15px;"><strong>📄 Preview Template:</strong> Use <code style="background:rgba(255,255,255,0.2);padding:2px 6px;border-radius:4px;">{{field_name}}</code> placeholders. Available placeholders will be shown automatically from Form Builder fields.</div>'
        }),
        ('⚙️ Status', {
            'fields': ('status',),
        }),
        # ('🔍 SEO (Optional)', {
        #     'fields': ('meta_title', 'meta_description', 'meta_keywords'),
        #     'classes': ('collapse',)
        # }),
        ('ℹ️ Additional Info (Optional)', {
            'fields': ('how_its_work', 'documents_required', 'data_privacy_policy'),
            'classes': ('collapse',)
        }),
    )

    class Media:
        css = {
            'all': [
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
                'https://cdn.quilljs.com/1.3.7/quill.snow.css',
            ]
        }
        js = [
            'https://cdn.quilljs.com/1.3.7/quill.min.js',
        ]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('ajax/get-subcategories/', self.admin_site.admin_view(self.get_subcategories_ajax), name='product-get-subcategories'),
            path('ajax/get-cities/', self.admin_site.admin_view(self.get_cities_ajax), name='product-get-cities'),
            path('<int:product_id>/duplicate/', self.admin_site.admin_view(self.duplicate_product), name='product-duplicate'),
        ]
        return custom_urls + urls

    def duplicate_product(self, request, product_id):
        """Duplicate a product with all its data"""
        from django.utils.text import slugify
        import copy, json

        try:
            original = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            self.message_user(request, 'Product not found.', level='error')
            return HttpResponseRedirect(reverse('admin:products_product_changelist'))

        # Generate unique slug
        base_slug = original.slug + '-copy'
        slug = base_slug
        counter = 1
        while Product.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        # Duplicate product
        new_product = Product.objects.get(pk=product_id)
        new_product.pk        = None
        new_product.id        = None
        new_product.title     = original.title + ' (Copy)'
        new_product.slug      = slug
        new_product.status    = Product.Status.DRAFT
        new_product.orders_count = 0
        new_product.views_count  = 0
        new_product.form_schema  = copy.deepcopy(original.form_schema)
        new_product.preview_template = original.preview_template
        new_product.save()

        # Copy M2M — states & cities
        new_product.available_states.set(original.available_states.all())
        new_product.available_cities.set(original.available_cities.all())

        # Copy FAQs
        for faq in original.faqs.all():
            faq.pk = None
            faq.product = new_product
            faq.save()

        # Copy images
        for img in original.images.all():
            img.pk = None
            img.product = new_product
            img.save()

        self.message_user(request, f'✅ "{original.title}" successfully duplicated as "{new_product.title}" (Draft).')
        return HttpResponseRedirect(reverse('admin:products_product_change', args=[new_product.pk]))

    def get_subcategories_ajax(self, request):
        """AJAX: Get subcategories by category"""
        category_id = request.GET.get('category_id', '')
        
        if category_id:
            subcategories = Subcategory.objects.filter(
                category_id=category_id, 
                is_active=True
            ).values('id', 'name')
            return JsonResponse({
                'success': True,
                'subcategories': list(subcategories)
            })
        return JsonResponse({'success': True, 'subcategories': []})

    def get_cities_ajax(self, request):
        """AJAX: Get cities by states"""
        state_ids = request.GET.get('state_ids', '')
        
        if state_ids:
            state_id_list = [int(x) for x in state_ids.split(',') if x.strip()]
            cities = City.objects.filter(
                state_id__in=state_id_list, 
                is_active=True
            ).values('id', 'name', 'state__name', 'state__code')
            return JsonResponse({
                'success': True,
                'cities': list(cities)
            })
        return JsonResponse({'success': True, 'cities': []})

    def duplicate_btn(self, obj):
        url = reverse('admin:product-duplicate', args=[obj.pk])
        return format_html(
            '<a href="{}" style="background:#f59e0b;color:#fff;padding:4px 12px;border-radius:6px;'
            'font-size:11px;font-weight:600;text-decoration:none;white-space:nowrap">'
            '⧉ Duplicate</a>', url
        )
    duplicate_btn.short_description = 'Duplicate'

    def duplicate_selected(self, request, queryset):
        import copy
        count = 0
        for original in queryset:
            base_slug = original.slug + '-copy'
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            new_p = Product.objects.get(pk=original.pk)
            new_p.pk = None
            new_p.id = None
            new_p.title = original.title + ' (Copy)'
            new_p.slug  = slug
            new_p.status = Product.Status.DRAFT
            new_p.orders_count = 0
            new_p.views_count  = 0
            new_p.form_schema  = copy.deepcopy(original.form_schema)
            new_p.preview_template = original.preview_template
            new_p.save()
            new_p.available_states.set(original.available_states.all())
            new_p.available_cities.set(original.available_cities.all())
            for faq in original.faqs.all():
                faq.pk = None; faq.product = new_p; faq.save()
            for img in original.images.all():
                img.pk = None; img.product = new_p; img.save()
            count += 1
        self.message_user(request, f'✅ {count} product(s) duplicated as Draft.')
    duplicate_selected.short_description = '⧉ Duplicate selected products'

    def status_badge(self, obj):
        colors = {
            'draft': '#6b7280',
            'active': '#10b981',
            'inactive': '#ef4444',
            'coming_soon': '#f59e0b',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def price_display(self, obj):
        if obj.original_price and obj.discount_percentage > 0:
            return format_html(
                '<span style="text-decoration:line-through;color:#9ca3af;">₹{}</span> <strong style="color:#10b981;">₹{}</strong> <span style="background:#dcfce7;color:#166534;padding:2px 6px;border-radius:10px;font-size:10px;">{}% OFF</span>',
                obj.original_price, obj.full_price, obj.discount_percentage
            )
        return format_html('<strong>₹{}</strong>', obj.full_price)
    price_display.short_description = 'Price'

    def form_fields_badge(self, obj):
        count = obj.form_fields_count
        if count > 0:
            return format_html(
                '<span style="background:#3b82f6;color:white;padding:4px 10px;border-radius:20px;font-size:11px;">{} fields</span>',
                count
            )
        return format_html(
            '<span style="background:#ef4444;color:white;padding:4px 10px;border-radius:20px;font-size:11px;">No form</span>'
        )
    form_fields_badge.short_description = 'Form'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image_preview', 'display_order']
    list_filter = ['product']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:50px;height:50px;object-fit:cover;border-radius:5px;"/>', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(ProductFAQ)
class ProductFAQAdmin(admin.ModelAdmin):
    list_display = ['product', 'question_short', 'is_active', 'display_order']
    list_filter = ['product', 'is_active']
    list_editable = ['is_active', 'display_order']
    
    def question_short(self, obj):
        return obj.question[:80] + '...' if len(obj.question) > 80 else obj.question
    question_short.short_description = 'Question'