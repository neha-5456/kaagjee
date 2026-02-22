"""
Notification Views - Admin API
"""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils import timezone
from .models import AdminNotification
from .serializers import AdminNotificationSerializer


class AdminNotificationListView(generics.ListAPIView):
    """List all admin notifications"""
    permission_classes = [IsAdminUser]
    serializer_class = AdminNotificationSerializer
    
    def get_queryset(self):
        qs = AdminNotification.objects.all()
        
        # Filter by read/unread
        is_read = self.request.query_params.get('is_read')
        if is_read == 'false':
            qs = qs.filter(is_read=False)
        elif is_read == 'true':
            qs = qs.filter(is_read=True)
        
        # Filter by type
        notification_type = self.request.query_params.get('type')
        if notification_type:
            qs = qs.filter(notification_type=notification_type)
        
        return qs[:50]  # Limit to 50 recent notifications
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        unread_count = AdminNotification.objects.filter(is_read=False).count()
        
        return Response({
            'success': True,
            'unread_count': unread_count,
            'count': len(serializer.data),
            'data': serializer.data
        })


class MarkNotificationReadView(APIView):
    """Mark notification as read"""
    permission_classes = [IsAdminUser]
    
    def post(self, request, pk):
        try:
            notification = AdminNotification.objects.get(pk=pk)
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
            
            return Response({
                'success': True,
                'message': 'Notification marked as read'
            })
        except AdminNotification.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Notification not found'
            }, status=404)


class MarkAllNotificationsReadView(APIView):
    """Mark all notifications as read"""
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        count = AdminNotification.objects.filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return Response({
            'success': True,
            'message': f'{count} notifications marked as read'
        })


class UnreadNotificationCountView(APIView):
    """Get unread notification count"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        count = AdminNotification.objects.filter(is_read=False).count()
        
        return Response({
            'success': True,
            'unread_count': count
        })
