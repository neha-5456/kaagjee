from django.shortcuts import render
from .models import Policy
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializer import PolicySerializer
# Create your views here.



class PolicyAPIView(APIView):
    def get(self, request):
        policy = Policy.objects.filter(is_active=True).first()
        serializer = PolicySerializer(policy)
        print(serializer.data)
        return Response({'policy': serializer.data})