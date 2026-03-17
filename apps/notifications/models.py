"""
Kaagjee — Notification Models

FCMDevice        : stores Firebase push tokens per user/device
UserNotification : in-app + push notifications for users
AdminNotification: in-app + push notifications for admin/staff

OrderNote lives in apps/orders/models.py to avoid circular migrations.
"""
from django.db import models
from django.conf import settings


class FCMDevice(models.Model):
    """One user can register multiple devices (Android, iOS, Web)."""

    class Platform(models.TextChoices):
        ANDROID = 'android', 'Android'
        IOS     = 'ios',     'iOS'
        WEB     = 'web',     'Web'

    user      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fcm_devices',
    )
    token     = models.TextField(unique=True)
    platform  = models.CharField(
        max_length=10, choices=Platform.choices, default=Platform.WEB
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'FCM Device'
        verbose_name_plural = 'FCM Devices'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} — {self.platform} ({'on' if self.is_active else 'off'})"


class UserNotification(models.Model):
    """Notification visible to a regular user."""

    class Type(models.TextChoices):
        ORDER_PLACED     = 'order_placed',     'Order Placed'
        ORDER_PROCESSING = 'order_processing', 'Order Processing'
        ORDER_COMPLETED  = 'order_completed',  'Order Completed'
        ORDER_CANCELLED  = 'order_cancelled',  'Order Cancelled'
        PAYMENT_SUCCESS  = 'payment_success',  'Payment Successful'
        PAYMENT_FAILED   = 'payment_failed',   'Payment Failed'
        ADMIN_NOTE       = 'admin_note',       'Note from Admin'
        GENERAL          = 'general',          'General'

    user              = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(max_length=30, choices=Type.choices)
    title             = models.CharField(max_length=200)
    message           = models.TextField()
    order_id          = models.CharField(max_length=50, blank=True)

    # Push tracking
    push_sent    = models.BooleanField(default=False)
    push_sent_at = models.DateTimeField(null=True, blank=True)

    # Read status
    is_read  = models.BooleanField(default=False)
    read_at  = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'User Notification'
        verbose_name_plural = 'User Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.user}] {self.title}"


class AdminNotification(models.Model):
    """Notification visible on the admin dashboard."""

    class Type(models.TextChoices):
        NEW_ORDER       = 'new_order',       'New Order'
        PAYMENT_SUCCESS = 'payment_success', 'Payment Success'
        PAYMENT_FAILED  = 'payment_failed',  'Payment Failed'
        ORDER_CANCELLED = 'order_cancelled', 'Order Cancelled'
        NEW_USER        = 'new_user',        'New User Registration'
        FORM_SUBMISSION = 'form_submission', 'New Form Submission'

    notification_type = models.CharField(max_length=30, choices=Type.choices)
    title             = models.CharField(max_length=200)
    message           = models.TextField()
    order_id          = models.CharField(max_length=50, blank=True)
    user_id           = models.IntegerField(null=True, blank=True)

    # Push tracking
    push_sent    = models.BooleanField(default=False)
    push_sent_at = models.DateTimeField(null=True, blank=True)

    # Read status
    is_read  = models.BooleanField(default=False)
    read_at  = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Admin Notification'
        verbose_name_plural = 'Admin Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} — {self.title}"
