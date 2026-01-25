"""
Kaagjee - Orders & Payment URLs
===============================
"""
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # ========================
    # FORM SUBMISSION
    # ========================
    path('submit-form/', views.SubmitFormView.as_view(), name='submit-form'),
    path('submit-form-files/', views.SubmitFormWithFilesView.as_view(), name='submit-form-files'),
    path('my-submissions/', views.MySubmissionsView.as_view(), name='my-submissions'),
    
    # ========================
    # CART
    # ========================
    path('cart/', views.GetCartView.as_view(), name='cart'),
    path('cart/count/', views.CartCountView.as_view(), name='cart-count'),
    path('cart/item/<int:item_id>/remove/', views.RemoveFromCartView.as_view(), name='cart-remove'),
    path('cart/clear/', views.ClearCartView.as_view(), name='cart-clear'),
    
    # ========================
    # CHECKOUT & PAYMENT
    # ========================
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('verify-payment/', views.VerifyPaymentView.as_view(), name='verify-payment'),
    
    # ========================
    # ORDERS
    # ========================
    path('my-orders/', views.MyOrdersView.as_view(), name='my-orders'),
    path('pending-payments/', views.PendingPaymentsView.as_view(), name='pending-payments'),
    path('<str:order_id>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('<str:order_id>/pay-pending/', views.PayPendingAmountView.as_view(), name='pay-pending'),
]
