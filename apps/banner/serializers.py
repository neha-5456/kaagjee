"""
CloudServices India - Banner Serializers
"""
from rest_framework import serializers
from .models import Banner


class BannerSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='Product.id', read_only=True, allow_null=True)
    product_slug = serializers.CharField(source='Product.slug', read_only=True, allow_null=True)
    product_title = serializers.CharField(source='Product.title', read_only=True, allow_null=True)
    
    class Meta:
        model = Banner
        fields = ['id', 'title', 'description', 'image', 'display_order', 'created_at', 
                  'product_id', 'product_slug', 'product_title']