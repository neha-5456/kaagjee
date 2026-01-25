"""
Kaagjee - Orders, Cart & Payment APIs
=====================================
Complete flow:
1. Submit Form → Add to Cart
2. Checkout → Create Order → Razorpay Payment
3. Half Payment → Pay Remaining from Orders
"""
from rest_framework import serializers, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import razorpay
import hmac
import hashlib

from .models import FormSubmission, Cart, CartItem, Order, OrderItem, Payment
from apps.products.models import Product


# ========================
# RAZORPAY CLIENT
# ========================
def get_razorpay_client():
    """Get Razorpay client instance"""
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# ========================
# SERIALIZERS
# ========================

class FormSubmissionSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    product_image = serializers.ImageField(source='product.featured_image', read_only=True)
    
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'submission_id', 'product', 'product_title', 'product_slug', 
            'product_image', 'form_data', 'uploaded_files', 'status',
            'price_at_submission', 'user_notes', 'created_at'
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    product_image = serializers.ImageField(source='product.featured_image', read_only=True)
    full_price = serializers.DecimalField(source='product.full_price', max_digits=10, decimal_places=2, read_only=True)
    half_price = serializers.DecimalField(source='product.half_price', max_digits=10, decimal_places=2, read_only=True)
    allow_half_payment = serializers.BooleanField(source='product.allow_half_payment', read_only=True)
    submission_id = serializers.UUIDField(source='form_submission.submission_id', read_only=True)
    form_data = serializers.JSONField(source='form_submission.form_data', read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product_id', 'product_title', 'product_slug', 'product_image',
            'full_price', 'half_price', 'allow_half_payment', 'unit_price',
            'submission_id', 'form_data', 'added_at'
        ]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'total_items', 'total_amount', 'items']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_title', 'product_slug', 'unit_price',
            'form_data', 'uploaded_files', 'created_at'
        ]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'payment_id', 'payment_for', 'amount', 'currency',
            'razorpay_order_id', 'razorpay_payment_id', 'status',
            'created_at', 'paid_at'
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'status', 'status_display', 'payment_type', 'payment_type_display',
            'total_amount', 'paid_amount', 'pending_amount',
            'first_payment_amount', 'first_payment_date',
            'second_payment_amount', 'second_payment_date', 'second_payment_due_date',
            'user_name', 'user_email', 'user_phone', 'user_notes',
            'items', 'payments', 'created_at', 'updated_at'
        ]


class OrderListSerializer(serializers.ModelSerializer):
    """Simplified order list"""
    items_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    has_pending_payment = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'status', 'status_display', 'payment_type',
            'total_amount', 'paid_amount', 'pending_amount',
            'has_pending_payment', 'items_count', 'created_at'
        ]
    
    def get_items_count(self, obj):
        return obj.items.count()


# ========================
# HELPER FUNCTIONS
# ========================

def get_or_create_cart(user):
    """Get or create cart for authenticated user"""
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


# ========================
# FORM SUBMISSION APIs
# ========================

