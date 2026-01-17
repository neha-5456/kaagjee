"""
CloudServices India - Account URLs
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterRequestView, RegisterVerifyView,
    LoginRequestView, LoginVerifyView,
    ProfileView, AddressListCreateView, AddressDetailView
)

app_name = 'accounts'

urlpatterns = [
    # Registration Flow
    path('register/request/', RegisterRequestView.as_view(), name='register-request'),
    path('register/verify/', RegisterVerifyView.as_view(), name='register-verify'),
    
    # Login Flow
    path('login/request/', LoginRequestView.as_view(), name='login-request'),
    path('login/verify/', LoginVerifyView.as_view(), name='login-verify'),
    
    # JWT Token
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # Addresses
    path('addresses/', AddressListCreateView.as_view(), name='address-list'),
    path('addresses/<int:pk>/', AddressDetailView.as_view(), name='address-detail'),
]
