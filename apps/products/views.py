"""
CloudServices India - Product Views & Serializers
==================================================
Features:
- Product listing with filters (category, subcategory, state, city)
- Featured & Popular products
- Product detail with form schema
- Location-based filtering (Pan India support)
"""
from rest_framework import serializers, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from .models import Product, ProductImage, ProductFAQ


# ========================
# SERIALIZERS
# ========================

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'display_order']


class ProductFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFAQ
        fields = ['id', 'question', 'answer', 'display_order']


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, allow_null=True)
    subcategory_slug = serializers.CharField(source='subcategory.slug', read_only=True, allow_null=True)
    discount_percentage = serializers.SerializerMethodField()
    form_fields_count = serializers.SerializerMethodField()
    available_states_list = serializers.SerializerMethodField()
    available_cities_list = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'short_description','description', 'featured_image',
            'category', 'category_name', 'category_slug',
            'subcategory', 'subcategory_name', 'subcategory_slug',
            'full_price', 'half_price', 'original_price', 'discount_percentage',
            'allow_half_payment', 'status', 'is_featured', 'is_popular',
            'is_pan_india', 'available_states_list', 'available_cities_list',
            'processing_time', 'form_fields_count', 'orders_count'
        ]

    def get_discount_percentage(self, obj):
        if obj.original_price and obj.original_price > obj.full_price:
            return int(((obj.original_price - obj.full_price) / obj.original_price) * 100)
        return 0

    def get_form_fields_count(self, obj):
        if obj.form_schema and isinstance(obj.form_schema, list):
            return len(obj.form_schema)
        return 0

    def get_available_states_list(self, obj):
        if obj.is_pan_india:
            return [{'id': None, 'name': 'Pan India', 'code': 'ALL'}]
        return list(obj.available_states.values('id', 'name', 'code'))

    def get_available_cities_list(self, obj):
        if obj.is_pan_india:
            return [{'id': None, 'name': 'All Cities'}]
        return list(obj.available_cities.values('id', 'name', 'state__name', 'state__code'))


class ProductDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True, allow_null=True)
    subcategory_slug = serializers.CharField(source='subcategory.slug', read_only=True, allow_null=True)
    images = ProductImageSerializer(many=True, read_only=True)
    faqs = ProductFAQSerializer(many=True, read_only=True)
    discount_percentage = serializers.SerializerMethodField()
    form_fields_count = serializers.SerializerMethodField()
    available_states_data = serializers.SerializerMethodField()
    available_cities_data = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'short_description', 'description', 'featured_image',
            'category', 'category_name', 'category_slug',
            'subcategory', 'subcategory_name', 'subcategory_slug',
            'is_pan_india', 'available_states', 'available_cities',
            'available_states_data', 'available_cities_data',
            'full_price', 'half_price', 'original_price', 'discount_percentage', 'allow_half_payment',
            'form_title', 'form_description', 'form_schema',
            'status', 'is_featured', 'is_popular',
            'meta_title', 'meta_description', 'meta_keywords',
            'processing_time', 'documents_required',
            'orders_count', 'views_count', 'form_fields_count',
            'images', 'faqs',
            'created_at', 'updated_at'
        ]

    def get_discount_percentage(self, obj):
        if obj.original_price and obj.original_price > obj.full_price:
            return int(((obj.original_price - obj.full_price) / obj.original_price) * 100)
        return 0

    def get_form_fields_count(self, obj):
        if obj.form_schema and isinstance(obj.form_schema, list):
            return len(obj.form_schema)
        return 0

    def get_available_states_data(self, obj):
        if obj.is_pan_india:
            return [{'id': None, 'name': 'Pan India', 'code': 'ALL'}]
        return list(obj.available_states.values('id', 'name', 'code', 'slug'))

    def get_available_cities_data(self, obj):
        if obj.is_pan_india:
            return [{'id': None, 'name': 'All Cities'}]
        return list(obj.available_cities.values('id', 'name', 'slug', 'state__name', 'state__code'))


class FormSchemaSerializer(serializers.ModelSerializer):
    """Returns only form schema for a product - used in order placement"""
    class Meta:
        model = Product
        fields = ['id', 'title', 'form_title', 'form_description', 'form_schema']


# ========================
# VIEWS
# ========================

