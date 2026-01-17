"""
CloudServices India - Product Models
====================================
Products/Services with Dynamic Form Builder
"""
from django.db import models
from apps.categories.models import Category, Subcategory
from apps.locations.models import State, City


class Product(models.Model):
    """Product/Service Model with Dynamic Form Schema"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        COMING_SOON = 'coming_soon', 'Coming Soon'

    # ========================
    # BASIC INFO
    # ========================
    title = models.CharField(max_length=300, verbose_name='Product Title')
    slug = models.SlugField(unique=True, max_length=350)
    short_description = models.CharField(max_length=500, blank=True, verbose_name='Short Description')
    description = models.TextField(blank=True, verbose_name='Full Description', 
                                   help_text='Supports HTML formatting')
    featured_image = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name='Featured Image')
    youtube_link = models.URLField(blank=True, verbose_name='YouTube Video Link')

    # ========================
    # CATEGORY
    # ========================
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products',
                                 verbose_name='Category')
    subcategory = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='products', verbose_name='Subcategory')

    # ========================
    # LOCATION AVAILABILITY
    # ========================
    is_pan_india = models.BooleanField(default=True, verbose_name='Available All India',
                                       help_text='If checked, available in all states/cities')
    available_states = models.ManyToManyField(State, blank=True, related_name='products',
                                              verbose_name='Available States ')
    available_cities = models.ManyToManyField(City, blank=True, related_name='products',
                                              verbose_name='Available Cities')

    # ========================
    # PRICING
    # ========================
    full_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Full Price')
    half_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                     verbose_name='Partial Price')
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                         verbose_name='Original Price (for discount display)')
    allow_half_payment = models.BooleanField(default=True, verbose_name='Allow 50% Advance')

    # ========================
    # FORM BUILDER (JSON)
    # ========================
    form_title = models.CharField(max_length=200, default='Application Form', 
                                  verbose_name='Form Title ')
    form_description = models.CharField(max_length=500, blank=True, 
                                        verbose_name='Form Description')
    form_schema = models.JSONField(default=list, blank=True, verbose_name='Form Fields (JSON)',
                                   help_text='DO NOT EDIT MANUALLY - Use Visual Form Builder below')

    # ========================
    # STATUS & FLAGS
    # ========================
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT,
                              verbose_name='Status')
    is_featured = models.BooleanField(default=False, verbose_name='Featured')
    is_popular = models.BooleanField(default=False, verbose_name='Popular')

    # ========================
    # SEO
    # ========================
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=500, blank=True)

    # ========================
    # ADDITIONAL INFO
    # ========================
    processing_time = models.CharField(max_length=100, blank=True, 
                                       verbose_name='Processing Time',
                                       help_text='e.g., 3-5 working days')
    documents_required = models.TextField(blank=True, verbose_name='Documents Required')

    # ========================
    # STATS
    # ========================
    orders_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)

    # ========================
    # TIMESTAMPS
    # ========================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-calculate half price if not set
        if self.allow_half_payment and not self.half_price and self.full_price:
            self.half_price = self.full_price / 2
        super().save(*args, **kwargs)

    @property
    def form_fields_count(self):
        """Number of form fields"""
        if self.form_schema and isinstance(self.form_schema, list):
            return len(self.form_schema)
        return 0

    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.original_price and self.full_price < self.original_price:
            return int(((self.original_price - self.full_price) / self.original_price) * 100)
        return 0


class ProductImage(models.Model):
    """Product Gallery Images"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')
    alt_text = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order']
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'

    def __str__(self):
        return f"{self.product.title} - Image {self.display_order}"


class ProductFAQ(models.Model):
    """Product FAQs"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=500)
    answer = models.TextField()
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']
        verbose_name = 'Product FAQ'
        verbose_name_plural = 'Product FAQs'

    def __str__(self):
        return f"{self.product.title} - {self.question[:50]}"
