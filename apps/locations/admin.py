"""
CloudServices India - Locations Admin
"""
from django.contrib import admin
from .models import State, City


class CityInline(admin.TabularInline):
    model = City
    extra = 3
    prepopulated_fields = {'slug': ('name',)}
    fields = ['name',  'slug', 'tier', 'is_popular', 'is_active']


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'cities_count', 'is_active', 'display_order']
    list_filter = ['is_active']
    list_editable = ['is_active', 'display_order']
    search_fields = ['name', 'code']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CityInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'code')
        }),
        ('Settings', {
            'fields': ('is_active', 'display_order')
        }),
    )


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'state', 'tier', 'is_popular', 'is_active']
    list_filter = ['state', 'tier', 'is_popular', 'is_active']
    list_editable = ['tier', 'is_popular', 'is_active']
    search_fields = ['name', 'state__name']
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['state']
