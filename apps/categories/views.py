"""
CloudServices India - Categories Views & Serializers
=====================================================
Features:
- Category listing with location filter (state, city)
- Subcategory listing with location filter
- Only show categories that have products in selected location
"""
from rest_framework import serializers, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db.models import Count, Q
from .models import Category, Subcategory
from apps.products.models import Product


# ========================
# SERIALIZERS
# ========================

class SubcategorySerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Subcategory
        fields = ['id', 'name', 'name_hi', 'slug', 'description', 'icon', 'products_count']

    def get_products_count(self, obj):
        # Check if annotated value exists (for filtered queries)
        if hasattr(obj, 'filtered_products_count'):
            return obj.filtered_products_count
        # Fall back to model property
        return obj.products_count


class CategorySerializer(serializers.ModelSerializer):
    subcategories_count = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'name_hi', 'slug', 'description', 'icon', 'image', 
                  'is_featured', 'subcategories_count', 'products_count']

    def get_subcategories_count(self, obj):
        if hasattr(obj, 'filtered_subcategories_count'):
            return obj.filtered_subcategories_count
        return obj.subcategories_count

    def get_products_count(self, obj):
        if hasattr(obj, 'filtered_products_count'):
            return obj.filtered_products_count
        return obj.products_count


class CategoryDetailSerializer(CategorySerializer):
    subcategories = SubcategorySerializer(many=True, read_only=True)

    class Meta(CategorySerializer.Meta):
        fields = CategorySerializer.Meta.fields + ['subcategories', 'meta_title', 'meta_description']


class CategoryWithSubcategoriesSerializer(serializers.ModelSerializer):
    """Category with filtered subcategories based on location"""
    subcategories = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'name_hi', 'slug', 'description', 'icon', 'image', 
                  'is_featured', 'products_count', 'subcategories']

    def get_products_count(self, obj):
        if hasattr(obj, 'filtered_products_count'):
            return obj.filtered_products_count
        return obj.products_count

    def get_subcategories(self, obj):
        state_id = self.context.get('state_id')
        city_id = self.context.get('city_id')
        
        subcategories = obj.subcategories.filter(is_active=True)
        
        if state_id or city_id:
            product_filter = Q(products__status='active')
            
            if state_id:
                product_filter &= (
                    Q(products__is_pan_india=True) | 
                    Q(products__available_states__id=state_id)
                )
            
            if city_id:
                product_filter &= (
                    Q(products__is_pan_india=True) | 
                    Q(products__available_cities__id=city_id)
                )
            
            subcategories = subcategories.filter(product_filter).distinct()
            subcategories = subcategories.annotate(
                filtered_products_count=Count(
                    'products',
                    filter=product_filter,
                    distinct=True
                )
            )
        else:
            subcategories = subcategories.annotate(
                filtered_products_count=Count('products', filter=Q(products__status='active'))
            )
        
        return SubcategorySerializer(subcategories, many=True).data


# ========================
# VIEWS
# ========================

