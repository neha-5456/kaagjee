"""
Notification Views — all endpoints

USER  (IsAuthenticated)
  POST   /api/notifications/register-token/       register FCM token
  DELETE /api/notifications/remove-token/         remove on logout
  GET    /api/notifications/                      list my notifications
  GET    /api/notifications/unread-count/         unread count
  POST   /api/notifications/<pk>/mark-read/       mark one read
  POST   /api/notifications/mark-all-read/        mark all read

ADMIN (IsAdminUser)
  GET    /api/notifications/admin/                        list admin notifications
  GET    /api/notifications/admin/unread-count/           admin unread count
  POST   /api/notifications/admin/<pk>/mark-read/         mark one read
  POST   /api/notifications/admin/mark-all-read/          mark all read
  POST   /api/notifications/admin/orders/<id>/add-note/   add note → triggers user push
  GET    /api/notifications/admin/orders/<id>/notes/      list notes on an order
  POST   /api/notifications/admin/send/                   custom push to any user
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .models import FCMDevice, UserNotification, AdminNotification
from .serializers import (
    RegisterTokenSerializer, RemoveTokenSerializer,
    UserNotificationSerializer, AdminNotificationSerializer,
    AddOrderNoteSerializer, SendToUserSerializer,
)
from . import firebase


# ─────────────────────────────────────────────────────────────
# FCM TOKEN
# ─────────────────────────────────────────────────────────────

class RegisterTokenView(APIView):
    """
    Save/refresh an FCM token for the logged-in user.
    Call this every time the app starts or Firebase refreshes the token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = RegisterTokenSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        device, created = FCMDevice.objects.update_or_create(
            token=ser.validated_data['token'],
            defaults={
                'user':      request.user,
                'platform':  ser.validated_data['platform'],
                'is_active': True,
            },
        )
        return Response(
            {'success': True, 'message': 'Token registered' if created else 'Token refreshed'},
            status=201 if created else 200,
        )


class RemoveTokenView(APIView):
    """Call on logout or when user revokes push permission."""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        ser = RemoveTokenSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        FCMDevice.objects.filter(
            user=request.user, token=ser.validated_data['token']
        ).update(is_active=False)
        return Response({'success': True, 'message': 'Token removed'})


# ─────────────────────────────────────────────────────────────
# USER NOTIFICATIONS
# ─────────────────────────────────────────────────────────────

class UserNotificationListView(APIView):
    """
    GET /api/notifications/
    Query params: is_read=true|false  type=order_placed|admin_note|...
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = UserNotification.objects.filter(user=request.user)

        if request.query_params.get('is_read') == 'false':
            qs = qs.filter(is_read=False)
        elif request.query_params.get('is_read') == 'true':
            qs = qs.filter(is_read=True)

        if t := request.query_params.get('type'):
            qs = qs.filter(notification_type=t)

        unread = UserNotification.objects.filter(user=request.user, is_read=False).count()
        data   = UserNotificationSerializer(qs[:50], many=True).data

        return Response({'success': True, 'unread_count': unread, 'count': len(data), 'data': data})


class UserUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = UserNotification.objects.filter(user=request.user, is_read=False).count()
        return Response({'success': True, 'unread_count': count})


class UserMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        n = get_object_or_404(UserNotification, pk=pk, user=request.user)
        n.is_read = True
        n.read_at = timezone.now()
        n.save(update_fields=['is_read', 'read_at'])
        return Response({'success': True})


class UserMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = UserNotification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return Response({'success': True, 'updated': count})


# ─────────────────────────────────────────────────────────────
# ADMIN NOTIFICATIONS
# ─────────────────────────────────────────────────────────────

class AdminNotificationListView(APIView):
    """
    GET /api/notifications/admin/
    Query params: is_read=true|false  type=new_order|payment_success|...
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = AdminNotification.objects.all()

        if request.query_params.get('is_read') == 'false':
            qs = qs.filter(is_read=False)
        elif request.query_params.get('is_read') == 'true':
            qs = qs.filter(is_read=True)

        if t := request.query_params.get('type'):
            qs = qs.filter(notification_type=t)

        unread = AdminNotification.objects.filter(is_read=False).count()
        data   = AdminNotificationSerializer(qs[:50], many=True).data

        return Response({'success': True, 'unread_count': unread, 'count': len(data), 'data': data})


