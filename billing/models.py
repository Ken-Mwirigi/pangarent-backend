from django.db import models

class MeterReading(models.Model):
    # Notice the quotes around 'properties.Unit'
    unit = models.ForeignKey('properties.Unit', on_delete=models.CASCADE)
    prev_reading = models.DecimalField(max_digits=10, decimal_places=2)
    current_reading = models.DecimalField(max_digits=10, decimal_places=2)
    reading_date = models.DateField()

class Invoice(models.Model):
    # FIX: Notice the quotes around 'tenants.TenantProfile'
    tenant = models.ForeignKey('tenants.TenantProfile', on_delete=models.CASCADE)
    
    # This does NOT need quotes because MeterReading is in the same file
    water_reading = models.OneToOneField(MeterReading, on_delete=models.SET_NULL, null=True)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    is_sent = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default="Unpaid") 
    created_at = models.DateTimeField(auto_now_add=True)

class Payment(models.Model):
    # This does NOT need quotes because Invoice is in the same file
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    mpesa_receipt_number = models.CharField(max_length=50, unique=True) 
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)