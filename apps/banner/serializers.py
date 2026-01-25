"""
CloudServices India - Banner Serializers
"""
from rest_framework import serializers
from .models import Banner


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['id', 'title', 'description', 'image', 'display_order', 'created_at']