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
from django.utils.html import format_html
from django.urls import path
from django.http import JsonResponse
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
                    'orders_count', 'created_at']
    list_filter = ['status', 'category', 'is_pan_india']
    list_editable = []
    search_fields = ['title', 'short_description']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ProductImageInline]
    save_on_top = True
    
    fieldsets = (
        ('📝 Basic Information', {
            'fields': ('title', 'slug', 'short_description', 'description', 'featured_image', 'youtube_link'),
        }),
        ('📁 Category', {
            'fields': ('category', 'subcategory'),
            'description': '<div style="background:#dcfce7;padding:10px;border-radius:8px;margin-bottom:15px;"><strong>💡 Tip:</strong> Pehle Category select karein, phir Subcategory automatically filter ho jayegi!</div>'
        }),
        ('📍 Location', {
            'fields': ('is_pan_india', 'available_states', 'available_cities'),
            'description': '<div style="background:#fef3c7;padding:10px;border-radius:8px;margin-bottom:15px;"><strong>💡 Tip:</strong> Pehle State select karein, phir City automatically filter ho jayegi!</div>'
        }),
        ('💰 Pricing', {
            'fields': ('full_price', 'half_price', 'original_price', 'allow_half_payment'),
        }),
        ('📋 Form Builder', {
            'fields': ('form_title', 'form_description', 'form_schema'),
            'description': '<div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:15px;border-radius:8px;margin-bottom:15px;"><strong>⭐ Visual Form Builder neeche hai!</strong></div>'
        }),
        ('⚙️ Status', {
            'fields': ('status',),
        }),
        # ('🔍 SEO (Optional)', {
        #     'fields': ('meta_title', 'meta_description', 'meta_keywords'),
        #     'classes': ('collapse',)
        # }),
        # ('ℹ️ Additional Info (Optional)', {
        #     'fields': ('processing_time', 'documents_required'),
        #     'classes': ('collapse',)
        # }),
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
        ]
        return custom_urls + urls

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


# @admin.register(ProductFAQ)
# class ProductFAQAdmin(admin.ModelAdmin):
#     list_display = ['product', 'question_short', 'is_active', 'display_order']
#     list_filter = ['product', 'is_active']
#     list_editable = ['is_active', 'display_order']
    
#     def question_short(self, obj):
#         return obj.question[:80] + '...' if len(obj.question) > 80 else obj.question
#     question_short.short_description = 'Question'