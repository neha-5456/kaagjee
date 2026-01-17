"""
CloudServices India - Payment Views
"""
from rest_framework import serializers, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import Payment
from apps.orders.models import Order
import razorpay


def get_razorpay_client():
    """Get Razorpay client"""
    key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
    if key_id and key_secret:
        return razorpay.Client(auth=(key_id, key_secret))
    return None


# ========================
# SERIALIZERS
# ========================

class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'payment_id', 'order', 'order_number', 'amount', 'currency',
                  'payment_type', 'status', 'razorpay_payment_id', 'created_at', 'completed_at']


class InitiatePaymentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    payment_type = serializers.ChoiceField(choices=['full', 'half', 'remaining'])


# ========================
# VIEWS
# ========================

class InitiatePaymentView(APIView):
    """Initiate payment - creates Razorpay order"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order_id = serializer.validated_data['order_id']
        payment_type = serializer.validated_data['payment_type']
        
        # Get order
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'success': False, 'error': 'Order not found'}, status=404)
        
        # Calculate amount
        if payment_type == 'remaining':
            amount = order.amount_pending
        elif payment_type == 'half':
            amount = order.total_amount / 2
        else:
            amount = order.total_amount - order.amount_paid
        
        if amount <= 0:
            return Response({'success': False, 'error': 'Invalid amount'}, status=400)
        
        # Get Razorpay client
        client = get_razorpay_client()
        if not client:
            # For development without Razorpay
            payment = Payment.objects.create(
                order=order,
                user=request.user,
                amount=amount,
                payment_type=payment_type,
                razorpay_order_id='dev_' + str(order.id)
            )
            return Response({
                'success': True,
                'data': {
                    'payment_id': payment.payment_id,
                    'amount': float(amount),
                    'currency': 'INR',
                    'order_number': order.order_number,
                    'dev_mode': True,
                    'message': 'Razorpay not configured. Use verify endpoint with any values.'
                }
            })
        
        # Create Razorpay order
        try:
            razorpay_order = client.order.create({
                'amount': int(amount * 100),  # In paise
                'currency': 'INR',
                'receipt': order.order_number
            })
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=500)
        
        # Create payment record
        payment = Payment.objects.create(
            order=order,
            user=request.user,
            amount=amount,
            payment_type=payment_type,
            razorpay_order_id=razorpay_order['id']
        )
        
        return Response({
            'success': True,
            'data': {
                'payment_id': payment.payment_id,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'amount': int(amount * 100),
                'currency': 'INR',
                'order_number': order.order_number
            }
        })


class VerifyPaymentView(APIView):
    """Verify payment after Razorpay callback"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        payment_id = request.data.get('payment_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id', '')
        razorpay_signature = request.data.get('razorpay_signature', '')
        
        # Get payment
        try:
            payment = Payment.objects.get(payment_id=payment_id, user=request.user)
        except Payment.DoesNotExist:
            return Response({'success': False, 'error': 'Payment not found'}, status=404)
        
        if payment.status == Payment.Status.SUCCESS:
            return Response({'success': True, 'message': 'Payment already verified'})
        
        # Verify signature (skip in dev mode)
        client = get_razorpay_client()
        if client and razorpay_signature:
            try:
                client.utility.verify_payment_signature({
                    'razorpay_order_id': payment.razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_signature': razorpay_signature
                })
            except:
                payment.status = Payment.Status.FAILED
                payment.failure_reason = 'Signature verification failed'
                payment.save()
                return Response({'success': False, 'error': 'Payment verification failed'}, status=400)
        
        # Update payment
        payment.status = Payment.Status.SUCCESS
        payment.razorpay_payment_id = razorpay_payment_id or 'dev_payment'
        payment.razorpay_signature = razorpay_signature
        payment.completed_at = timezone.now()
        payment.save()
        
        # Update order
        order = payment.order
        order.amount_paid += payment.amount
        
        if order.amount_paid >= order.total_amount:
            order.status = Order.Status.PAID
            order.paid_at = timezone.now()
        else:
            order.status = Order.Status.PARTIALLY_PAID
        
        order.save()
        
        return Response({
            'success': True,
            'message': 'Payment verified successfully',
            'data': PaymentSerializer(payment).data
        })


class PaymentListView(generics.ListAPIView):
    """List user's payments"""
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).select_related('order')


class PaymentDetailView(generics.RetrieveAPIView):
    """Get payment detail"""
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer
    lookup_field = 'payment_id'

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)


# Admin
class AdminPaymentListView(generics.ListAPIView):
    """Admin: List all payments"""
    permission_classes = [IsAdminUser]
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all().select_related('order', 'user')
