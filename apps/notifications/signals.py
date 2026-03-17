"""
Signals — auto-create DB notifications + Firebase push on Order/Payment events.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.orders.models import Order, Payment
from .models import AdminNotification, UserNotification
from . import firebase


# ─────────────────────────────────────────────────────────────
# ORDER
# ─────────────────────────────────────────────────────────────

@receiver(post_save, sender=Order)
def on_order_save(sender, instance, created, **kwargs):
    if created:
        _handle_new_order(instance)
    else:
        _handle_order_status_change(instance)


def _handle_new_order(order):
    # Admin notification
    a = AdminNotification.objects.create(
        notification_type=AdminNotification.Type.NEW_ORDER,
        title=f'New Order: {order.order_id}',
        message=f'{order.user_name} ({order.user_phone}) placed an order. Total: ₹{order.total_amount}',
        order_id=order.order_id,
        user_id=order.user_id,
    )
    firebase.push_to_admins(
        title=f'🛒 New Order — {order.order_id}',
        body=f'{order.user_name} • ₹{order.total_amount}',
        data={'type': 'new_order', 'order_id': order.order_id},
        notif_obj=a,
    )

    # User notification
    u = UserNotification.objects.create(
        user=order.user,
        notification_type=UserNotification.Type.ORDER_PLACED,
        title=f'Order Placed — {order.order_id}',
        message=(
            f'Your order {order.order_id} has been placed successfully. '
            f'Total: ₹{order.total_amount}. We will keep you updated!'
        ),
        order_id=order.order_id,
    )
    firebase.push_to_user(
        user=order.user,
        title=f'✅ Order Placed — {order.order_id}',
        body=f'Total: ₹{order.total_amount}',
        data={'type': 'order_placed', 'order_id': order.order_id},
        notif_obj=u,
    )


# status → (UserNotification.Type, push_title, push_body, db_title, db_message)
_STATUS_NOTIF = {
    Order.Status.PROCESSING: (
        UserNotification.Type.ORDER_PROCESSING,
        '⚙️ Order Processing — {oid}',
        'Your documents are being verified.',
        'Order is Being Processed — {oid}',
        'Your order {oid} is under processing. We will update you soon.',
    ),
    Order.Status.COMPLETED: (
        UserNotification.Type.ORDER_COMPLETED,
        '🎉 Order Completed — {oid}',
        'Your order is complete. Thank you!',
        'Order Completed — {oid}',
        'Your order {oid} has been completed successfully. Thank you for using Kaagjee!',
    ),
    Order.Status.CANCELLED: (
        UserNotification.Type.ORDER_CANCELLED,
        '❌ Order Cancelled — {oid}',
        'Your order has been cancelled.',
        'Order Cancelled — {oid}',
        'Your order {oid} has been cancelled. Contact support if you have questions.',
    ),
}


def _handle_order_status_change(order):
    if order.status not in _STATUS_NOTIF:
        return
    ntype, push_t, push_b, db_t, db_m = _STATUS_NOTIF[order.status]
    oid = order.order_id
    u = UserNotification.objects.create(
        user=order.user,
        notification_type=ntype,
        title=db_t.format(oid=oid),
        message=db_m.format(oid=oid),
        order_id=oid,
    )
    firebase.push_to_user(
        user=order.user,
        title=push_t.format(oid=oid),
        body=push_b,
        data={'type': order.status, 'order_id': oid},
        notif_obj=u,
    )


# ─────────────────────────────────────────────────────────────
# PAYMENT
# ─────────────────────────────────────────────────────────────

@receiver(post_save, sender=Payment)
def on_payment_save(sender, instance, created, **kwargs):
    if instance.status == Payment.Status.SUCCESS:
        _handle_payment_success(instance)
    elif instance.status == Payment.Status.FAILED and not created:
        _handle_payment_failed(instance)


def _handle_payment_success(payment):
    oid = payment.order.order_id

    a = AdminNotification.objects.create(
        notification_type=AdminNotification.Type.PAYMENT_SUCCESS,
        title=f'Payment Received — {oid}',
        message=f'₹{payment.amount} received for order {oid}',
        order_id=oid,
        user_id=payment.user_id,
    )
    firebase.push_to_admins(
        title=f'💰 Payment Received — ₹{payment.amount}',
        body=f'Order {oid}',
        data={'type': 'payment_success', 'order_id': oid},
        notif_obj=a,
    )

    u = UserNotification.objects.create(
        user=payment.user,
        notification_type=UserNotification.Type.PAYMENT_SUCCESS,
        title=f'Payment Successful — ₹{payment.amount}',
        message=f'Your payment of ₹{payment.amount} for order {oid} was received successfully.',
        order_id=oid,
    )
    firebase.push_to_user(
        user=payment.user,
        title=f'✅ Payment Successful — ₹{payment.amount}',
        body=f'Order {oid}',
        data={'type': 'payment_success', 'order_id': oid},
        notif_obj=u,
    )


def _handle_payment_failed(payment):
    oid = payment.order.order_id

    AdminNotification.objects.create(
        notification_type=AdminNotification.Type.PAYMENT_FAILED,
        title=f'Payment Failed — {oid}',
        message=f'₹{payment.amount} payment failed for order {oid}',
        order_id=oid,
        user_id=payment.user_id,
    )

    u = UserNotification.objects.create(
        user=payment.user,
        notification_type=UserNotification.Type.PAYMENT_FAILED,
        title=f'Payment Failed — ₹{payment.amount}',
        message=(
            f'Your payment of ₹{payment.amount} for order {oid} failed. '
            f'Please retry or contact support.'
        ),
        order_id=oid,
    )
    firebase.push_to_user(
        user=payment.user,
        title=f'❌ Payment Failed — ₹{payment.amount}',
        body='Please retry or contact support.',
        data={'type': 'payment_failed', 'order_id': oid},
        notif_obj=u,
    )
