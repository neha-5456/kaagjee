"""
CloudServices India - Blog Views
"""
from rest_framework import generics, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import BlogPost, BlogCategory, BlogTag
from .serializers import (
    BlogPostListSerializer, BlogPostDetailSerializer,
    BlogCategorySerializer, BlogTagSerializer
)


class BlogPostListView(generics.ListAPIView):
    """List all published blog posts with full details"""
    serializer_class = BlogPostDetailSerializer

    def get_queryset(self):
        queryset = BlogPost.objects.filter(status='published').select_related('author').prefetch_related('categories', 'tags')

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(categories__slug=category)

        # Filter by tag
        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__slug=tag)

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)

        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            paginated_response.data['success'] = True
            paginated_response.data['count'] = queryset.count()
            paginated_response.data['data'] = paginated_response.data.pop('results', [])
            return paginated_response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })


class BlogPostDetailView(generics.RetrieveAPIView):
    """Get blog post detail by slug"""
    serializer_class = BlogPostDetailSerializer
    lookup_field = 'slug'
    
    def get_queryset(self):
        return BlogPost.objects.filter(status='published')
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment views count
        instance.views_count += 1
        instance.save(update_fields=['views_count'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class BlogCategoryListView(generics.ListAPIView):
    """List all active blog categories"""
    queryset = BlogCategory.objects.filter(is_active=True)
    serializer_class = BlogCategorySerializer


class BlogTagListView(generics.ListAPIView):
    """List all blog tags"""
    queryset = BlogTag.objects.all()
    serializer_class = BlogTagSerializer