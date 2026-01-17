"""
CloudServices India - Location URLs
"""
from django.urls import path
from .views import *

app_name = 'locations'

urlpatterns = [
    path('states/', StateListView.as_view(), name='state-list'),
    path('states/<slug:slug>/', StateDetailView.as_view(), name='state-detail'),
    path('cities/', CityListView.as_view(), name='city-list'),
    path('cities/popular/', PopularCitiesView.as_view(), name='city-popular'),
]
