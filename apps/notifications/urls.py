from django.urls import path
from .views import (
    RegisterTokenView, RemoveTokenView,
    UserNotificationListView, UserUnreadCountView,
    UserMarkReadView, UserMarkAllReadView,
    AdminNotificationListView, AdminUnreadCountView,
    AdminMarkReadView, AdminMarkAllReadView,
    AddOrderNoteView, OrderNotesListView,
    SendToUserView,
)

app_name = 'notifications'

urlpatterns = [

    # ── FCM token ────────────────────────────────────────────────────
    path('register-token/', RegisterTokenView.as_view(), name='register-token'),
    path('remove-token/',   RemoveTokenView.as_view(),   name='remove-token'),

    # ── User ─────────────────────────────────────────────────────────
    path('',                     UserNotificationListView.as_view(), name='user-list'),
    path('unread-count/',        UserUnreadCountView.as_view(),      name='user-unread-count'),
    path('<int:pk>/mark-read/',  UserMarkReadView.as_view(),         name='user-mark-read'),
    path('mark-all-read/',       UserMarkAllReadView.as_view(),      name='user-mark-all-read'),

    # ── Admin ─────────────────────────────────────────────────────────
    path('admin/',                    AdminNotificationListView.as_view(), name='admin-list'),
    path('admin/unread-count/',       AdminUnreadCountView.as_view(),      name='admin-unread-count'),
    path('admin/<int:pk>/mark-read/', AdminMarkReadView.as_view(),         name='admin-mark-read'),
    path('admin/mark-all-read/',      AdminMarkAllReadView.as_view(),      name='admin-mark-all-read'),
    path('admin/send/',               SendToUserView.as_view(),            name='admin-send'),

    # ── Order notes ───────────────────────────────────────────────────
    path('admin/orders/<str:order_id>/add-note/', AddOrderNoteView.as_view(),   name='add-note'),
    path('admin/orders/<str:order_id>/notes/',    OrderNotesListView.as_view(), name='order-notes'),
]
