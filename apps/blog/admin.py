"""
CloudServices India - Blog Admin
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import BlogPost, BlogCategory, BlogTag


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'status_badge', 'views_count', 'created_at']
    list_filter = ['status', 'categories', 'created_at']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['categories', 'tags']
    
    fieldsets = (
        ('📝 Basic Information', {
            'fields': ('title', 'slug', 'content', 'excerpt', 'featured_image')
        }),
        ('📁 Categories & Tags', {
            'fields': ('categories', 'tags')
        }),
        ('⚙️ Settings', {
            'fields': ('author', 'status', 'published_at')
        }),
        ('🔍 SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        colors = {
            'draft': '#6b7280',
            'published': '#10b981',
            'archived': '#ef4444',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:white;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'posts_count', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

    def posts_count(self, obj):
        return obj.posts.count()
    posts_count.short_description = 'Posts'


@admin.register(BlogTag)
class BlogTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'posts_count', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

    def posts_count(self, obj):
        return obj.posts.count()
    posts_count.short_description = 'Posts'