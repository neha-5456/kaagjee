"""
CloudServices India - Categories URLs
=====================================
"""
from django.urls import path
from .views import (
    CategoryListView,
    FeaturedCategoriesView,
    CategoryDetailView,
    SubcategoryListView,
    CategoriesWithProductsView,
)

app_name = 'categories'

urlpatterns = [
    # List all categories with location filter
    # GET /categories/
    # GET /categories/?state_id=1
    # GET /categories/?state_code=MH
    # GET /categories/?city_id=5
    # GET /categories/?state_id=1&city_id=5
    path('', CategoryListView.as_view(), name='category-list'),
    
    # Featured categories
    # GET /categories/featured/
    # GET /categories/featured/?state_id=1&city_id=5
    path('featured/', FeaturedCategoriesView.as_view(), name='featured-categories'),
    
    # Subcategories list with filters
    # GET /categories/subcategories/?category=pan-card
    # GET /categories/subcategories/?category=pan-card&state_id=1
    # GET /categories/subcategories/?category_id=1&state_id=1&city_id=5
    path('subcategories/', SubcategoryListView.as_view(), name='subcategory-list'),
    
    # Categories with products - nested structure
    # GET /categories/with-products/?state_id=1
    # GET /categories/with-products/?state_id=1&city_id=5
    # Returns: Categories → Subcategories with product counts
    path('with-products/', CategoriesWithProductsView.as_view(), name='categories-with-products'),
    
    # Category detail with subcategories
    # GET /categories/pan-card/
    # GET /categories/pan-card/?state_id=1&city_id=5
    path('<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),
]