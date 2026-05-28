"""
CloudServices India - Products URLs
===================================
"""
from django.urls import path
from .views import (
    PolicyAPIView, 
)
app_name = 'policy'

urlpatterns = [

    path('', PolicyAPIView.as_view(), name='policy-list'),
    
   
]