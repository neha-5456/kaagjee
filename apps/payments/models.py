"""
CloudServices India - Payment Models
"""
from django.db import models
from apps.accounts.models import User
from apps.orders.models import Order
import uuid


class Payment(models.Model):
    """Payment Model"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    class PaymentType(models.TextChoices):
        FULL = 'full', 'Full Payment'
        HALF = 'half', '50% Advance'
        REMAINING = 'remaining', 'Remaining Amount'

    payment_id = models.CharField(max_length=50, unique=True, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.FULL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Razorpay fields
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)
    payment_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f"{self.payment_id} - ₹{self.amount}"

    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = f"PAY{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)
