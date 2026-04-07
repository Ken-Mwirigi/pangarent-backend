from django.contrib import admin
from .models import Property, Floor, Unit

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    # Updated to use address and city instead of location
    list_display = ('name', 'landlord', 'address', 'city', 'created_at')
    search_fields = ('name', 'address', 'city', 'landlord__full_name')
    list_filter = ('city', 'created_at')

@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    # Added 'name' since we added it to the Floor model
    list_display = ('property', 'name', 'level')
    list_filter = ('property',)
    search_fields = ('name', 'property__name')

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    # Added garbage_fee so you can see all financials at a glance
    list_display = ('unit_name', 'floor', 'rent_amount', 'garbage_fee', 'water_rate_per_unit', 'is_occupied')
    list_filter = ('is_occupied', 'floor__property')
    search_fields = ('unit_name', 'floor__property__name')