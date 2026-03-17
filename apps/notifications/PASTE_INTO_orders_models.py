

# ─── ADD THIS AT THE BOTTOM OF apps/orders/models.py ────────────────────────

class OrderNote(models.Model):
    """
    Admin note on an order.
    Save triggers UserNotification + Firebase push (lazy import → no circular deps).
    """
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='notes')
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='order_notes_added',
    )
    note        = models.TextField()
    is_internal = models.BooleanField(default=False, help_text='Not sent to user')
    notify_user = models.BooleanField(default=True,  help_text='Send Firebase push to user')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order Note'
        verbose_name_plural = 'Order Notes'

    def __str__(self):
        return f"Note on {self.order.order_id} by {self.added_by}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.notify_user and not self.is_internal:
            # Lazy import — prevents circular dependency at module load time
            from apps.notifications.models import UserNotification
            from apps.notifications import firebase
            notif = UserNotification.objects.create(
                user=self.order.user,
                notification_type=UserNotification.Type.ADMIN_NOTE,
                title=f'Update on your order {self.order.order_id}',
                message=self.note,
                order_id=self.order.order_id,
            )
            firebase.push_to_user(
                user=self.order.user,
                title=f'📋 Update on Order {self.order.order_id}',
                body=self.note[:100],
                data={'type': 'admin_note', 'order_id': self.order.order_id},
                notif_obj=notif,
            )
