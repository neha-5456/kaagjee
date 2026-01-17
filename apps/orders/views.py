"""
CloudServices India - Orders Views
"""
from rest_framework import serializers, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db import transaction
from .models import Order, OrderItem, OrderFormSubmission, OrderStatusHistory
from apps.products.models import Product


# ========================
# SERIALIZERS
# ========================

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_title', 'product_slug', 'unit_price', 
                  'quantity', 'total_price', 'payment_option', 'state', 'city']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    amount_pending = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_fully_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'user', 'status', 'subtotal', 'discount',
                  'total_amount', 'amount_paid', 'amount_pending', 'is_fully_paid',
                  'customer_name', 'customer_email', 'customer_phone', 'customer_notes',
                  'items', 'created_at', 'paid_at']
        read_only_fields = ['order_number', 'user', 'created_at']


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating order"""
    product_id = serializers.IntegerField()
    payment_option = serializers.ChoiceField(choices=['full', 'half'])
    form_data = serializers.JSONField()
    state_id = serializers.IntegerField(required=False, allow_null=True)
    city_id = serializers.IntegerField(required=False, allow_null=True)
    customer_notes = serializers.CharField(required=False, allow_blank=True)


# ========================
# VIEWS
# ========================

class CreateOrderView(APIView):
    """Create a new order"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Get product
        try:
            product = Product.objects.get(id=data['product_id'], status=Product.Status.ACTIVE)
        except Product.DoesNotExist:
            return Response({'success': False, 'error': 'Product not found'}, status=404)
        
        # Calculate price
        payment_option = data['payment_option']
        if payment_option == 'half' and product.allow_half_payment:
            price = product.half_price or (product.full_price / 2)
        else:
            price = product.full_price
            payment_option = 'full'
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            subtotal=price,
            total_amount=price,
            customer_name=request.user.full_name,
            customer_email=request.user.email or '',
            customer_phone=str(request.user.phone_number),
            customer_notes=data.get('customer_notes', '')
        )
        
        # Create order item
        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            product_title=product.title,
            product_slug=product.slug,
            unit_price=price,
            total_price=price,
            payment_option=payment_option,
            state_id=data.get('state_id'),
            city_id=data.get('city_id')
        )
        
        # Save form submission
        OrderFormSubmission.objects.create(
            order_item=order_item,
            form_data=data['form_data'],
            form_schema_snapshot=product.form_schema or []
        )
        
        # Increment product orders count
        Product.objects.filter(pk=product.pk).update(orders_count=product.orders_count + 1)
        
        return Response({
            'success': True,
            'message': 'Order created successfully',
            'data': OrderSerializer(order).data
        }, status=201)


class OrderListView(generics.ListAPIView):
    """List user's orders"""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


class OrderDetailView(generics.RetrieveAPIView):
    """Get order detail"""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items')


# ========================
# ADMIN VIEWS
# ========================

class AdminOrderListView(generics.ListAPIView):
    """Admin: List all orders"""
    permission_classes = [IsAdminUser]
    serializer_class = OrderSerializer
    queryset = Order.objects.all().select_related('user').prefetch_related('items')


class AdminOrderDetailView(generics.RetrieveUpdateAPIView):
    """Admin: Get/Update order"""
    permission_classes = [IsAdminUser]
    serializer_class = OrderSerializer
    queryset = Order.objects.all()


class AdminUpdateOrderStatusView(APIView):
    """Admin: Update order status"""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'success': False, 'error': 'Order not found'}, status=404)
        
        new_status = request.data.get('status')
        if new_status not in Order.Status.values:
            return Response({'success': False, 'error': 'Invalid status'}, status=400)
        
        old_status = order.status
        
        # Create history
        OrderStatusHistory.objects.create(
            order=order,
            from_status=old_status,
            to_status=new_status,
            changed_by=request.user,
            notes=request.data.get('notes', '')
        )
        
        # Update status
        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])
        
        return Response({
            'success': True,
            'message': f'Status changed to {order.get_status_display()}',
            'data': OrderSerializer(order).data
        })