class SubmitFormView(APIView):
    """
    Submit product form and add to cart
    
    POST /api/orders/submit-form/
    
    Body:
    {
        "product_id": 1,
        "form_data": {"name": "John", "phone": "9876543210"},
        "user_notes": "Optional notes"
    }
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        product_id = request.data.get('product_id')
        product_slug = request.data.get('product_slug')
        form_data = request.data.get('form_data', {})
        user_notes = request.data.get('user_notes', '')
        
        # Get product
        try:
            if product_id:
                product = Product.objects.get(id=product_id, status=Product.Status.ACTIVE)
            elif product_slug:
                product = Product.objects.get(slug=product_slug, status=Product.Status.ACTIVE)
            else:
                return Response({
                    'success': False,
                    'error': 'product_id or product_slug required'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validate required fields from form_schema
        errors = []
        for field in (product.form_schema or []):
            if field.get('required') and field.get('name'):
                if field['name'] not in form_data or not form_data[field['name']]:
                    errors.append(f"{field.get('label', field['name'])} is required")
        
        if errors:
            return Response({
                'success': False,
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create submission
        submission = FormSubmission.objects.create(
            user=request.user,
            product=product,
            form_data=form_data,
            price_at_submission=product.full_price,
            user_notes=user_notes,
            status=FormSubmission.Status.IN_CART
        )
        
        # Add to cart
        cart = get_or_create_cart(request.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            product=product,
            form_submission=submission,
            unit_price=product.full_price
        )
        
        return Response({
            'success': True,
            'message': 'Form submitted and added to cart',
            'data': {
                'submission': FormSubmissionSerializer(submission).data,
                'cart_item_id': cart_item.id,
                'cart_total': cart.total_amount,
                'cart_items_count': cart.total_items
            }
        }, status=status.HTTP_201_CREATED)


class SubmitFormWithFilesView(APIView):
    """Submit form with file uploads"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @transaction.atomic
    def post(self, request):
        import json
        import os
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        import uuid as uuid_lib
        
        product_id = request.data.get('product_id')
        
        try:
            product = Product.objects.get(id=product_id, status=Product.Status.ACTIVE)
        except Product.DoesNotExist:
            return Response({'success': False, 'error': 'Product not found'}, status=404)
        
        # Parse form_data
        try:
            form_data = json.loads(request.data.get('form_data', '{}'))
        except:
            form_data = {}
        
        # Handle files
        uploaded_files = {}
        submission_uuid = uuid_lib.uuid4().hex[:12]
        
        for key, file in request.FILES.items():
            if key.startswith('file_'):
                field_name = key[5:]
                ext = os.path.splitext(file.name)[1]
                filename = f"{submission_uuid}_{field_name}{ext}"
                path = f"submissions/{product.slug}/{filename}"
                saved_path = default_storage.save(path, ContentFile(file.read()))
                uploaded_files[field_name] = saved_path
                form_data[field_name] = saved_path
        
        # Create submission
        submission = FormSubmission.objects.create(
            user=request.user,
            product=product,
            form_data=form_data,
            uploaded_files=uploaded_files,
            price_at_submission=product.full_price,
            status=FormSubmission.Status.IN_CART
        )
        
        # Add to cart
        cart = get_or_create_cart(request.user)
        CartItem.objects.create(
            cart=cart,
            product=product,
            form_submission=submission,
            unit_price=product.full_price
        )
        
        return Response({
            'success': True,
            'message': 'Form submitted with files',
            'data': {
                'submission': FormSubmissionSerializer(submission).data,
                'cart_items_count': cart.total_items
            }
        }, status=201)


# ========================
# CART APIs
# ========================

class GetCartView(APIView):
    """Get user's cart"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        cart = get_or_create_cart(request.user)
        return Response({
            'success': True,
            'data': CartSerializer(cart).data
        })


class CartCountView(APIView):
    """Get cart count for header badge"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        cart = get_or_create_cart(request.user)
        return Response({
            'success': True,
            'data': {
                'count': cart.total_items,
                'total': cart.total_amount
            }
        })


class RemoveFromCartView(APIView):
    """Remove item from cart"""
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def delete(self, request, item_id):
        cart = get_or_create_cart(request.user)
        
        try:
            cart_item = cart.items.get(id=item_id)
        except CartItem.DoesNotExist:
            return Response({'success': False, 'error': 'Item not found'}, status=404)
        
        # Update submission status
        submission = cart_item.form_submission
        submission.status = FormSubmission.Status.SUBMITTED
        submission.save()
        
        cart_item.delete()
        
        return Response({
            'success': True,
            'message': 'Removed from cart',
            'data': {
                'cart_items_count': cart.total_items,
                'cart_total': cart.total_amount
            }
        })


class ClearCartView(APIView):
    """Clear all cart items"""
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def delete(self, request):
        cart = get_or_create_cart(request.user)
        
        for item in cart.items.all():
            item.form_submission.status = FormSubmission.Status.SUBMITTED
            item.form_submission.save()
        
        cart.items.all().delete()
        
        return Response({
            'success': True,
            'message': 'Cart cleared'
        })


# ========================
# CHECKOUT & ORDER APIs
# ========================

