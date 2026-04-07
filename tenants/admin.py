from django.contrib import admin
from .models import TenantProfile, Lease

@admin.register(TenantProfile)
class TenantProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'id_number')
    search_fields = ('full_name', 'user__email', 'id_number')

@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'unit', 'start_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('tenant__full_name', 'unit__unit_name')