class AdminUnreadCountView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        count = AdminNotification.objects.filter(is_read=False).count()
        return Response({'success': True, 'unread_count': count})


class AdminMarkReadView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        n = get_object_or_404(AdminNotification, pk=pk)
        n.is_read = True
        n.read_at = timezone.now()
        n.save(update_fields=['is_read', 'read_at'])
        return Response({'success': True})


class AdminMarkAllReadView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        count = AdminNotification.objects.filter(is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({'success': True, 'updated': count})


# ─────────────────────────────────────────────────────────────
# ORDER NOTES (admin → user push)
# ─────────────────────────────────────────────────────────────

class AddOrderNoteView(APIView):
    """
    Admin adds a note to an order.
    notify_user=True (default) → UserNotification + Firebase push sent to user.
    is_internal=True            → only visible to admin, no push.

    POST /api/notifications/admin/orders/<order_id>/add-note/
    Body: { "note": "...", "is_internal": false, "notify_user": true }
    """
    permission_classes = [IsAdminUser]

    def post(self, request, order_id):
        from apps.orders.models import Order, OrderNote

        order = get_object_or_404(Order, order_id=order_id)
        ser   = AddOrderNoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        note_obj = OrderNote.objects.create(
            order       = order,
            added_by    = request.user,
            note        = ser.validated_data['note'],
            is_internal = ser.validated_data['is_internal'],
            notify_user = ser.validated_data['notify_user'],
        )

        user_notified = False
        if ser.validated_data['notify_user'] and not ser.validated_data['is_internal']:
            u = UserNotification.objects.create(
                user=order.user,
                notification_type=UserNotification.Type.ADMIN_NOTE,
                title=f'Update on your order {order_id}',
                message=ser.validated_data['note'],
                order_id=order_id,
            )
            firebase.push_to_user(
                user=order.user,
                title=f'📋 Update on Order {order_id}',
                body=ser.validated_data['note'][:100],
                data={'type': 'admin_note', 'order_id': order_id},
                notif_obj=u,
            )
            user_notified = True

        return Response({
            'success':       True,
            'message':       'Note added',
            'user_notified': user_notified,
            'note_id':       note_obj.id,
        }, status=201)


class OrderNotesListView(APIView):
    """GET /api/notifications/admin/orders/<order_id>/notes/"""
    permission_classes = [IsAdminUser]

    def get(self, request, order_id):
        from apps.orders.models import Order, OrderNote
        order = get_object_or_404(Order, order_id=order_id)
        notes = OrderNote.objects.filter(order=order).select_related('added_by')
        data  = [
            {
                'id':          n.id,
                'note':        n.note,
                'is_internal': n.is_internal,
                'notify_user': n.notify_user,
                'added_by':    str(n.added_by) if n.added_by else 'Admin',
                'created_at':  n.created_at,
            }
            for n in notes
        ]
        return Response({'success': True, 'count': len(data), 'data': data})


# ─────────────────────────────────────────────────────────────
# CUSTOM PUSH (admin → any user)
# ─────────────────────────────────────────────────────────────

class SendToUserView(APIView):
    """
    Admin sends a custom push notification to any user.

    POST /api/notifications/admin/send/
    Body: { "user_id": 5, "title": "Hello", "message": "Your doc is ready" }
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        from django.contrib.auth import get_user_model
        ser = SendToUserSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        User = get_user_model()
        user = get_object_or_404(User, pk=ser.validated_data['user_id'])

        notif = UserNotification.objects.create(
            user=user,
            notification_type=UserNotification.Type.GENERAL,
            title=ser.validated_data['title'],
            message=ser.validated_data['message'],
        )
        firebase.push_to_user(
            user=user,
            title=ser.validated_data['title'],
            body=ser.validated_data['message'][:100],
            data={'type': 'general'},
            notif_obj=notif,
        )
        return Response({'success': True, 'message': 'Notification sent', 'notif_id': notif.id})
