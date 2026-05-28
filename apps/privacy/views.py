from django.shortcuts import render
from .models import Privacy
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializer import PrivacySerializer
# Create your views here.



class PrivacyAPIView(APIView):
    def get(self, request):
        privacy = Privacy.objects.filter(is_active=True).first()
        serializer = PrivacySerializer(privacy)
        print(serializer.data)
        return Response({'privacy': serializer.data})