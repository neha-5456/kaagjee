"""
CloudServices India - Categories Admin
"""
from django.contrib import admin
from .models import Category, Subcategory


class SubcategoryInline(admin.TabularInline):
    model = Subcategory
    extra = 2
    prepopulated_fields = {'slug': ('name',)}
    fields = ['name', 'name_hi', 'slug', 'icon', 'is_active', 'display_order']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'subcategories_count', 'products_count', 'is_featured', 'is_active', 'display_order']
    list_filter = ['is_featured', 'is_active']
    list_editable = ['is_featured', 'is_active', 'display_order']
    search_fields = ['name', 'name_hi']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SubcategoryInline]
    
    fieldsets = (
        ('Basic Info / बेसिक जानकारी', {
            'fields': ('name', 'name_hi', 'slug', 'description')
        }),
        ('Appearance / दिखावट', {
            'fields': ('icon', 'image')
        }),
        ('Settings / सेटिंग्स', {
            'fields': ('is_featured', 'is_active', 'display_order')
        }),
        ('SEO (Optional)', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'products_count', 'is_active', 'display_order']
    list_filter = ['category', 'is_active']
    list_editable = ['is_active', 'display_order']
    search_fields = ['name', 'category__name']
    prepopulated_fields = {'slug': ('name',)}
