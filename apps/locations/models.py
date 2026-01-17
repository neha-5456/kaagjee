"""
CloudServices India - Location Models
=====================================
State and City management for Pan-India services
"""
from django.db import models


class State(models.Model):
    """Indian State Model"""
    
    name = models.CharField(max_length=100)
    # name_hi = models.CharField(max_length=100, blank=True, verbose_name='Name (Hindi)')
    slug = models.SlugField(unique=True)
    code = models.CharField(max_length=5, unique=True, help_text='State code like MH, DL, KA')
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'State'
        verbose_name_plural = 'States'

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def cities_count(self):
        return self.cities.filter(is_active=True).count()


class City(models.Model):
    """Indian City Model"""
    
    class Tier(models.TextChoices):
        TIER_1 = 'tier_1', 'Tier 1 (Metro)'
        TIER_2 = 'tier_2', 'Tier 2'
        TIER_3 = 'tier_3', 'Tier 3'

    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='cities')
    name = models.CharField(max_length=100)
    # name_hi = models.CharField(max_length=100, blank=True, verbose_name='Name (Hindi)')
    slug = models.SlugField()
    tier = models.CharField(max_length=10, choices=Tier.choices, default=Tier.TIER_2)
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ['state', 'slug']
        verbose_name = 'City'
        verbose_name_plural = 'Cities' 

    def __str__(self):
        return f"{self.name}, {self.state.code}"
