from django.db import models
from django.conf import settings

class TenantProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='tenantprofile'
    )
    full_name = models.CharField(max_length=255)
    id_number = models.CharField(max_length=50)
    
    # Optional fields (The tenant can fill these out themselves later during onboarding)
    nationality = models.CharField(max_length=50, default="Kenyan", blank=True)
    marital_status = models.CharField(max_length=20, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.full_name


class Lease(models.Model):
    tenant = models.ForeignKey(TenantProfile, on_delete=models.CASCADE, related_name='leases')
    # Link directly to the Unit model from the properties app
    unit = models.ForeignKey('properties.Unit', on_delete=models.SET_NULL, null=True, related_name='leases')
    
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Financials set during assignment
    rent_amount_at_signing = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Lease: {self.tenant.full_name} -> {self.unit}"