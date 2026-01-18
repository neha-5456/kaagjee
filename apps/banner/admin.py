"""
CloudServices India - Banner Admin
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Banner


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'image_preview', 'is_active', 'display_order', 'created_at']
    list_filter = ['is_active', 'created_at']
    list_editable = ['is_active', 'display_order']
    search_fields = ['title', 'description']
    
    
    fields = ['title', 'description', 'image', 'is_active', 'display_order']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width:80px;height:40px;object-fit:cover;border-radius:5px;"/>', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'