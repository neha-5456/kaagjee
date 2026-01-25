"""
Kaagjee - Orders, Cart & Payment Models
=======================================
- FormSubmission: User's filled product form
- Cart & CartItem: Shopping cart
- Order & OrderItem: Orders with payment tracking
- Payment: Razorpay payment records
"""
from django.db import models
from django.conf import settings
from apps.products.models import Product
import uuid


class FormSubmission(models.Model):
    """
    Stores user's filled form data for a product
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SUBMITTED = 'submitted', 'Submitted'
        IN_CART = 'in_cart', 'In Cart'
        ORDERED = 'ordered', 'Ordered'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    submission_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # User (required - only logged in users)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='form_submissions'
    )
    
    # Product
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='submissions'
    )
    
    # Form data (JSON)
    form_data = models.JSONField(default=dict)
    uploaded_files = models.JSONField(default=dict, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    
    # Price at submission
    price_at_submission = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Notes
    user_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Form Submission'
        verbose_name_plural = 'Form Submissions'
    
    def __str__(self):
        return f"{self.product.title} - {self.user.phone_number} ({self.submission_id})"
    
    def save(self, *args, **kwargs):
        if not self.price_at_submission:
            self.price_at_submission = self.product.full_price
        super().save(*args, **kwargs)


class Cart(models.Model):
    """Shopping Cart - One per user"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart - {self.user.phone_number}"
    
    @property
    def total_items(self):
        return self.items.count()
    
    @property
    def total_amount(self):
        return sum(item.unit_price for item in self.items.all())


class CartItem(models.Model):
    """Cart Item - Links to FormSubmission"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    form_submission = models.OneToOneField(
        FormSubmission,
        on_delete=models.CASCADE,
        related_name='cart_item'
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.product.title} in {self.cart}"
    
    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.full_price
        super().save(*args, **kwargs)


class Order(models.Model):
    """Order with Payment Tracking"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Payment Pending'
        PARTIAL_PAID = 'partial_paid', 'Partially Paid (50%)'
        PAID = 'paid', 'Fully Paid'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'
    
    class PaymentType(models.TextChoices):
        FULL = 'full', 'Full Payment'
        HALF = 'half', 'Half Payment (50% Advance)'
    
    # Order ID
    order_id = models.CharField(max_length=50, unique=True, editable=False)
    
    # User
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    
    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Payment Type
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.FULL)
    
    # Amounts
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total Order Amount')
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Amount Paid')
    pending_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Pending Amount')
    
    # First payment (advance)
    first_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    first_payment_date = models.DateTimeField(null=True, blank=True)
    
    # Second payment (remaining)
    second_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    second_payment_date = models.DateTimeField(null=True, blank=True)
    second_payment_due_date = models.DateField(null=True, blank=True)
    
    # User details at order time
    user_name = models.CharField(max_length=200)
    user_email = models.EmailField(blank=True)
    user_phone = models.CharField(max_length=20)
    
    # Notes
    user_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
    
    def __str__(self):
        return f"Order {self.order_id} - {self.user.phone_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            # Generate order ID: KJ-YYYYMMDD-XXXXX
            import datetime
            import random
            date_str = datetime.datetime.now().strftime('%Y%m%d')
            random_str = ''.join([str(random.randint(0, 9)) for _ in range(5)])
            self.order_id = f"KJ-{date_str}-{random_str}"
        
        # Calculate pending amount
        self.pending_amount = self.total_amount - self.paid_amount
        
        # Update status based on payment
        if self.paid_amount >= self.total_amount:
            if self.status not in [self.Status.PROCESSING, self.Status.COMPLETED, self.Status.CANCELLED]:
                self.status = self.Status.PAID
        elif self.paid_amount > 0:
            if self.status == self.Status.PENDING:
                self.status = self.Status.PARTIAL_PAID
        
        super().save(*args, **kwargs)
    
    @property
    def is_fully_paid(self):
        return self.paid_amount >= self.total_amount
    
    @property
    def has_pending_payment(self):
        return self.pending_amount > 0


class OrderItem(models.Model):
    """Individual item in an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    form_submission = models.OneToOneField(
        FormSubmission,
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_item'
    )
    
    # Snapshot at order time
    product_title = models.CharField(max_length=300)
    product_slug = models.SlugField(max_length=350)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Form data copy
    form_data = models.JSONField(default=dict)
    uploaded_files = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def __str__(self):
        return f"{self.product_title} - {self.order.order_id}"


class Payment(models.Model):
    """Razorpay Payment Records"""
    
    class Status(models.TextChoices):
        CREATED = 'created', 'Created'
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
    
    class PaymentFor(models.TextChoices):
        FIRST = 'first', 'First Payment (Advance)'
        SECOND = 'second', 'Second Payment (Remaining)'
        FULL = 'full', 'Full Payment'
    
    # Payment ID
    payment_id = models.CharField(max_length=100, unique=True, editable=False)
    
    # Order reference
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    
    # Payment for
    payment_for = models.CharField(max_length=20, choices=PaymentFor.choices, default=PaymentFor.FULL)
    
    # Amount
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    
    # Razorpay fields
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=500, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)
    
    # Response data
    razorpay_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
    
    def __str__(self):
        return f"Payment {self.payment_id} - ₹{self.amount} - {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.payment_id:
            self.payment_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)
