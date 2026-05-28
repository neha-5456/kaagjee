from rest_framework import serializers
from .models import Privacy

class PrivacySerializer(serializers.ModelSerializer):
    class Meta:
        model = Privacy
        fields = "__all__"