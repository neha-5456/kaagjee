"""
CloudServices India - Banner Models
"""
from django.db import models


class Banner(models.Model):
    """Simple Banner Model for mobile app"""
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='banners/')
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Banner'
        verbose_name_plural = 'Banners'

    def __str__(self):
        return self.title