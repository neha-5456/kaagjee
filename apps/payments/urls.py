from django.urls import path
from .views import *

app_name = 'payments'

urlpatterns = [
    path('initiate/', InitiatePaymentView.as_view(), name='initiate'),
    path('verify/', VerifyPaymentView.as_view(), name='verify'),
    path('', PaymentListView.as_view(), name='list'),
    path('<str:payment_id>/', PaymentDetailView.as_view(), name='detail'),
    path('admin/', AdminPaymentListView.as_view(), name='admin-list'),
]
