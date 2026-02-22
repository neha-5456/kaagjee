"""
Kaagjee - Admin Notification System
"""
from django.db import models
from django.conf import settings


class AdminNotification(models.Model):
    """Admin notifications for orders and important events"""
    
    class Type(models.TextChoices):
        NEW_ORDER = 'new_order', 'New Order'
        PAYMENT_SUCCESS = 'payment_success', 'Payment Success'
        PAYMENT_FAILED = 'payment_failed', 'Payment Failed'
        ORDER_CANCELLED = 'order_cancelled', 'Order Cancelled'
        NEW_USER = 'new_user', 'New User Registration'
        FORM_SUBMISSION = 'form_submission', 'New Form Submission'
    
    notification_type = models.CharField(max_length=30, choices=Type.choices)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    order_id = models.CharField(max_length=50, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Admin Notification'
        verbose_name_plural = 'Admin Notifications'
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.title}"
