from django.contrib import admin
from .models import FCMDevice, UserNotification, AdminNotification


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display  = ['user', 'platform', 'is_active', 'token_preview', 'created_at']
    list_filter   = ['platform', 'is_active']
    search_fields = ['user__phone_number', 'token']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['deactivate']

    def token_preview(self, obj):
        return obj.token[:40] + '...'
    token_preview.short_description = 'Token'

    @admin.action(description='Deactivate selected tokens')
    def deactivate(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display  = ['user', 'title', 'notification_type', 'order_id', 'is_read', 'push_sent', 'created_at']
    list_filter   = ['notification_type', 'is_read', 'push_sent']
    search_fields = ['title', 'order_id', 'user__phone_number']
    readonly_fields = ['created_at', 'read_at', 'push_sent_at']


@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    list_display  = ['title', 'notification_type', 'order_id', 'is_read', 'push_sent', 'created_at']
    list_filter   = ['notification_type', 'is_read', 'push_sent']
    search_fields = ['title', 'order_id']
    readonly_fields = ['created_at', 'read_at', 'push_sent_at']
