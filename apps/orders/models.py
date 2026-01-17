"""
CloudServices India - Order Models
"""
from django.db import models
from apps.accounts.models import User
from apps.products.models import Product
from apps.locations.models import State, City
import uuid


class Order(models.Model):
    """Order Model"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PARTIALLY_PAID = 'partially_paid', 'Partially Paid'
        PAID = 'paid', 'Paid'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    order_number = models.CharField(max_length=50, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Customer Info (snapshot)
    customer_name = models.CharField(max_length=200, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            from django.utils import timezone
            date_str = timezone.now().strftime('%Y%m%d')
            random_str = uuid.uuid4().hex[:6].upper()
            self.order_number = f"CS{date_str}{random_str}"
        super().save(*args, **kwargs)

    @property
    def amount_pending(self):
        return self.total_amount - self.amount_paid

    @property
    def is_fully_paid(self):
        return self.amount_paid >= self.total_amount


class OrderItem(models.Model):
    """Order Line Item"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    
    # Snapshot at time of order
    product_title = models.CharField(max_length=300)
    product_slug = models.CharField(max_length=350)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment option
    payment_option = models.CharField(max_length=10, default='full')  # full or half
    
    # Location
    state = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f"{self.product_title} - {self.order.order_number}"


class OrderFormSubmission(models.Model):
    """Form data submitted for an order item"""
    
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='form_submission')
    form_data = models.JSONField(default=dict)
    form_schema_snapshot = models.JSONField(default=list)  # Schema at time of submission
    uploaded_files = models.JSONField(default=list)
    
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_submissions')
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Form Submission'
        verbose_name_plural = 'Form Submissions'


class OrderStatusHistory(models.Model):
    """Order status change history"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Status History'
        verbose_name_plural = 'Status Histories'