class CheckoutView(APIView):
    """
    Create order from cart and initiate Razorpay payment
    
    POST /api/orders/checkout/
    
    Body:
    {
        "payment_type": "full" or "half",
        "user_name": "John Doe",
        "user_email": "john@example.com",
        "user_phone": "9876543210",
        "user_notes": "Optional"
    }
    
    Response includes Razorpay order details for frontend payment
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        cart = get_or_create_cart(request.user)
        
        # Check cart not empty
        if cart.total_items == 0:
            return Response({
                'success': False,
                'error': 'Cart is empty'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        payment_type = request.data.get('payment_type', 'full')
        user_name = request.data.get('user_name', getattr(request.user, 'full_name', ''))
        user_email = request.data.get('user_email', getattr(request.user, 'email', ''))
        user_phone = request.data.get('user_phone', str(request.user.phone))
        user_notes = request.data.get('user_notes', '')
        
        # Validate payment type
        if payment_type not in ['full', 'half']:
            return Response({
                'success': False,
                'error': 'Invalid payment_type. Use "full" or "half"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if half payment is allowed for all items
        if payment_type == 'half':
            for item in cart.items.all():
                if not item.product.allow_half_payment:
                    return Response({
                        'success': False,
                        'error': f'Half payment not allowed for: {item.product.title}'
                    }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate amounts
        total_amount = cart.total_amount
        
        if payment_type == 'half':
            first_payment = total_amount / 2
            second_payment = total_amount - first_payment
        else:
            first_payment = total_amount
            second_payment = 0
        
        # Create Order
        order = Order.objects.create(
            user=request.user,
            payment_type=payment_type,
            total_amount=total_amount,
            first_payment_amount=first_payment,
            second_payment_amount=second_payment,
            user_name=user_name,
            user_email=user_email,
            user_phone=user_phone,
            user_notes=user_notes,
            second_payment_due_date=timezone.now().date() + timedelta(days=7) if payment_type == 'half' else None
        )
        
        # Create Order Items from Cart
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                form_submission=cart_item.form_submission,
                product_title=cart_item.product.title,
                product_slug=cart_item.product.slug,
                unit_price=cart_item.unit_price,
                form_data=cart_item.form_submission.form_data,
                uploaded_files=cart_item.form_submission.uploaded_files
            )
            # Update submission status
            cart_item.form_submission.status = FormSubmission.Status.ORDERED
            cart_item.form_submission.save()
        
        # Clear cart
        cart.items.all().delete()
        
        # Create Razorpay order
        try:
            client = get_razorpay_client()
            razorpay_order = client.order.create({
                'amount': int(first_payment * 100),  # Razorpay accepts amount in paise
                'currency': 'INR',
                'receipt': order.order_id,
                'notes': {
                    'order_id': order.order_id,
                    'payment_for': 'first' if payment_type == 'half' else 'full',
                    'user_phone': user_phone
                }
            })
        except Exception as e:
            # Rollback order if Razorpay fails
            order.delete()
            return Response({
                'success': False,
                'error': f'Payment gateway error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create Payment record
        payment = Payment.objects.create(
            order=order,
            user=request.user,
            payment_for='first' if payment_type == 'half' else 'full',
            amount=first_payment,
            razorpay_order_id=razorpay_order['id'],
            status=Payment.Status.CREATED
        )
        
        return Response({
            'success': True,
            'message': 'Order created. Complete payment.',
            'data': {
                'order': OrderSerializer(order).data,
                'payment': {
                    'payment_id': payment.payment_id,
                    'amount': float(first_payment),
                    'currency': 'INR',
                    'razorpay_order_id': razorpay_order['id'],
                    'razorpay_key': settings.RAZORPAY_KEY_ID,
                    'user_name': user_name,
                    'user_email': user_email,
                    'user_phone': user_phone,
                    'description': f'Payment for Order {order.order_id}'
                }
            }
        }, status=status.HTTP_201_CREATED)


class VerifyPaymentView(APIView):
    """
    Verify Razorpay payment after frontend completes payment
    
    POST /api/orders/verify-payment/
    
    Body:
    {
        "razorpay_order_id": "order_xxx",
        "razorpay_payment_id": "pay_xxx",
        "razorpay_signature": "signature_xxx"
    }
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')
        
        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return Response({
                'success': False,
                'error': 'Missing payment details'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find payment record
        try:
            payment = Payment.objects.get(
                razorpay_order_id=razorpay_order_id,
                user=request.user
            )
        except Payment.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verify signature
        try:
            client = get_razorpay_client()
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
        except razorpay.errors.SignatureVerificationError:
            payment.status = Payment.Status.FAILED
            payment.error_message = 'Signature verification failed'
            payment.save()
            return Response({
                'success': False,
                'error': 'Payment verification failed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update payment
        payment.razorpay_payment_id = razorpay_payment_id
        payment.razorpay_signature = razorpay_signature
        payment.status = Payment.Status.SUCCESS
        payment.paid_at = timezone.now()
        payment.save()
        
        # Update order
        order = payment.order
        order.paid_amount += payment.amount
        
        if payment.payment_for in ['first', 'full']:
            order.first_payment_date = timezone.now()
        else:
            order.second_payment_date = timezone.now()
        
        order.save()
        
        # Increment product orders count
        for item in order.items.all():
            if item.product:
                item.product.orders_count += 1
                item.product.save()
        
        return Response({
            'success': True,
            'message': 'Payment successful',
            'data': {
                'order': OrderSerializer(order).data,
                'is_fully_paid': order.is_fully_paid,
                'pending_amount': float(order.pending_amount)
            }
        })


class PayPendingAmountView(APIView):
    """
    Pay remaining amount for half-payment orders
    
    POST /api/orders/<order_id>/pay-pending/
    
    Creates new Razorpay order for pending amount
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request, order_id):
        try:
            order = Order.objects.get(order_id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if there's pending amount
        if order.pending_amount <= 0:
            return Response({
                'success': False,
                'error': 'No pending amount'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if order is not cancelled
        if order.status in [Order.Status.CANCELLED, Order.Status.REFUNDED]:
            return Response({
                'success': False,
                'error': 'Cannot pay for cancelled order'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        pending_amount = order.pending_amount
        
        # Create Razorpay order
        try:
            client = get_razorpay_client()
            razorpay_order = client.order.create({
                'amount': int(pending_amount * 100),
                'currency': 'INR',
                'receipt': f"{order.order_id}-2",
                'notes': {
                    'order_id': order.order_id,
                    'payment_for': 'second',
                    'user_phone': order.user_phone
                }
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Payment gateway error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create Payment record
        payment = Payment.objects.create(
            order=order,
            user=request.user,
            payment_for='second',
            amount=pending_amount,
            razorpay_order_id=razorpay_order['id'],
            status=Payment.Status.CREATED
        )
        
        return Response({
            'success': True,
            'message': 'Pay remaining amount',
            'data': {
                'order_id': order.order_id,
                'payment': {
                    'payment_id': payment.payment_id,
                    'amount': float(pending_amount),
                    'currency': 'INR',
                    'razorpay_order_id': razorpay_order['id'],
                    'razorpay_key': settings.RAZORPAY_KEY_ID,
                    'user_name': order.user_name,
                    'user_email': order.user_email,
                    'user_phone': order.user_phone,
                    'description': f'Remaining payment for Order {order.order_id}'
                }
            }
        })


# ========================
# ORDER LISTING APIs
# ========================

class MyOrdersView(generics.ListAPIView):
    """
    Get user's orders
    
    GET /api/orders/my-orders/
    
    Query params:
    - status: filter by status
    - has_pending: true/false - filter orders with pending payment
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListSerializer
    
    def get_queryset(self):
        qs = Order.objects.filter(user=self.request.user)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        has_pending = self.request.query_params.get('has_pending')
        if has_pending == 'true':
            qs = qs.filter(pending_amount__gt=0)
        
        return qs.prefetch_related('items')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Summary
        total_orders = queryset.count()
        pending_payments = queryset.filter(pending_amount__gt=0).count()
        
        return Response({
            'success': True,
            'summary': {
                'total_orders': total_orders,
                'pending_payments': pending_payments
            },
            'data': serializer.data
        })


class OrderDetailView(APIView):
    """
    Get single order detail
    
    GET /api/orders/<order_id>/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id):
        try:
            order = Order.objects.prefetch_related(
                'items', 'payments'
            ).get(order_id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'data': OrderSerializer(order).data
        })


class PendingPaymentsView(APIView):
    """
    Get all orders with pending payments
    
    GET /api/orders/pending-payments/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        orders = Order.objects.filter(
            user=request.user,
            pending_amount__gt=0
        ).exclude(
            status__in=[Order.Status.CANCELLED, Order.Status.REFUNDED]
        )
        
        data = []
        for order in orders:
            data.append({
                'order_id': order.order_id,
                'total_amount': float(order.total_amount),
                'paid_amount': float(order.paid_amount),
                'pending_amount': float(order.pending_amount),
                'due_date': order.second_payment_due_date,
                'created_at': order.created_at,
                'items_count': order.items.count()
            })
        
        total_pending = sum(order.pending_amount for order in orders)
        
        return Response({
            'success': True,
            'summary': {
                'total_pending_orders': orders.count(),
                'total_pending_amount': float(total_pending)
            },
            'data': data
        })


# ========================
# MY SUBMISSIONS
# ========================

class MySubmissionsView(generics.ListAPIView):
    """Get user's form submissions"""
    permission_classes = [IsAuthenticated]
    serializer_class = FormSubmissionSerializer
    
    def get_queryset(self):
        return FormSubmission.objects.filter(
            user=self.request.user
        ).select_related('product')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': len(serializer.data),
            'data': serializer.data
        })