class ProductListView(generics.ListAPIView):
    """
    List all active products with filtering
    
    Query Parameters:
    -----------------
    - category: Category ID
    - category_slug: Category slug
    - subcategory: Subcategory ID
    - subcategory_slug: Subcategory slug
    - state_id: State ID (filters products available in this state)
    - state_code: State code like MH, DL, UP
    - city_id: City ID (filters products available in this city)
    - city_slug: City slug
    - is_featured: true/false
    - is_popular: true/false
    - min_price: Minimum price
    - max_price: Maximum price
    - search: Search in title, description
    - ordering: full_price, -full_price, orders_count, -orders_count, created_at, -created_at
    
    Examples:
    ---------
    /products/?category=1
    /products/?category_slug=pan-card
    /products/?subcategory=2
    /products/?state_id=1
    /products/?state_code=MH
    /products/?city_id=5
    /products/?state_id=1&city_id=5
    /products/?category=1&state_id=1
    /products/?category_slug=pan-card&state_code=MH&city_id=10
    """
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'short_description', 'description']
    ordering_fields = ['full_price', 'orders_count', 'created_at', 'title', 'views_count']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Product.objects.filter(
            status=Product.Status.ACTIVE
        ).select_related('category', 'subcategory').prefetch_related(
            'available_states', 'available_cities'
        )
        
        params = self.request.query_params
        
        # ========================================
        # CATEGORY FILTERING
        # ========================================
        category_id = params.get('category')
        category_slug = params.get('category_slug')
        
        if category_id:
            qs = qs.filter(category_id=category_id)
        elif category_slug:
            qs = qs.filter(category__slug=category_slug)
        
        # ========================================
        # SUBCATEGORY FILTERING
        # ========================================
        subcategory_id = params.get('subcategory')
        subcategory_slug = params.get('subcategory_slug')
        
        if subcategory_id:
            qs = qs.filter(subcategory_id=subcategory_id)
        elif subcategory_slug:
            qs = qs.filter(subcategory__slug=subcategory_slug)
        
        # ========================================
        # STATE FILTERING
        # ========================================
        state_id = params.get('state_id')
        state_code = params.get('state_code')
        state_slug = params.get('state_slug')
        
        if state_id:
            # Products that are Pan India OR available in this state
            qs = qs.filter(
                Q(is_pan_india=True) | Q(available_states__id=state_id)
            )
        elif state_code:
            qs = qs.filter(
                Q(is_pan_india=True) | Q(available_states__code__iexact=state_code)
            )
        elif state_slug:
            qs = qs.filter(
                Q(is_pan_india=True) | Q(available_states__slug=state_slug)
            )
        
        # ========================================
        # CITY FILTERING
        # ========================================
        city_id = params.get('city_id')
        city_slug = params.get('city_slug')
        
        if city_id:
            # Products that are Pan India OR available in this city
            qs = qs.filter(
                Q(is_pan_india=True) | Q(available_cities__id=city_id)
            )
        elif city_slug:
            qs = qs.filter(
                Q(is_pan_india=True) | Q(available_cities__slug=city_slug)
            )
        
        # ========================================
        # FEATURED / POPULAR FILTERING
        # ========================================
        is_featured = params.get('is_featured')
        is_popular = params.get('is_popular')
        
        if is_featured and is_featured.lower() == 'true':
            qs = qs.filter(is_featured=True)
        
        if is_popular and is_popular.lower() == 'true':
            qs = qs.filter(is_popular=True)
        
        # ========================================
        # PRICE FILTERING
        # ========================================
        min_price = params.get('min_price')
        max_price = params.get('max_price')
        
        if min_price:
            try:
                qs = qs.filter(full_price__gte=float(min_price))
            except ValueError:
                pass
        
        if max_price:
            try:
                qs = qs.filter(full_price__lte=float(max_price))
            except ValueError:
                pass
        
        # Remove duplicates from M2M joins
        return qs.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })


class FeaturedProductsView(generics.ListAPIView):
    """List featured products"""
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        qs = Product.objects.filter(
            status=Product.Status.ACTIVE,
            is_featured=True
        ).select_related('category', 'subcategory')[:12]
        
        # Optional: Filter by location
        state_id = self.request.query_params.get('state_id')
        city_id = self.request.query_params.get('city_id')
        
        if state_id:
            qs = qs.filter(Q(is_pan_india=True) | Q(available_states__id=state_id)).distinct()
        
        if city_id:
            qs = qs.filter(Q(is_pan_india=True) | Q(available_cities__id=city_id)).distinct()
        
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': len(serializer.data),
            'data': serializer.data
        })


class PopularProductsView(generics.ListAPIView):
    """List popular products"""
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        qs = Product.objects.filter(
            status=Product.Status.ACTIVE,
            is_popular=True
        ).select_related('category', 'subcategory').order_by('-orders_count')[:12]
        
        # Optional: Filter by location
        state_id = self.request.query_params.get('state_id')
        city_id = self.request.query_params.get('city_id')
        
        if state_id:
            qs = qs.filter(Q(is_pan_india=True) | Q(available_states__id=state_id)).distinct()
        
        if city_id:
            qs = qs.filter(Q(is_pan_india=True) | Q(available_cities__id=city_id)).distinct()
        
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': len(serializer.data),
            'data': serializer.data
        })


class ProductDetailView(generics.RetrieveAPIView):
    """Get product detail by slug"""
    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer
    queryset = Product.objects.filter(status=Product.Status.ACTIVE)
    lookup_field = 'slug'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment views
        Product.objects.filter(pk=instance.pk).update(views_count=instance.views_count + 1)
        serializer = self.get_serializer(instance)
        return Response({'success': True, 'data': serializer.data})


