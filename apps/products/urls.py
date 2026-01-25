"""
CloudServices India - Products URLs
===================================
"""
from django.urls import path
from .views import (
    ProductListView,
    FeaturedProductsView,
    PopularProductsView,
    ProductDetailView,
    ProductFormSchemaView,
    ProductsByCategoryView,
    ProductsByLocationView,
    CheckProductAvailabilityView,
)

app_name = 'products'

urlpatterns = [
    # List all products with filters
    # GET /products/
    # Filters: category, category_slug, subcategory, subcategory_slug, 
    #          state_id, state_code, city_id, city_slug,
    #          is_featured, is_popular, min_price, max_price, search
    path('', ProductListView.as_view(), name='product-list'),
    
    # Featured products
    # GET /products/featured/
    # Optional: state_id, city_id
    path('featured/', FeaturedProductsView.as_view(), name='featured-products'),
    
    # Popular products  
    # GET /products/popular/
    # Optional: state_id, city_id
    path('popular/', PopularProductsView.as_view(), name='popular-products'),
    
    # Products by location
    # GET /products/by-location/?state_id=1&city_id=5
    # Required: state_id OR state_code
    # Optional: city_id, category, subcategory
    path('by-location/', ProductsByLocationView.as_view(), name='products-by-location'),
    
    # Products by category
    # GET /products/by-category/pan-card/
    # Optional: subcategory, state_id, city_id
    path('by-category/<slug:category_slug>/', ProductsByCategoryView.as_view(), name='products-by-category'),
    
    # Product detail
    # GET /products/<slug>/
    path('<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
    
    # Product form schema only
    # GET /products/<slug>/form-schema/
    path('<slug:slug>/form-schema/', ProductFormSchemaView.as_view(), name='product-form-schema'),
    
    # Check product availability in location
    # POST /products/<slug>/check-availability/
    # Body: {"state_id": 1, "city_id": 5}
    path('<slug:slug>/check-availability/', CheckProductAvailabilityView.as_view(), name='check-availability'),
]