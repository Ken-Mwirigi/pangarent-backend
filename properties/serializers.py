from rest_framework import serializers
from .models import Property, Floor, Unit

class UnitSerializer(serializers.ModelSerializer):
    # Map Django snake_case to React camelCase
    name = serializers.CharField(source='unit_name')
    rentAmount = serializers.DecimalField(source='rent_amount', max_digits=10, decimal_places=2)
    garbageFee = serializers.DecimalField(source='garbage_fee', max_digits=10, decimal_places=2)
    waterPerUnit = serializers.DecimalField(source='water_rate_per_unit', max_digits=10, decimal_places=2)
    isOccupied = serializers.BooleanField(source='is_occupied', read_only=True)
    floorId = serializers.PrimaryKeyRelatedField(source='floor', queryset=Floor.objects.all(), write_only=True)

    class Meta:
        model = Unit
        fields = ['id', 'name', 'rentAmount', 'garbageFee', 'waterPerUnit', 'isOccupied', 'floorId']

class FloorSerializer(serializers.ModelSerializer):
    # This nests the units inside the floor automatically!
    units = UnitSerializer(many=True, read_only=True)
    propertyId = serializers.PrimaryKeyRelatedField(source='property', queryset=Property.objects.all(), write_only=True)
    number = serializers.IntegerField(source='level')

    class Meta:
        model = Floor
        fields = ['id', 'name', 'number', 'propertyId', 'units']

class PropertySerializer(serializers.ModelSerializer):
    # This nests the floors inside the property automatically!
    floors = FloorSerializer(many=True, read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', format="%Y-%m-%d", read_only=True)
    
    class Meta:
        model = Property
        fields = ['id', 'name', 'address', 'city', 'createdAt', 'floors']
        # We don't include landlord here because the backend will automatically assign it