from django.urls import path
from .views import *

app_name = 'orders'

urlpatterns = [
    path('create/', CreateOrderView.as_view(), name='create'),
    path('', OrderListView.as_view(), name='list'),
    path('<int:pk>/', OrderDetailView.as_view(), name='detail'),
    
    # Admin
    path('admin/', AdminOrderListView.as_view(), name='admin-list'),
    path('admin/<int:pk>/', AdminOrderDetailView.as_view(), name='admin-detail'),
    path('admin/<int:pk>/status/', AdminUpdateOrderStatusView.as_view(), name='admin-status'),
]
