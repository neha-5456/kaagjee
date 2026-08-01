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
from rest_framework.permissions import BasePermission, IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import razorpay
import hmac
import hashlib

from .models import (
    FormSubmission, Cart, CartItem, Order, OrderItem, Payment,
    OrderTask, OrderTaskDocument
)
from apps.products.models import Product
from apps.products.utils import calculate_total_price


import os
import uuid
from datetime import datetime
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.parsers import MultiPartParser, FormParser
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
    base_price = serializers.DecimalField(source='product.full_price', max_digits=10, decimal_places=2, read_only=True)
    half_price = serializers.DecimalField(source='product.half_price', max_digits=10, decimal_places=2, read_only=True)
    allow_half_payment = serializers.BooleanField(source='product.allow_half_payment', read_only=True)
    submission_id = serializers.UUIDField(source='form_submission.submission_id', read_only=True)
    form_data = serializers.JSONField(source='form_submission.form_data', read_only=True)
    pricing_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id', 'product_id', 'product_title', 'product_slug', 'product_image',
            'base_price', 'half_price', 'allow_half_payment', 'unit_price',
            'pricing_breakdown', 'submission_id', 'form_data', 'added_at', 'half_payment'
        ]

    def get_pricing_breakdown(self, obj):
        from apps.products.utils import calculate_total_price
        pricing = calculate_total_price(obj.product, obj.form_submission.form_data)
        return {
            'base_price': pricing['base_price'],
            'options_price': pricing.get('options_price', 0),
            'total_price': pricing['total_price'],
            'breakdown': pricing['price_breakdown']
        }


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'total_items', 'total_amount', 'items']


class OrderItemSerializer(serializers.ModelSerializer):
    rendered_preview = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_title', 'product_slug', 'unit_price',
            'form_data', 'uploaded_files', 'rendered_preview', 'created_at'
        ]

    def get_rendered_preview(self, obj):
        product = obj.product
        if not product or not product.preview_template:
            return None
        if hasattr(product, 'is_preview_enabled') and not product.is_preview_enabled:
            return None
        return _render_order_preview_template(product.preview_template, obj.form_data or {}, product.form_schema)


def _render_order_preview_template(template, form_data, form_schema=None):
    import re

    def normalize_template_html(html):
        html = re.sub(r'<span[^>]*>\s*\{\{\s*</span>', '{{', html)
        html = re.sub(r'<span[^>]*>\s*\}\}\s*</span>', '}}', html)
        return html

    template = normalize_template_html(template or '')
    lookup = dict(form_data or {})

    def collect(fields):
        for field in (fields or []):
            name = field.get('name', '')
            label = field.get('label', '')
            performa_key = field.get('performa_key', '').strip()
            value = form_data.get(name, '') or (form_data.get(performa_key, '') if performa_key else '')

            if name:
                lookup[name] = value
            if performa_key:
                lookup[performa_key] = value
            if label:
                normalized = re.sub(r'[^\w]+', '_', label.strip()).strip('_').lower()
                lookup[normalized] = value
                lookup[label] = value

            for opt in (field.get('options') or []):
                collect(opt.get('nested_fields') or [])

    if form_schema:
        collect(form_schema)

    def replacer(match):
        key = match.group(1).strip()
        val = lookup.get(key, '')
        if isinstance(val, list):
            val = ', '.join(str(v) for v in val)
        return str(val) if val else match.group(0)

    return re.sub(r'\{\{\s*([\w_ ]+)\s*\}\}', replacer, template)


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
    workflow_tasks = serializers.SerializerMethodField()
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
            'items', 'payments', 'workflow_tasks', 'created_at', 'updated_at'
        ]

    def get_workflow_tasks(self, obj):
        tasks = obj.workflow_tasks.select_related('assigned_admin', 'approved_by', 'created_by').all()
        return OrderTaskSerializer(tasks, many=True, context=self.context).data


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


class OrderWithAssignedTasksSerializer(serializers.ModelSerializer):
    """Order with assigned staff tasks grouped by staff member."""
    assigned_staff_groups = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'status', 'status_display', 'payment_type', 'payment_type_display',
            'total_amount', 'paid_amount', 'pending_amount',
            'user_name', 'user_email', 'user_phone', 'user_notes',
            'items_count', 'assigned_staff_groups', 'created_at', 'updated_at'
        ]
    
    def get_items_count(self, obj):
        return obj.items.count()
    
    def get_assigned_staff_groups(self, obj):
        """Group assigned tasks by staff member for this order."""
        tasks = obj.workflow_tasks.filter(
            assigned_admin__isnull=False
        ).select_related('assigned_admin', 'approved_by', 'created_by')
        
        context = self.context or {}
        task_status_filter = context.get('task_status_filter')
        admin_phone_filter = context.get('admin_phone_filter')
        current_user_id = context.get('current_user_id')
        is_superuser = context.get('is_superuser', False)
        
        if not is_superuser and current_user_id:
            tasks = tasks.filter(assigned_admin_id=current_user_id)
        
        if task_status_filter:
            tasks = tasks.filter(status=task_status_filter)
        
        if admin_phone_filter:
            tasks = tasks.filter(assigned_admin__phone_number=admin_phone_filter)
        
        grouped = {}
        for task in tasks:
            staff_id = task.assigned_admin_id
            if staff_id not in grouped:
                grouped[staff_id] = {
                    'staff_id': staff_id,
                    'staff_name': getattr(task.assigned_admin, 'full_name', None) or str(getattr(task.assigned_admin, 'phone_number', '')),
                    'staff_phone': str(task.assigned_admin.phone_number) if task.assigned_admin else None,
                    'tasks': []
                }
            grouped[staff_id]['tasks'].append(
                OrderTaskInOrderGroupSerializer(task, context=self.context).data
            )

        return list(grouped.values())


class IsSuperAdminPermission(BasePermission):
    """Allow only super admin user roles."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_superuser', False):
            return True
        if getattr(user, 'is_staff', False):
            return True
        return getattr(user, 'role', None) == 'admin'


class IsTaskAssignedAdmin(BasePermission):
    """Allow only the assigned admin or super admin."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_superuser', False):
            return True
        if getattr(user, 'is_staff', False):
            return True
        if getattr(user, 'role', None) == 'admin':
            return True
        return obj.assigned_admin_id == getattr(user, 'id', None)


class OrderTaskDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderTaskDocument
        fields = [
            'id', 'file', 'file_url', 'description', 'uploaded_by',
            'uploaded_by_name', 'uploaded_at'
        ]
        read_only_fields = ['uploaded_by', 'uploaded_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

    def get_uploaded_by_name(self, obj):
        return getattr(obj.uploaded_by, 'full_name', None) or str(getattr(obj.uploaded_by, 'phone_number', ''))


class OrderTaskSerializer(serializers.ModelSerializer):
    documents = OrderTaskDocumentSerializer(many=True, read_only=True)
    assigned_admin_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = OrderTask
        fields = [
            'id', 'order', 'title', 'description', 'assigned_admin',
            'assigned_admin_name', 'payment_amount', 'status', 'status_display',
            'remarks', 'requires_file_upload', 'completed_at', 'approved_by', 'approved_by_name',
            'approved_at', 'payment_released', 'documents',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'completed_at', 'approved_by', 'approved_at',
            'payment_released', 'created_by', 'created_at', 'updated_at'
        ]

    def get_assigned_admin_name(self, obj):
        if obj.assigned_admin:
            return getattr(obj.assigned_admin, 'full_name', None) or str(getattr(obj.assigned_admin, 'phone_number', ''))
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return getattr(obj.approved_by, 'full_name', None) or str(getattr(obj.approved_by, 'phone_number', ''))
        return None

    def validate(self, attrs):
        if self.instance and self.instance.status == OrderTask.Status.APPROVED:
            raise serializers.ValidationError('Approved tasks cannot be modified.')
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        task = OrderTask.objects.create(created_by=request.user, **validated_data)
        return task

    def update(self, instance, validated_data):
        assigned_admin = validated_data.get('assigned_admin')
        status = validated_data.get('status')
        if assigned_admin and instance.status == OrderTask.Status.PENDING:
            instance.status = OrderTask.Status.ASSIGNED
        if status:
            instance.status = status
        return super().update(instance, validated_data)


class OrderTaskInOrderGroupSerializer(serializers.ModelSerializer):
    """Serializer for tasks nested under an order group without repeating full order details."""
    documents = OrderTaskDocumentSerializer(many=True, read_only=True)
    assigned_admin_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = OrderTask
        fields = [
            'id', 'order', 'title', 'description', 'assigned_admin',
            'assigned_admin_name', 'payment_amount', 'status', 'status_display',
            'remarks', 'requires_file_upload', 'completed_at', 'approved_by', 'approved_by_name',
            'approved_at', 'payment_released', 'documents',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'completed_at', 'approved_by', 'approved_at',
            'payment_released', 'created_by', 'created_at', 'updated_at'
        ]

    def get_assigned_admin_name(self, obj):
        if obj.assigned_admin:
            return getattr(obj.assigned_admin, 'full_name', None) or str(getattr(obj.assigned_admin, 'phone_number', ''))
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return getattr(obj.approved_by, 'full_name', None) or str(getattr(obj.approved_by, 'phone_number', ''))
        return None


class OrderTaskWithOrderDetailsSerializer(serializers.ModelSerializer):
    """Serializer that includes full order details for task listing."""
    documents = OrderTaskDocumentSerializer(many=True, read_only=True)
    assigned_admin_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    order_details = serializers.SerializerMethodField()

    class Meta:
        model = OrderTask
        fields = [
            'id', 'order', 'order_details', 'title', 'description', 'assigned_admin',
            'assigned_admin_name', 'payment_amount', 'status', 'status_display',
            'remarks', 'requires_file_upload', 'completed_at', 'approved_by', 'approved_by_name',
            'approved_at', 'payment_released', 'documents',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'completed_at', 'approved_by', 'approved_at',
            'payment_released', 'created_by', 'created_at', 'updated_at'
        ]

    def get_assigned_admin_name(self, obj):
        if obj.assigned_admin:
            return getattr(obj.assigned_admin, 'full_name', None) or str(getattr(obj.assigned_admin, 'phone_number', ''))
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return getattr(obj.approved_by, 'full_name', None) or str(getattr(obj.approved_by, 'phone_number', ''))
        return None

    def get_order_details(self, obj):
        """Return complete order details including items, payments, and status."""
        order = obj.order
        return {
            'id': order.id,
            'order_id': order.order_id,
            'status': order.status,
            'status_display': order.get_status_display(),
            'payment_type': order.payment_type,
            'payment_type_display': order.get_payment_type_display(),
            'total_amount': float(order.total_amount),
            'paid_amount': float(order.paid_amount),
            'pending_amount': float(order.pending_amount),
            'user_name': order.user_name,
            'user_email': order.user_email,
            'user_phone': order.user_phone,
            'user_notes': order.user_notes,
            'items_count': order.items.count(),
            'created_at': order.created_at,
            'updated_at': order.updated_at,
        }


# ========================
# HELPER FUNCTIONS
# ========================

def get_or_create_cart(user):
    """Get or create cart for authenticated user"""
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


def remap_with_performa_keys(form_data, form_schema):
    """form_data keys ko performa_key se replace karo agar set hai"""
    if not form_schema:
        return form_data
    key_map = {}
    def collect_keys(fields):
        for field in (fields or []):
            name = field.get('name', '')
            pk   = field.get('performa_key', '').strip()
            if name and pk:
                key_map[name] = pk
            for opt in (field.get('options') or []):
                collect_keys(opt.get('nested_fields') or [])
    collect_keys(form_schema)
    return {key_map.get(k, k): v for k, v in form_data.items()}


def _parse_date_field_value(value):
    if not value:
        return None
    value_str = str(value).strip()
    if not value_str:
        return None
    try:
        return datetime.strptime(value_str, '%Y-%m-%d').date()
    except ValueError:
        try:
            return datetime.fromisoformat(value_str).date()
        except ValueError:
            return None


def _month_difference_inclusive(start_date, end_date):
    if end_date < start_date:
        return -1
    return (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)


def validate_range_date_fields(form_schema, form_data):
    """Validate range_date fields configured in the product form builder."""
    errors = []

    for field in (form_schema or []):
        if field.get('field_type') != 'range_date':
            continue

        name = str(field.get('name', '')).strip()
        if not name:
            continue

        label = field.get('label', name or 'Date Range')
        start_key = f'{name}_start'
        end_key = f'{name}_end'

        start_value = form_data.get(start_key)
        end_value = form_data.get(end_key)
        start_date = _parse_date_field_value(start_value)
        end_date = _parse_date_field_value(end_value)

        if not start_date or not end_date:
            errors.append(f"{label} requires both start and end dates.")
            continue

        if start_date > end_date:
            errors.append(f"{label} start date cannot be after end date.")
            continue

        configured_start = _parse_date_field_value(field.get('range_start_date'))
        configured_end = _parse_date_field_value(field.get('range_end_date'))
        if configured_start and start_date < configured_start:
            errors.append(f"{label} start date must be on or after {configured_start.isoformat()}.")
        if configured_end and end_date > configured_end:
            errors.append(f"{label} end date must be on or before {configured_end.isoformat()}.")

        max_months = int(field.get('max_months') or field.get('allowed_months') or 11)
        month_diff = _month_difference_inclusive(start_date, end_date)
        if month_diff > max_months:
            errors.append(f"{label} cannot exceed {max_months} months.")

    return errors


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

        # performa_key se remap karo
        form_data = remap_with_performa_keys(form_data, product.form_schema)
        
        # Validate required fields from form_schema
        errors = []
        for field in (product.form_schema or []):
            if field.get('required') and field.get('name'):
                if field.get('field_type') == 'range_date':
                    start_key = f"{field['name']}_start"
                    end_key = f"{field['name']}_end"
                    if not form_data.get(start_key) or not form_data.get(end_key):
                        errors.append(f"{field.get('label', field['name'])} requires both start and end dates")
                elif field['name'] not in form_data or not form_data[field['name']]:
                    errors.append(f"{field.get('label', field['name'])} is required")

        range_errors = validate_range_date_fields(product.form_schema, form_data)
        errors.extend(range_errors)

        if errors:
            return Response({
                'success': False,
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate price based on selected options (dynamic pricing)
        pricing = calculate_total_price(product, form_data)
        calculated_price = pricing['total_price']
        
        # Create submission
        submission = FormSubmission.objects.create(
            user=request.user,
            product=product,
            form_data=form_data,
            price_at_submission=calculated_price,
            user_notes=user_notes,
            status=FormSubmission.Status.IN_CART
        )
        
        # Add to cart
        cart = get_or_create_cart(request.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            product=product,
            form_submission=submission,
            unit_price=calculated_price
        )
        
        return Response({
            'success': True,
            'message': 'Form submitted and added to cart',
            'data': {
                'submission': FormSubmissionSerializer(submission).data,
                'cart_item_id': cart_item.id,
                'cart_total': cart.total_amount,
                'cart_items_count': cart.total_items,
                'pricing': pricing
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

        # performa_key se remap karo
        form_data = remap_with_performa_keys(form_data, product.form_schema)

        # Validate required + range-date constraints
        errors = []
        for field in (product.form_schema or []):
            if field.get('required') and field.get('name'):
                if field.get('field_type') == 'range_date':
                    start_key = f"{field['name']}_start"
                    end_key = f"{field['name']}_end"
                    if not form_data.get(start_key) or not form_data.get(end_key):
                        errors.append(f"{field.get('label', field['name'])} requires both start and end dates")
                elif field['name'] not in form_data or not form_data[field['name']]:
                    errors.append(f"{field.get('label', field['name'])} is required")

        errors.extend(validate_range_date_fields(product.form_schema, form_data))
        if errors:
            return Response({
                'success': False,
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Handle files
        uploaded_files = {}
        submission_uuid = uuid_lib.uuid4().hex[:12]
        
        # Process all uploaded files
        for key, file_list in request.FILES.lists():
            field_name = key[5:] if key.startswith('file_') else key
            
            saved_files = []
            for file in file_list:
                ext = os.path.splitext(file.name)[1]
                filename = f"{submission_uuid}_{field_name}_{file.name}"
                path = f"submissions/{product.slug}/{filename}"
                saved_path = default_storage.save(path, ContentFile(file.read()))
                saved_files.append(saved_path)
            
            # Store as single file or array based on count
            if len(saved_files) == 1:
                uploaded_files[field_name] = saved_files[0]
                form_data[field_name] = saved_files[0]
            else:
                uploaded_files[field_name] = saved_files
                form_data[field_name] = saved_files
        
        # ========================================
        # DYNAMIC PRICING: Calculate based on selected dropdown/radio options
        # ========================================
        pricing = calculate_total_price(product, form_data)
        print("Pricing details:", pricing)
        calculated_price = pricing['total_price']
        
        # Check if dropdown option selected (has price_breakdown)
        has_dropdown_selection = bool(pricing.get('price_breakdown'))
        half_payment_value = 0 if has_dropdown_selection else product.half_price
        
        # Create submission with calculated price (not just product.full_price)
        submission = FormSubmission.objects.create(
            user=request.user,
            product=product,
            form_data=form_data,
            uploaded_files=uploaded_files,
            price_at_submission=calculated_price,
            status=FormSubmission.Status.IN_CART
        )
        
        # Add to cart with calculated price
        cart = get_or_create_cart(request.user)
        CartItem.objects.create(
            cart=cart,
            product=product,
            form_submission=submission,
            unit_price=calculated_price,
            half_payment=half_payment_value
        )
        
        return Response({
            'success': True,
            'message': 'Form submitted with files',
            'data': {
                'submission': FormSubmissionSerializer(submission).data,
                'cart_items_count': cart.total_items,
                'pricing': pricing
            }
        }, status=201)
    
    
    @transaction.atomic
    def put(self, request):
        import json
        import os
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile

        submission_id = request.data.get('submission_id')

        if not submission_id:
            return Response(
                {'success': False, 'error': 'submission_id is required'},
                status=400
            )

        try:
            submission = FormSubmission.objects.get(
                id=submission_id,
                user=request.user,
                status=FormSubmission.Status.IN_CART
            )
        except FormSubmission.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Submission not found or not editable'},
                status=404
            )

        # Existing data
        form_data = submission.form_data or {}
        uploaded_files = submission.uploaded_files or {}

        # Update form_data
        try:
            incoming_form_data = json.loads(request.data.get('form_data', '{}'))
            incoming_form_data = remap_with_performa_keys(incoming_form_data, submission.product.form_schema)
            form_data.update(incoming_form_data)
        except:
            pass

        # Handle new uploaded files
        for key, file_list in request.FILES.lists():
            field_name = key[5:] if key.startswith('file_') else key
            saved_files = []

            for file in file_list:
                filename = f"{submission.id}_{field_name}_{file.name}"
                path = f"submissions/{submission.product.slug}/{filename}"
                saved_path = default_storage.save(path, ContentFile(file.read()))
                saved_files.append(saved_path)

            if len(saved_files) == 1:
                uploaded_files[field_name] = saved_files[0]
                form_data[field_name] = saved_files[0]
            else:
                uploaded_files[field_name] = saved_files
                form_data[field_name] = saved_files

        # ========================================
        # DYNAMIC PRICING (Same as POST)
        # ========================================
        pricing = calculate_total_price(submission.product, form_data)
        calculated_price = pricing['total_price']
        
        # Check if dropdown option selected (has price_breakdown)
        has_dropdown_selection = bool(pricing.get('price_breakdown'))
        half_payment_value = 0 if has_dropdown_selection else submission.product.half_price

        # Update submission
        submission.form_data = form_data
        submission.uploaded_files = uploaded_files
        submission.price_at_submission = calculated_price
        submission.save(update_fields=[
            'form_data',
            'uploaded_files',
            'price_at_submission'
        ])

        # Update cart item price
        CartItem.objects.filter(
            form_submission=submission
        ).update(
            unit_price=calculated_price,
            half_payment=half_payment_value
        )

        return Response({
            'success': True,
            'message': 'Form updated successfully',
            'data': {
                'submission': FormSubmissionSerializer(submission).data,
                'pricing': pricing
            }
        }, status=200)

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
        user_name = request.data.get('user_name', getattr(request.user, 'full_name', '') or str(request.user.phone_number))
        user_email = request.data.get('user_email', getattr(request.user, 'email', '') or '')
        user_phone = request.data.get('user_phone', str(getattr(request.user, 'phone_number', '')))
        user_notes = request.data.get('user_notes', '')
        
        # Validate payment type
        if payment_type not in ['full', 'half']:
            return Response({
                'success': False,
                'error': 'Invalid payment_type. Use "full" or "half"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if any cart item has dropdown variation (has price_breakdown)
        # Recalculate prices for all cart items and update unit_price
        has_variation = False
        for item in cart.items.all():
            pricing = calculate_total_price(item.product, item.form_submission.form_data)
            new_price = pricing['total_price']
            # Update unit_price and price_at_submission with latest calculated price
            item.unit_price = new_price
            item.save(update_fields=['unit_price'])
            item.form_submission.price_at_submission = new_price
            item.form_submission.save(update_fields=['price_at_submission'])
            if pricing.get('price_breakdown'):
                has_variation = True
        
        # If variation exists, force full payment only
        if has_variation:
            if payment_type == 'half':
                return Response({
                    'success': False,
                    'error': 'Half payment not allowed for variation products'
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


# class OrderDetailView(APIView):
#     """
#     Get single order detail
    
#     GET /api/orders/<order_id>/
#     """
#     permission_classes = [IsAuthenticated , IsSuperAdminPermission]
    
#     def get(self, request, order_id):
#         try:
#             order = Order.objects.prefetch_related(
#                 'items', 'payments'
#             ).get(order_id=order_id, user=request.user)
#         except Order.DoesNotExist:
#             return Response({
#                 'success': False,
#                 'error': 'Order not found'
#             }, status=status.HTTP_404_NOT_FOUND)
        
#         return Response({
#             'success': True,
#             'data': OrderSerializer(order).data
#         })

class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        queryset = Order.objects.prefetch_related('items', 'payments')

        if request.user.is_staff:
            order = get_object_or_404(queryset, order_id=order_id)
        else:
            order = get_object_or_404(
                queryset,
                order_id=order_id,
                user=request.user
            )

        return Response({
            "success": True,
            "data": OrderSerializer(order).data
        })

class OrderTaskListCreateView(APIView):
    """Super admin can list and create tasks for any order."""
    permission_classes = [IsAuthenticated, IsSuperAdminPermission]

    def get(self, request):
        order_id = request.query_params.get('order_id')
        tasks = OrderTask.objects.select_related(
            'order', 'assigned_admin', 'approved_by', 'created_by'
        ).all()
        if order_id:
            tasks = tasks.filter(order__order_id=order_id)
        serializer = OrderTaskSerializer(tasks, many=True, context={'request': request})
        return Response({'success': True, 'data': serializer.data})

    def post(self, request):
        serializer = OrderTaskSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            task = serializer.save()
            return Response({
                'success': True,
                'message': 'Order task created',
                'data': OrderTaskSerializer(task, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class OrderTaskDetailView(APIView):
    """Super admin can retrieve, update, and delete a task."""
    permission_classes = [IsAuthenticated, IsSuperAdminPermission]

    def get_object(self, task_id):
        return get_object_or_404(OrderTask, id=task_id)

    def get(self, request, task_id):
        task = self.get_object(task_id)
        serializer = OrderTaskSerializer(task, context={'request': request})
        return Response({'success': True, 'data': serializer.data})

    def put(self, request, task_id):
        task = self.get_object(task_id)
        serializer = OrderTaskSerializer(task, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            task = serializer.save()
            return Response({'success': True, 'message': 'Order task updated', 'data': OrderTaskSerializer(task, context={'request': request}).data})
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, task_id):
        task = self.get_object(task_id)
        task.delete()
        return Response({'success': True, 'message': 'Order task deleted'})


class AssignedTaskListView(generics.ListAPIView):
    """Assigned admins can view tasks assigned to them."""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderTaskSerializer

    def get_queryset(self):
        return OrderTask.objects.filter(assigned_admin=self.request.user).select_related(
            'order', 'assigned_admin', 'approved_by', 'created_by'
        )


class MobileAssignedTaskListView(generics.ListAPIView):
    """Mobile-friendly endpoint: list only tasks assigned to the current admin."""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderTaskSerializer

    def get_queryset(self):
        return OrderTask.objects.filter(assigned_admin=self.request.user).select_related(
            'order', 'assigned_admin', 'approved_by', 'created_by'
        ).order_by('-updated_at', '-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})


class AssignedTaskDetailView(APIView):
    """Assigned admin can retrieve their own task."""
    permission_classes = [IsAuthenticated]

    def get_object(self, task_id):
        task = get_object_or_404(OrderTask, id=task_id)
        if task.assigned_admin_id != self.request.user.id and getattr(self.request.user, 'role', None) != 'admin' and not getattr(self.request.user, 'is_superuser', False):
            return None
        return task

    def get(self, request, task_id):
        task = self.get_object(task_id)
        if not task:
            return Response({'success': False, 'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        serializer = OrderTaskSerializer(task, context={'request': request})
        return Response({'success': True, 'data': serializer.data})


class AssignedTaskCompleteView(APIView):
    """Assigned admin uploads documents and marks the task as completed."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, task_id):
        task = get_object_or_404(OrderTask, id=task_id)
        user = request.user
        if task.assigned_admin_id != user.id and getattr(user, 'role', None) != 'admin' and not getattr(user, 'is_superuser', False):
            return Response({'success': False, 'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        remarks = request.data.get('remarks', task.remarks)
        files = request.FILES.getlist('files') or request.FILES.getlist('documents')

        task.remarks = remarks
        task.status = OrderTask.Status.COMPLETED
        task.save()

        documents = []
        for file in files:
            doc = OrderTaskDocument.objects.create(
                task=task,
                file=file,
                uploaded_by=user
            )
            documents.append(doc)

        serializer = OrderTaskSerializer(task, context={'request': request})
        return Response({
            'success': True,
            'message': 'Task marked completed and documents uploaded',
            'data': serializer.data
        })


class MobileTaskSubmitView(APIView):
    """Mobile-friendly endpoint: submit task completion or rejection with notes and uploads."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, task_id):
        task = get_object_or_404(OrderTask, id=task_id)
        user = request.user
        if task.assigned_admin_id != user.id and getattr(user, 'role', None) != 'admin' and not getattr(user, 'is_superuser', False):
            return Response({'success': False, 'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        raw_status = request.data.get('status') or request.data.get('action') or request.data.get('decision') or ''
        action = str(raw_status).strip().lower()
        remarks = request.data.get('remarks', '')
        files = request.FILES.getlist('files') or request.FILES.getlist('documents')

        rejected_actions = {'rejected', 'reject', 'rejection', 'declined', 'decline', 'false', '0'}
        if action in rejected_actions:
            task.status = OrderTask.Status.REJECTED
            task.payment_released = False
            task.approved_by = None
            task.approved_at = None
            task.completed_at = None
        else:
            task.status = OrderTask.Status.COMPLETED
            task.payment_released = False
            task.approved_by = None
            task.approved_at = None

        task.remarks = remarks
        task.save()

        for file in files:
            OrderTaskDocument.objects.create(task=task, file=file, uploaded_by=user)

        serializer = OrderTaskSerializer(task, context={'request': request})
        return Response({
            'success': True,
            'message': 'Task submitted successfully',
            'task_id': task.id,
            'data': serializer.data
        })


class OrderTaskApprovalView(APIView):
    """Super admin approves or rejects a completed task."""
    permission_classes = [IsAuthenticated, IsSuperAdminPermission]

    def post(self, request, task_id, action):
        task = get_object_or_404(OrderTask, id=task_id)
        if task.status != OrderTask.Status.COMPLETED:
            return Response({'success': False, 'error': 'Only completed tasks can be approved or rejected'}, status=status.HTTP_400_BAD_REQUEST)

        remarks = request.data.get('remarks', '')
        if action == 'approve':
            task.status = OrderTask.Status.APPROVED
            task.approved_by = request.user
            task.approved_at = timezone.now()
            task.payment_released = True
            message = 'Task approved'
        else:
            task.status = OrderTask.Status.REJECTED
            task.approved_by = request.user
            task.approved_at = timezone.now()
            task.payment_released = False
            message = 'Task rejected'

        task.remarks = remarks
        task.save()
        serializer = OrderTaskSerializer(task, context={'request': request})
        return Response({'success': True, 'message': message, 'data': serializer.data})


class SuperAdminAssignedTasksView(generics.ListAPIView):
    """
    Super admin can view all tasks assigned to staff members with complete order details.
    
    GET /api/orders/admin/all-assigned-tasks/
    
    Query params:
    - status: filter by task status (pending, assigned, in_progress, completed, approved, rejected)
    - order_id: filter by specific order
    - admin_phone: filter by staff member's phone number
    """
    permission_classes = [IsAuthenticated, IsSuperAdminPermission]
    serializer_class = OrderTaskWithOrderDetailsSerializer

    def get_queryset(self):
        # Get all tasks assigned to any staff member (not None)
        qs = OrderTask.objects.filter(
            assigned_admin__isnull=False
        ).select_related(
            'order', 'assigned_admin', 'approved_by', 'created_by'
        ).order_by('-created_at')
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        # Filter by order_id if provided
        order_id_filter = self.request.query_params.get('order_id')
        if order_id_filter:
            qs = qs.filter(order__order_id=order_id_filter)
        
        # Filter by assigned staff member phone if provided
        admin_phone = self.request.query_params.get('admin_phone')
        if admin_phone:
            qs = qs.filter(assigned_admin__phone_number=admin_phone)
        
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Summary statistics
        total_tasks = queryset.count()
        pending_tasks = queryset.filter(status__in=[
            OrderTask.Status.PENDING, 
            OrderTask.Status.ASSIGNED, 
            OrderTask.Status.IN_PROGRESS
        ]).count()
        completed_tasks = queryset.filter(status=OrderTask.Status.COMPLETED).count()
        approved_tasks = queryset.filter(status=OrderTask.Status.APPROVED).count()
        rejected_tasks = queryset.filter(status=OrderTask.Status.REJECTED).count()
        
        # Get count of unique staff members with assigned tasks
        assigned_staff_count = queryset.values('assigned_admin').distinct().count()
        
        return Response({
            'success': True,
            'summary': {
                'total_tasks': total_tasks,
                'assigned_staff_count': assigned_staff_count,
                'pending_tasks': pending_tasks,
                'completed_tasks': completed_tasks,
                'approved_tasks': approved_tasks,
                'rejected_tasks': rejected_tasks,
            },
            'data': serializer.data
        })


class OrdersWithAssignedTasksView(generics.ListAPIView):
    """
    Super admin can view all orders that have tasks assigned to staff.
    Each order includes its assigned tasks with full details.
    
    GET /api/orders/admin/orders-with-tasks/
    
    Query params:
    - task_status: filter by task status (pending, assigned, in_progress, completed, approved, rejected)
    - order_status: filter by order status
    - admin_phone: filter by staff member's phone number
    """
    permission_classes = [IsAuthenticated, IsSuperAdminPermission]
    serializer_class = OrderWithAssignedTasksSerializer

    def get_queryset(self):
        user = self.request.user
        is_superuser = getattr(user, 'is_superuser', False)

        if is_superuser:
            qs = Order.objects.prefetch_related(
                'workflow_tasks',
                'items'
            ).filter(
                workflow_tasks__assigned_admin__isnull=False
            ).distinct().order_by('-created_at')
        else:
            qs = Order.objects.prefetch_related(
                'workflow_tasks',
                'items'
            ).filter(
                workflow_tasks__assigned_admin=user
            ).distinct().order_by('-created_at')
        
        # Filter by order status if provided
        order_status_filter = self.request.query_params.get('order_status')
        if order_status_filter:
            qs = qs.filter(status=order_status_filter)
        
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Additional filtering by task status (done in Python since it's prefetched)
        task_status_filter = request.query_params.get('task_status')
        admin_phone_filter = request.query_params.get('admin_phone')
        is_superuser = getattr(request.user, 'is_superuser', False)
        
        # Pass filters to context for the serializer to use
        context = self.get_serializer_context()
        context['task_status_filter'] = task_status_filter
        context['admin_phone_filter'] = admin_phone_filter
        context['current_user_id'] = request.user.id
        context['is_superuser'] = is_superuser
        
        filtered_orders = []
        seen_order_ids = set()
        total_filtered_tasks = 0
        
        for order in queryset:
            if order.id in seen_order_ids:
                continue

            assigned_tasks = [
                task for task in order.workflow_tasks.all()
                if task.assigned_admin_id
            ]
            
            if not is_superuser:
                assigned_tasks = [
                    task for task in assigned_tasks
                    if task.assigned_admin_id == request.user.id
                ]
            
            # Filter by task status if provided
            if task_status_filter:
                assigned_tasks = [
                    task for task in assigned_tasks
                    if task.status == task_status_filter
                ]
            
            # Filter by admin phone if provided
            if admin_phone_filter:
                assigned_tasks = [
                    task for task in assigned_tasks
                    if str(task.assigned_admin.phone_number) == admin_phone_filter
                ]
            
            # Only include orders that have matching tasks after filtering
            if assigned_tasks:
                filtered_orders.append(order)
                seen_order_ids.add(order.id)
                total_filtered_tasks += len(assigned_tasks)
        
        serializer = self.get_serializer(filtered_orders, many=True, context=context)
        
        # Calculate summary based on filtered data
        total_orders = len(filtered_orders)
        
        return Response({
            'success': True,
            'summary': {
                'total_orders': total_orders,
                'total_tasks': total_filtered_tasks,
            },
            'data': serializer.data
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


class SubmissionDetailView(APIView):
    """
    GET /api/orders/submissions/<submission_id>/
    Returns a single form submission by its UUID.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, submission_id):
        try:
            submission = FormSubmission.objects.select_related('product').get(
                submission_id=submission_id,
                user=request.user
            )
        except FormSubmission.DoesNotExist:
            return Response({'success': False, 'error': 'Submission not found'}, status=404)

        return Response({
            'success': True,
            'data': FormSubmissionSerializer(submission).data
        })




class FileUploadView(APIView):
    """
    Upload single file and get server path
    
    POST /api/orders/upload-file/
    
    Headers:
        Authorization: Bearer <token>
        Content-Type: multipart/form-data
    
    Form Data:
        - file: The file to upload (required)
        - folder: Custom folder name (optional, default: 'uploads')
        - prefix: Filename prefix (optional, e.g., 'passport', 'aadhaar')
    
    Response:
        {
            "success": true,
            "message": "File uploaded successfully",
            "data": {
                "file_path": "uploads/mobile/abc123_passport_document.pdf",
                "file_url": "/media/uploads/mobile/abc123_passport_document.pdf",
                "file_name": "abc123_passport_document.pdf",
                "original_name": "document.pdf",
                "file_size": 1024,
                "content_type": "application/pdf"
            }
        }
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = [
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg',
        # Documents
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.txt', '.rtf', '.odt', '.ods', '.odp',
        # Others
        '.zip', '.rar', '.7z'
    ]
    
    # Max file size: 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    def post(self, request):
        # Get file from request
        file = request.FILES.get('file')
        
        if not file:
            return Response({
                'success': False,
                'error': 'No file provided',
                'message': 'Please send a file with key "file"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file size
        if file.size > self.MAX_FILE_SIZE:
            return Response({
                'success': False,
                'error': 'File too large',
                'message': f'Maximum file size is {self.MAX_FILE_SIZE // (1024*1024)}MB'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate file extension
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            return Response({
                'success': False,
                'error': 'Invalid file type',
                'message': f'Allowed types: {", ".join(self.ALLOWED_EXTENSIONS)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get optional parameters
        folder = request.data.get('folder', 'mobile')
        prefix = request.data.get('prefix', '')
        
        # Generate unique filename
        unique_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now().strftime('%Y%m%d')
        original_name = os.path.splitext(file.name)[0]
        
        # Clean original name (remove special chars)
        clean_name = ''.join(c for c in original_name if c.isalnum() or c in '-_')[:30]
        
        # Build filename
        if prefix:
            filename = f"{unique_id}_{prefix}_{clean_name}{ext}"
        else:
            filename = f"{unique_id}_{timestamp}_{clean_name}{ext}"
        
        # Build full path
        file_path = f"uploads/{folder}/{filename}"
        
        # Save file
        try:
            saved_path = default_storage.save(file_path, ContentFile(file.read()))
            file_url = f"{settings.MEDIA_URL}{saved_path}"
            
            return Response({
                'success': True,
                'message': 'File uploaded successfully',
                'data': {
                    'file_path': saved_path,
                    'file_url': file_url,
                    'file_name': filename,
                    'original_name': file.name,
                    'file_size': file.size,
                    'content_type': file.content_type
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Upload failed',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MultipleFilesUploadView(APIView):
    """
    Upload multiple files and get server paths
    
    POST /api/orders/upload-files/
    
    Headers:
        Authorization: Bearer <token>
        Content-Type: multipart/form-data
    
    Form Data:
        - files: Multiple files (required)
        - folder: Custom folder name (optional, default: 'mobile')
        - prefix: Filename prefix (optional)
    
    Response:
        {
            "success": true,
            "message": "3 files uploaded successfully",
            "data": {
                "uploaded_files": [
                    {
                        "file_path": "uploads/mobile/abc123_doc1.pdf",
                        "file_url": "/media/uploads/mobile/abc123_doc1.pdf",
                        "file_name": "abc123_doc1.pdf",
                        "original_name": "doc1.pdf"
                    },
                    ...
                ],
                "total_uploaded": 3,
                "total_size": 3072
            }
        }
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    ALLOWED_EXTENSIONS = [
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.txt', '.rtf', '.odt', '.ods', '.odp',
        '.zip', '.rar', '.7z'
    ]
    MAX_FILE_SIZE = 10 * 1024 * 1024
    MAX_FILES = 10
    
    def post(self, request):
        # Get files - can be sent as 'files' or 'files[]' or multiple 'file' keys
        files = request.FILES.getlist('files') or request.FILES.getlist('files[]')
        
        # Also check for individual file keys (file_0, file_1, etc.)
        if not files:
            for key in request.FILES:
                if key.startswith('file'):
                    files.extend(request.FILES.getlist(key))
        
        if not files:
            return Response({
                'success': False,
                'error': 'No files provided',
                'message': 'Please send files with key "files" or "files[]"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(files) > self.MAX_FILES:
            return Response({
                'success': False,
                'error': 'Too many files',
                'message': f'Maximum {self.MAX_FILES} files allowed at once'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get optional parameters
        folder = request.data.get('folder', 'mobile')
        prefix = request.data.get('prefix', '')
        
        # Generate unique batch ID
        batch_id = uuid.uuid4().hex[:8]
        
        uploaded_files = []
        errors = []
        total_size = 0
        
        for idx, file in enumerate(files):
            # Validate file size
            if file.size > self.MAX_FILE_SIZE:
                errors.append(f"{file.name}: File too large (max {self.MAX_FILE_SIZE // (1024*1024)}MB)")
                continue
            
            # Validate extension
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in self.ALLOWED_EXTENSIONS:
                errors.append(f"{file.name}: Invalid file type")
                continue
            
            # Generate filename
            original_name = os.path.splitext(file.name)[0]
            clean_name = ''.join(c for c in original_name if c.isalnum() or c in '-_')[:30]
            
            if prefix:
                filename = f"{batch_id}_{prefix}_{idx}_{clean_name}{ext}"
            else:
                filename = f"{batch_id}_{idx}_{clean_name}{ext}"
            
            file_path = f"uploads/{folder}/{filename}"
            
            try:
                saved_path = default_storage.save(file_path, ContentFile(file.read()))
                file_url = f"{settings.MEDIA_URL}{saved_path}"
                
                uploaded_files.append({
                    'file_path': saved_path,
                    'file_url': file_url,
                    'file_name': filename,
                    'original_name': file.name,
                    'file_size': file.size,
                    'content_type': file.content_type
                })
                total_size += file.size
                
            except Exception as e:
                errors.append(f"{file.name}: {str(e)}")
        
        if not uploaded_files:
            return Response({
                'success': False,
                'error': 'No files uploaded',
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'message': f'{len(uploaded_files)} file(s) uploaded successfully',
            'data': {
                'uploaded_files': uploaded_files,
                'total_uploaded': len(uploaded_files),
                'total_size': total_size,
                'batch_id': batch_id
            },
            'errors': errors if errors else None
        }, status=status.HTTP_201_CREATED)


class DeleteUploadedFileView(APIView):
    """
    Delete an uploaded file (optional - for cleanup)

    DELETE /api/orders/delete-file/

    Body:
        {"file_path": "uploads/mobile/abc123_doc.pdf"}
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        file_path = request.data.get('file_path')
        
        if not file_path:
            return Response({
                'success': False,
                'error': 'file_path required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Security: Only allow deletion from uploads folder
        if not file_path.startswith('uploads/'):
            return Response({
                'success': False,
                'error': 'Invalid file path'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
                return Response({
                    'success': True,
                    'message': 'File deleted successfully'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'File not found'
                }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========================
# PDF GENERATION API
# ========================

class GeneratePDFView(APIView):
    """
    POST /api/orders/generate-pdf/

    Body:
    {
        "product_slug": "pan-card",
        "form_data": {"full_name": "Rahul", "city": "Delhi", ...}
    }

    OR use an existing submission:
    {
        "submission_id": "<uuid>"
    }

    Returns a PDF file (application/pdf) generated from the product's
    preview_template with placeholders replaced by form_data values.

    Requires: weasyprint  →  pip install weasyprint
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            from weasyprint import HTML
        except ImportError:
            return Response(
                {'success': False, 'error': 'PDF generation not available. Install weasyprint.'},
                status=500
            )

        from django.http import HttpResponse
        import re

        submission_id = request.data.get('submission_id')
        product_slug  = request.data.get('product_slug')
        form_data     = request.data.get('form_data', {})

        # --- resolve product + form_data ---
        if submission_id:
            try:
                submission = FormSubmission.objects.select_related('product').get(
                    submission_id=submission_id,
                    user=request.user
                )
                product   = submission.product
                form_data = submission.form_data
                # Debug: Log submission data
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[PDF] Submission {submission_id}: form_data keys = {list(form_data.keys()) if form_data else 'None'}")
                if form_data and 'registration_number' in form_data:
                    logger.info(f"[PDF] Found registration_number = {form_data.get('registration_number')}")
            except FormSubmission.DoesNotExist:
                return Response({'success': False, 'error': 'Submission not found'}, status=404)
        elif product_slug:
            try:
                product = Product.objects.get(slug=product_slug, status=Product.Status.ACTIVE)
            except Product.DoesNotExist:
                return Response({'success': False, 'error': 'Product not found'}, status=404)
        else:
            return Response({'success': False, 'error': 'product_slug or submission_id required'}, status=400)

        if not product.preview_template:
            return Response({'success': False, 'error': 'No preview template configured for this product'}, status=400)

        # --- build lookup table with field names and performa_keys ---
        import logging
        logger = logging.getLogger(__name__)
        
        lookup = dict(form_data)
        performa_keys = set()
        logger.info(f"[PDF] Initial lookup from form_data: {list(lookup.keys())}")
        
        def collect(fields):
            for field in (fields or []):
                name         = field.get('name', '')
                label        = field.get('label', '')
                performa_key = field.get('performa_key', '').strip()
                value        = form_data.get(name, '') or (form_data.get(performa_key, '') if performa_key else '')
                if name:
                    lookup[name] = value
                if performa_key:
                    lookup[performa_key] = value
                    performa_keys.add(performa_key)
                if label:
                    normalized = re.sub(r'[^\w]+', '_', label.strip()).strip('_').lower()
                    lookup[normalized] = value
                    lookup[label]      = value
                for opt in (field.get('options') or []):
                    collect(opt.get('nested_fields') or [])
        collect(product.form_schema or [])
        
        logger.info(f"[PDF] Final lookup keys after collection: {list(lookup.keys())}")

        # --- render template ---
        def replacer(match):
            key = match.group(1).strip()
            val = lookup.get(key, None)
            # Debug: Log missing keys (optional - remove later if not needed)
            if val is None:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"PDF rendering: Key '{key}' not found in lookup. Available keys: {list(lookup.keys())}")
                return match.group(0)  # Return original placeholder if not found
            if isinstance(val, list):
                val = ', '.join(str(v) for v in val)
            if key in performa_keys and val:
                return f'<strong style="font-weight:700;display:inline-block;margin:0 0.12em">{val}</strong>'
            return str(val) if val else ''
        template = product.preview_template
        pages = []
        try:
            parsed = _json.loads(template)
            if isinstance(parsed, list):
                # JSON array: [{"title": "Page 1", "template": "<html>..."}, ...]
                pages = [p.get('template', '') for p in parsed if p.get('template', '').strip()]
        except (ValueError, TypeError):
            pass

        if not pages:
            # Fallback: split by PAGE_BREAK marker
            pages = [p.strip() for p in template.split('<!-- PAGE_BREAK -->') if p.strip()]

        if not pages:
            return Response({'success': False, 'error': 'No pages found in template'}, status=400)

        def normalize_template_html(html):
            # Quill editor may wrap the literal braces in styled spans,
            # e.g. <span>{{</span>registration_number<span>}}</span>
            html = re.sub(r'<span[^>]*>\s*\{\{\s*</span>', '{{', html)
            html = re.sub(r'<span[^>]*>\s*\}\}\s*</span>', '}}', html)
            return html

        def render_page(html):
            return re.sub(r'\{\{\s*([\w_ ]+)\s*\}\}', replacer, normalize_template_html(html))

        pages_html = ''
        for i, page in enumerate(pages):
            is_last = (i == len(pages) - 1)
            style = '' if is_last else 'page-break-after: always;'
            pages_html += f'<div class="ql-page" style="{style}">{render_page(page)}</div>'

        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ margin: 20mm 15mm; }}
                * {{ box-sizing: border-box; }}
                body {{
                    font-family: Arial, sans-serif;
                    font-size: 13px;
                    color: #1f2937;
                    line-height: 1.6;
                    margin: 0;
                    padding: 0;
                }}

                /* ── Headings ── */
                h1 {{ font-size: 20px; font-weight: 700; margin: 10px 0 6px; }}
                h2 {{ font-size: 17px; font-weight: 700; margin: 8px 0 5px; }}
                h3 {{ font-size: 15px; font-weight: 700; margin: 6px 0 4px; }}

                /* ── Paragraphs — Quill wraps every line in <p> ── */
                p {{ margin: 0; padding: 0; min-height: 1.6em; }}

                /* ── Inline formatting ── */
                strong, b {{ font-weight: 700; }}
                em, i     {{ font-style: italic; }}
                u         {{ text-decoration: underline; }}
                s         {{ text-decoration: line-through; }}
                a         {{ color: #2563eb; text-decoration: underline; }}
                span      {{ /* inline styles from Quill (color/background-color) pass through */ }}

                /* ── Quill alignment classes ── */
                .ql-align-center  {{ text-align: center; }}
                .ql-align-right   {{ text-align: right; }}
                .ql-align-justify {{ text-align: justify; }}

                /* ── Quill indent (on both <p> and <li>) ── */
                .ql-indent-1 {{ padding-left: 3em; }}
                .ql-indent-2 {{ padding-left: 6em; }}
                .ql-indent-3 {{ padding-left: 9em; }}
                .ql-indent-4 {{ padding-left: 12em; }}
                .ql-indent-5 {{ padding-left: 15em; }}

                /* ── Lists ── */
                ol, ul {{ padding-left: 1.5em; margin: 4px 0; }}
                li {{ margin: 2px 0; }}
                li.ql-indent-1 {{ padding-left: 3em; }}
                li.ql-indent-2 {{ padding-left: 6em; }}

                /* ── Table ── */
                table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
                td, th {{ border: 1px solid #d1d5db; padding: 6px 10px; }}
                th {{ background: #f1f5f9; font-weight: 600; }}

                /* ── Page break ── */
                .ql-page {{ page-break-after: always; }}
                .ql-page:last-child {{ page-break-after: avoid; }}
            </style>
        </head>
        <body>
            {pages_html}
        </body>
        </html>
        """

        pdf_bytes = HTML(string=full_html).write_pdf()
        filename = f"{product.slug}-performa.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        response['X-Total-Pages'] = str(len(pages))
        return response