class ProductFormSchemaView(generics.RetrieveAPIView):
    """Get only form schema for a product"""
    permission_classes = [AllowAny]
    serializer_class = FormSchemaSerializer
    queryset = Product.objects.filter(status=Product.Status.ACTIVE)
    lookup_field = 'slug'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({'success': True, 'data': serializer.data})


class ProductsByCategoryView(generics.ListAPIView):
    """
    List products by category slug
    
    URL: /products/by-category/<category_slug>/
    Optional Query Params: state_id, city_id, subcategory
    """
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        category_slug = self.kwargs.get('category_slug')
        qs = Product.objects.filter(
            status=Product.Status.ACTIVE,
            category__slug=category_slug
        ).select_related('category', 'subcategory')
        
        params = self.request.query_params
        
        # Subcategory filter
        subcategory_id = params.get('subcategory')
        subcategory_slug = params.get('subcategory_slug')
        
        if subcategory_id:
            qs = qs.filter(subcategory_id=subcategory_id)
        elif subcategory_slug:
            qs = qs.filter(subcategory__slug=subcategory_slug)
        
        # State filter
        state_id = params.get('state_id')
        state_code = params.get('state_code')
        
        if state_id:
            qs = qs.filter(Q(is_pan_india=True) | Q(available_states__id=state_id))
        elif state_code:
            qs = qs.filter(Q(is_pan_india=True) | Q(available_states__code__iexact=state_code))
        
        # City filter
        city_id = params.get('city_id')
        
        if city_id:
            qs = qs.filter(Q(is_pan_india=True) | Q(available_cities__id=city_id))
        
        return qs.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'category_slug': self.kwargs.get('category_slug'),
            'count': len(serializer.data),
            'data': serializer.data
        })


class ProductsByLocationView(generics.ListAPIView):
    """
    List products available in a specific location
    
    URL: /products/by-location/
    Required: state_id OR state_code
    Optional: city_id, category, subcategory
    """
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        params = self.request.query_params
        
        qs = Product.objects.filter(
            status=Product.Status.ACTIVE
        ).select_related('category', 'subcategory')
        
        # State filter (required for this endpoint)
        state_id = params.get('state_id')
        state_code = params.get('state_code')
        
        if state_id:
            qs = qs.filter(Q(is_pan_india=True) | Q(available_states__id=state_id))
        elif state_code:
            qs = qs.filter(Q(is_pan_india=True) | Q(available_states__code__iexact=state_code))
        else:
            # If no state provided, return empty or all pan-india
            qs = qs.filter(is_pan_india=True)
        
        # City filter
        city_id = params.get('city_id')
        if city_id:
            qs = qs.filter(Q(is_pan_india=True) | Q(available_cities__id=city_id))
        
        # Category filter
        category_id = params.get('category')
        category_slug = params.get('category_slug')
        
        if category_id:
            qs = qs.filter(category_id=category_id)
        elif category_slug:
            qs = qs.filter(category__slug=category_slug)
        
        # Subcategory filter
        subcategory_id = params.get('subcategory')
        if subcategory_id:
            qs = qs.filter(subcategory_id=subcategory_id)
        
        return qs.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Get location info for response
        state_id = request.query_params.get('state_id')
        state_code = request.query_params.get('state_code')
        city_id = request.query_params.get('city_id')
        
        return Response({
            'success': True,
            'filters': {
                'state_id': state_id,
                'state_code': state_code,
                'city_id': city_id
            },
            'count': len(serializer.data),
            'data': serializer.data
        })


class CheckProductAvailabilityView(APIView):
    """
    Check if a product is available in a specific location
    
    POST /products/<slug>/check-availability/
    Body: {"state_id": 1, "city_id": 5}
    """
    permission_classes = [AllowAny]

    def post(self, request, slug):
        try:
            product = Product.objects.get(slug=slug, status=Product.Status.ACTIVE)
        except Product.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Product not found'
            }, status=404)
        
        state_id = request.data.get('state_id')
        city_id = request.data.get('city_id')
        
        # Check availability
        is_available = False
        reason = ''
        
        if product.is_pan_india:
            is_available = True
            reason = 'Product is available Pan India'
        else:
            # Check state
            if state_id:
                state_available = product.available_states.filter(id=state_id).exists()
                if not state_available:
                    reason = 'Product not available in selected state'
                else:
                    is_available = True
                    reason = 'Product available in selected state'
            
            # Check city (more specific)
            if city_id and is_available:
                city_available = product.available_cities.filter(id=city_id).exists()
                if not city_available:
                    # Check if any city is specified or it's state-level
                    if product.available_cities.exists():
                        is_available = False
                        reason = 'Product not available in selected city'
                    else:
                        reason = 'Product available in entire state'
                else:
                    reason = 'Product available in selected city'
        
        return Response({
            'success': True,
            'data': {
                'product_slug': slug,
                'product_title': product.title,
                'is_available': is_available,
                'is_pan_india': product.is_pan_india,
                'reason': reason,
                'checked_location': {
                    'state_id': state_id,
                    'city_id': city_id
                }
            }
        })