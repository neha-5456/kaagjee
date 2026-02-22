"""
Admin Notification Admin
"""
from django.contrib import admin
from .models import AdminNotification


@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'order_id']
    readonly_fields = ['notification_type', 'title', 'message', 'order_id', 'user_id', 'created_at']
    list_per_page = 50
    
    def has_add_permission(self, request):
        return False
