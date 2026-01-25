"""
CloudServices India - Banner URLs
"""
from django.urls import path
from .views import BannerListView

app_name = 'banner'

urlpatterns = [
    path('', BannerListView.as_view(), name='banner-list'),
]