class CategoryListView(generics.ListAPIView):
    """
    List all active categories
    
    Query Parameters:
    -----------------
    - state_id: Filter categories that have products in this state
    - state_code: Filter by state code (MH, DL, UP)
    - city_id: Filter categories that have products in this city
    - city_slug: Filter by city slug
    
    Examples:
    ---------
    /categories/                          → All categories
    /categories/?state_id=1               → Categories with products in state 1
    /categories/?state_code=MH            → Categories with products in Maharashtra
    /categories/?city_id=5                → Categories with products in city 5
    /categories/?state_id=1&city_id=5     → Categories with products in state 1 AND city 5
    """
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer

    def get_queryset(self):
        qs = Category.objects.filter(is_active=True)
        
        params = self.request.query_params
        state_id = params.get('state_id')
        state_code = params.get('state_code')
        city_id = params.get('city_id')
        city_slug = params.get('city_slug')
        
        # Build product filter for location
        product_filter = Q(products__status='active')
        has_location_filter = False
        
        if state_id:
            product_filter &= (
                Q(products__is_pan_india=True) | 
                Q(products__available_states__id=state_id)
            )
            has_location_filter = True
        elif state_code:
            product_filter &= (
                Q(products__is_pan_india=True) | 
                Q(products__available_states__code__iexact=state_code)
            )
            has_location_filter = True
        
        if city_id:
            product_filter &= (
                Q(products__is_pan_india=True) | 
                Q(products__available_cities__id=city_id)
            )
            has_location_filter = True
        elif city_slug:
            product_filter &= (
                Q(products__is_pan_india=True) | 
                Q(products__available_cities__slug=city_slug)
            )
            has_location_filter = True
        
        if has_location_filter:
            # Filter categories that have products in the location
            qs = qs.filter(product_filter).distinct()
            
            # Annotate with filtered counts (use different names to avoid conflict with model properties)
            qs = qs.annotate(
                filtered_products_count=Count(
                    'products',
                    filter=product_filter,
                    distinct=True
                ),
                filtered_subcategories_count=Count(
                    'subcategories',
                    filter=Q(subcategories__is_active=True),
                    distinct=True
                )
            )
        else:
            # No location filter - annotate with default counts
            qs = qs.annotate(
                filtered_products_count=Count(
                    'products',
                    filter=Q(products__status='active'),
                    distinct=True
                ),
                filtered_subcategories_count=Count(
                    'subcategories',
                    filter=Q(subcategories__is_active=True),
                    distinct=True
                )
            )
        
        return qs.order_by('display_order', 'name')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        filters = {}
        if request.query_params.get('state_id'):
            filters['state_id'] = request.query_params.get('state_id')
        if request.query_params.get('state_code'):
            filters['state_code'] = request.query_params.get('state_code')
        if request.query_params.get('city_id'):
            filters['city_id'] = request.query_params.get('city_id')
        
        return Response({
            'success': True,
            'filters': filters if filters else None,
            'count': len(serializer.data),
            'data': serializer.data
        })


class FeaturedCategoriesView(generics.ListAPIView):
    """
    List featured categories with optional location filter
    """
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer

    def get_queryset(self):
        qs = Category.objects.filter(is_active=True, is_featured=True)
        
        params = self.request.query_params
        state_id = params.get('state_id')
        city_id = params.get('city_id')
        
        product_filter = Q(products__status='active')
        has_location_filter = False
        
        if state_id:
            product_filter &= (
                Q(products__is_pan_india=True) | 
                Q(products__available_states__id=state_id)
            )
            has_location_filter = True
        
        if city_id:
            product_filter &= (
                Q(products__is_pan_india=True) | 
                Q(products__available_cities__id=city_id)
            )
            has_location_filter = True
        
        if has_location_filter:
            qs = qs.filter(product_filter).distinct()
            qs = qs.annotate(
                filtered_products_count=Count('products', filter=product_filter, distinct=True),
                filtered_subcategories_count=Count('subcategories', filter=Q(subcategories__is_active=True), distinct=True)
            )
        else:
            qs = qs.annotate(
                filtered_products_count=Count('products', filter=Q(products__status='active'), distinct=True),
                filtered_subcategories_count=Count('subcategories', filter=Q(subcategories__is_active=True), distinct=True)
            )
        
        return qs.order_by('display_order', 'name')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': len(serializer.data),
            'data': serializer.data
        })


class CategoryDetailView(generics.RetrieveAPIView):
    """
    Get category with subcategories
    Subcategories are also filtered by location if provided
    """
    permission_classes = [AllowAny]
    queryset = Category.objects.filter(is_active=True)
    lookup_field = 'slug'

    def get_serializer_class(self):
        return CategoryWithSubcategoriesSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['state_id'] = self.request.query_params.get('state_id')
        context['city_id'] = self.request.query_params.get('city_id')
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        })


