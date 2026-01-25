# views.py
from django.http import JsonResponse
from .models import AboutUs

def about_us_api(request):
    about = AboutUs.objects.filter(is_active=True).first()
    if not about:
        return JsonResponse({"message": "No About Us content found."}, status=404)

    return JsonResponse({
        "title": about.title,
        "description": about.description,
    })
