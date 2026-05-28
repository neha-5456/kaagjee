"""
CloudServices India - Products URLs
===================================
"""
from django.urls import path
from .views import (
    PrivacyAPIView, 
)
app_name = 'privacy'

urlpatterns = [

    path('', PrivacyAPIView.as_view(), name='privacy-list'),
    
   
]