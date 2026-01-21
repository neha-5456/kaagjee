"""
CloudServices India - Category Models
=====================================
Service categories and subcategories
"""
from django.db import models


class Category(models.Model):
    """Main Category Model"""
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=100, blank=True, help_text='Font Awesome icon class e.g., fa-file-alt')
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

    @property
    def subcategories_count(self):
        return self.subcategories.filter(is_active=True).count()

    @property
    def products_count(self):
        return self.products.filter(status='active').count()


class Subcategory(models.Model):
    """Subcategory Model"""
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=200)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=100, blank=True)
    
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'name']
        unique_together = ['category', 'slug']
        verbose_name = 'Subcategory'
        verbose_name_plural = 'Subcategories'

    def __str__(self):
        return f"{self.category.name} → {self.name}"

    @property
    def products_count(self):
        return self.products.filter(status='active').count()
