"""
Notification Signals - Auto-create notifications on events
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.orders.models import Order, Payment
from .models import AdminNotification


@receiver(post_save, sender=Order)
def create_order_notification(sender, instance, created, **kwargs):
    """Create notification when new order is placed"""
    if created:
        AdminNotification.objects.create(
            notification_type=AdminNotification.Type.NEW_ORDER,
            title=f'New Order: {instance.order_id}',
            message=f'New order placed by {instance.user_name} ({instance.user_phone}). Total: ₹{instance.total_amount}',
            order_id=instance.order_id,
            user_id=instance.user.id
        )


@receiver(post_save, sender=Payment)
def create_payment_notification(sender, instance, created, **kwargs):
    """Create notification when payment status changes"""
    if instance.status == Payment.Status.SUCCESS:
        AdminNotification.objects.create(
            notification_type=AdminNotification.Type.PAYMENT_SUCCESS,
            title=f'Payment Success: {instance.payment_id}',
            message=f'Payment of ₹{instance.amount} received for order {instance.order.order_id}',
            order_id=instance.order.order_id,
            user_id=instance.user.id
        )
    elif instance.status == Payment.Status.FAILED and not created:
        AdminNotification.objects.create(
            notification_type=AdminNotification.Type.PAYMENT_FAILED,
            title=f'Payment Failed: {instance.payment_id}',
            message=f'Payment of ₹{instance.amount} failed for order {instance.order.order_id}',
            order_id=instance.order.order_id,
            user_id=instance.user.id
        )
