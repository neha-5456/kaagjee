"""
CloudServices India - Blog URLs
"""
from django.urls import path
from .views import (
    BlogPostListView, BlogPostDetailView,
    BlogCategoryListView, BlogTagListView
)

app_name = 'blog'

urlpatterns = [
    path('posts/', BlogPostListView.as_view(), name='post-list'),
    path('posts/<slug:slug>/', BlogPostDetailView.as_view(), name='post-detail'),
    path('categories/', BlogCategoryListView.as_view(), name='category-list'),
    path('tags/', BlogTagListView.as_view(), name='tag-list'),
]