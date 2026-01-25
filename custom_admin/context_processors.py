"""
Custom Admin Context Processors
"""
from django.utils import timezone
from datetime import timedelta


def admin_context(request):
    """
    Add dashboard statistics to admin context
    """
    if not request.path.startswith('/admin/'):
        return {}
    
    try:
        from apps.accounts.models import User
        from apps.products.models import Product
        from apps.orders.models import Order
        from apps.categories.models import Category
        from apps.locations.models import State
        from apps.blog.models import BlogPost
        
        # Calculate date range for recent activity
        week_ago = timezone.now() - timedelta(days=7)
        
        return {
            'user_count': User.objects.count(),
            'product_count': Product.objects.count(),
            'order_count': Order.objects.count(),
            'category_count': Category.objects.count(),
            'state_count': State.objects.count(),
            'blog_count': BlogPost.objects.count(),
            
            # Recent activity (last 7 days)
            'recent_users': User.objects.filter(date_joined__gte=week_ago).count(),
            'recent_products': Product.objects.filter(created_at__gte=week_ago).count(),
            'recent_orders': Order.objects.filter(created_at__gte=week_ago).count(),
        }
    except Exception:
        return {}
