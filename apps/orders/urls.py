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
    path('submissions/<uuid:submission_id>/', views.SubmissionDetailView.as_view(), name='submission-detail'),
    
    path('upload-file/', views.FileUploadView.as_view(), name='upload-file'),
    path('upload-files/', views.MultipleFilesUploadView.as_view(), name='upload-files'),
    path('delete-file/', views.DeleteUploadedFileView.as_view(), name='delete-file'),
    path('generate-pdf/', views.GeneratePDFView.as_view(), name='generate-pdf'),
    
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

    # ========================
    # ORDER TASKS
    # ========================
    path('admin/tasks/', views.OrderTaskListCreateView.as_view(), name='order-task-list-create'),
    path('admin/tasks/<int:task_id>/', views.OrderTaskDetailView.as_view(), name='order-task-detail'),
    path('admin/tasks/<int:task_id>/<str:action>/', views.OrderTaskApprovalView.as_view(), name='order-task-approval'),
    path('admin/all-assigned-tasks/', views.SuperAdminAssignedTasksView.as_view(), name='super-admin-assigned-tasks'),
    path('admin/orders-with-tasks/', views.OrdersWithAssignedTasksView.as_view(), name='orders-with-tasks'),
    path('admin/tasks/assigned/', views.AssignedTaskListView.as_view(), name='assigned-task-list'),
    path('tasks/<int:task_id>/', views.AssignedTaskDetailView.as_view(), name='assigned-task-detail'),
    path('tasks/<int:task_id>/complete/', views.AssignedTaskCompleteView.as_view(), name='assigned-task-complete'),

    # Mobile app friendly endpoints
    path('mobile/tasks/', views.MobileAssignedTaskListView.as_view(), name='mobile-task-list'),
    path('mobile/tasks/<int:task_id>/submit/', views.MobileTaskSubmitView.as_view(), name='mobile-task-submit'),
]
