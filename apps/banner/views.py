"""
CloudServices India - Banner Views
"""
from rest_framework import generics
from .models import Banner
from .serializers import BannerSerializer


class BannerListView(generics.ListAPIView):
    """List all active banners"""
    serializer_class = BannerSerializer
    
    def get_queryset(self):
        return Banner.objects.filter(is_active=True).order_by('display_order', '-created_at')