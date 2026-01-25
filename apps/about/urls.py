# urls.py
from django.urls import path
from .views import about_us_api

urlpatterns = [
    path('', about_us_api, name='about-us'),
]
