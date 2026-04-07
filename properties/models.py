from django.db import models

class Property(models.Model):
    landlord = models.ForeignKey('accounts.LandlordProfile', on_delete=models.CASCADE, related_name='properties')
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Floor(models.Model):
    property = models.ForeignKey(Property, related_name='floors', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)  # e.g. "Ground Floor"
    level = models.IntegerField()           # e.g. 0, 1, 2

    def __str__(self):
        return f"{self.property.name} - {self.name}"

class Unit(models.Model):
    floor = models.ForeignKey(Floor, related_name='units', on_delete=models.CASCADE)
    unit_name = models.CharField(max_length=50) 
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    garbage_fee = models.DecimalField(max_digits=10, decimal_places=2)
    water_rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2) 
    is_occupied = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.floor.property.name} - {self.unit_name}"