class SubcategoryListView(generics.ListAPIView):
    """
    List subcategories with optional filters
    
    Query Parameters:
    -----------------
    - category: Category slug to filter subcategories
    - category_id: Category ID to filter subcategories
    - state_id: Filter subcategories that have products in this state
    - state_code: Filter by state code
    - city_id: Filter subcategories that have products in this city
    """
    permission_classes = [AllowAny]
    serializer_class = SubcategorySerializer

    def get_queryset(self):
        qs = Subcategory.objects.filter(is_active=True)
        
        params = self.request.query_params
        
        # Category filter
        category_slug = params.get('category')
        category_id = params.get('category_id')
        
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        elif category_id:
            qs = qs.filter(category_id=category_id)
        
        # Location filters
        state_id = params.get('state_id')
        state_code = params.get('state_code')
        city_id = params.get('city_id')
        
        product_filter = Q(products__status='active')
        has_location_filter = False
        
        if state_id:
            product_filter &= (
                Q(products__is_pan_india=True) | 
                Q(products__available_states__id=state_id)
            )
            has_location_filter = True
        elif state_code:
            product_filter &= (
                Q(products__is_pan_india=True) | 
                Q(products__available_states__code__iexact=state_code)
            )
            has_location_filter = True
        
        if city_id:
            product_filter &= (
                Q(products__is_pan_india=True) | 
                Q(products__available_cities__id=city_id)
            )
            has_location_filter = True
        
        if has_location_filter:
            qs = qs.filter(product_filter).distinct()
            qs = qs.annotate(
                filtered_products_count=Count('products', filter=product_filter, distinct=True)
            )
        else:
            qs = qs.annotate(
                filtered_products_count=Count('products', filter=Q(products__status='active'))
            )
        
        return qs.order_by('display_order', 'name')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        filters = {}
        if request.query_params.get('category'):
            filters['category'] = request.query_params.get('category')
        if request.query_params.get('state_id'):
            filters['state_id'] = request.query_params.get('state_id')
        if request.query_params.get('city_id'):
            filters['city_id'] = request.query_params.get('city_id')
        
        return Response({
            'success': True,
            'filters': filters if filters else None,
            'count': len(serializer.data),
            'data': serializer.data
        })


class CategoriesWithProductsView(APIView):
    """
    Get all categories with their subcategories, filtered by location
    Returns nested structure: Categories → Subcategories
    Only includes categories/subcategories that have products in the location
    
    Query Parameters:
    -----------------
    - state_id: Required - Filter by state
    - city_id: Optional - Filter by city
    
    Example:
    --------
    /categories/with-products/?state_id=1&city_id=5
    """
    permission_classes = [AllowAny]

    def get(self, request):
        state_id = request.query_params.get('state_id')
        state_code = request.query_params.get('state_code')
        city_id = request.query_params.get('city_id')
        
        # Build product filter
        product_filter = Q(status='active')
        
        if state_id:
            product_filter &= (
                Q(is_pan_india=True) | 
                Q(available_states__id=state_id)
            )
        elif state_code:
            product_filter &= (
                Q(is_pan_india=True) | 
                Q(available_states__code__iexact=state_code)
            )
        
        if city_id:
            product_filter &= (
                Q(is_pan_india=True) | 
                Q(available_cities__id=city_id)
            )
        
        # Get products matching the filter
        products = Product.objects.filter(product_filter).distinct()
        
        # Get unique category IDs that have products
        category_ids = products.values_list('category_id', flat=True).distinct()
        
        # Get categories
        categories = Category.objects.filter(
            id__in=category_ids,
            is_active=True
        ).order_by('display_order', 'name')
        
        # Build response
        result = []
        for category in categories:
            # Get subcategories for this category that have products
            subcategory_ids = products.filter(
                category=category
            ).values_list('subcategory_id', flat=True).distinct()
            
            subcategories = Subcategory.objects.filter(
                id__in=subcategory_ids,
                is_active=True
            ).order_by('display_order', 'name')
            
            # Count products per subcategory
            subcategories_data = []
            for subcat in subcategories:
                subcat_products_count = products.filter(
                    category=category,
                    subcategory=subcat
                ).count()
                
                subcategories_data.append({
                    'id': subcat.id,
                    'name': subcat.name,
                    'name_hi': subcat.name_hi,
                    'slug': subcat.slug,
                    'icon': subcat.icon,
                    'products_count': subcat_products_count
                })
            
            # Products without subcategory
            no_subcat_count = products.filter(
                category=category,
                subcategory__isnull=True
            ).count()
            
            result.append({
                'id': category.id,
                'name': category.name,
                'name_hi': category.name_hi,
                'slug': category.slug,
                'icon': category.icon,
                'image': category.image.url if category.image else None,
                'is_featured': category.is_featured,
                'products_count': products.filter(category=category).count(),
                'products_without_subcategory': no_subcat_count,
                'subcategories': subcategories_data
            })
        
        return Response({
            'success': True,
            'location': {
                'state_id': state_id,
                'state_code': state_code,
                'city_id': city_id
            },
            'count': len(result),
            'data': result
        })