from rest_framework import serializers
from .models import FCMDevice, UserNotification, AdminNotification


class RegisterTokenSerializer(serializers.Serializer):
    token    = serializers.CharField(min_length=10)
    platform = serializers.ChoiceField(choices=FCMDevice.Platform.choices, default='web')


class RemoveTokenSerializer(serializers.Serializer):
    token = serializers.CharField(min_length=10)


class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserNotification
        fields = ['id', 'notification_type', 'title', 'message',
                  'order_id', 'is_read', 'created_at', 'read_at']


class AdminNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AdminNotification
        fields = ['id', 'notification_type', 'title', 'message',
                  'order_id', 'user_id', 'is_read', 'created_at', 'read_at']


class AddOrderNoteSerializer(serializers.Serializer):
    note        = serializers.CharField(min_length=1)
    is_internal = serializers.BooleanField(default=False)
    notify_user = serializers.BooleanField(default=True)


class SendToUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    title   = serializers.CharField(min_length=1, max_length=200)
    message = serializers.CharField(min_length=1)
