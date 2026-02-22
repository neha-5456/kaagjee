"""
Notification URLs
"""
from django.urls import path
from .views import (
    AdminNotificationListView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
    UnreadNotificationCountView
)

app_name = 'notifications'

urlpatterns = [
    path('', AdminNotificationListView.as_view(), name='list'),
    path('unread-count/', UnreadNotificationCountView.as_view(), name='unread-count'),
    path('<int:pk>/mark-read/', MarkNotificationReadView.as_view(), name='mark-read'),
    path('mark-all-read/', MarkAllNotificationsReadView.as_view(), name='mark-all-read'),
]
