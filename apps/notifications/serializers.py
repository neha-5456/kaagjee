"""
Notification Serializers
"""
from rest_framework import serializers
from .models import AdminNotification


class AdminNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminNotification
        fields = ['id', 'notification_type', 'title', 'message', 'order_id', 
                  'user_id', 'is_read', 'created_at', 'read_at']
