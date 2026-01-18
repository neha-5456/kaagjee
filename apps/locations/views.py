"""
CloudServices India - Locations Serializers & Views
"""
from rest_framework import serializers, generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import State, City


# ========================
# SERIALIZERS
# ========================

class CitySerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source='state.name', read_only=True)
    state_code = serializers.CharField(source='state.code', read_only=True)

    class Meta:
        model = City
        fields = ['id', 'name', 'slug', 'tier', 'is_popular', 'state', 'state_name', 'state_code']


class StateSerializer(serializers.ModelSerializer):
    cities_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = State
        fields = ['id', 'name', 'slug', 'code', 'cities_count']


class StateDetailSerializer(StateSerializer):
    cities = CitySerializer(many=True, read_only=True)

    class Meta(StateSerializer.Meta):
        fields = StateSerializer.Meta.fields + ['cities']


# ========================
# VIEWS
# ========================

class StateListView(generics.ListAPIView):
    """List all active states"""
    permission_classes = [AllowAny]
    serializer_class = StateSerializer
    queryset = State.objects.filter(is_active=True)
    search_fields = ['name', 'code']


class StateDetailView(generics.RetrieveAPIView):
    """Get state with its cities"""
    permission_classes = [AllowAny]
    serializer_class = StateDetailSerializer
    queryset = State.objects.filter(is_active=True)
    lookup_field = 'slug'


class CityListView(generics.ListAPIView):
    """List cities, optionally filtered by state"""
    permission_classes = [AllowAny]
    serializer_class = CitySerializer
    search_fields = ['name']

    def get_queryset(self):
        qs = City.objects.filter(is_active=True).select_related('state')
        
        # Filter by state
        state_id = self.request.query_params.get('state_id')
        state_code = self.request.query_params.get('state_code')
        
        if state_id:
            qs = qs.filter(state_id=state_id)
        elif state_code:
            qs = qs.filter(state__code=state_code.upper())
        
        # Filter by tier
        tier = self.request.query_params.get('tier')
        if tier:
            qs = qs.filter(tier=tier)
        
        return qs


class PopularCitiesView(generics.ListAPIView):
    """List popular cities"""
    permission_classes = [AllowAny]
    serializer_class = CitySerializer
    queryset = City.objects.filter(is_active=True, is_popular=True).select_related('state')[:20]
