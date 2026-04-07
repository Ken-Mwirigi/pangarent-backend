from rest_framework import serializers
from .models import MeterReading, Invoice
from properties.models import Unit
from tenants.models import TenantProfile

class InvoiceGenerationSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField()
    tenant_id = serializers.IntegerField()
    prev_reading = serializers.DecimalField(max_digits=10, decimal_places=2)
    current_reading = serializers.DecimalField(max_digits=10, decimal_places=2)
    water_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    rent_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    garbage_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    is_draft = serializers.BooleanField(default=True) # True = Draft, False = Send Now

    def save(self):
        unit = Unit.objects.get(id=self.validated_data['unit_id'])
        tenant = TenantProfile.objects.get(id=self.validated_data['tenant_id'])
        
        # 1. Create the Meter Reading
        from django.utils import timezone
        reading = MeterReading.objects.create(
            unit=unit,
            prev_reading=self.validated_data['prev_reading'],
            current_reading=self.validated_data['current_reading'],
            reading_date=timezone.now().date()
        )

        # 2. Create the Invoice
        status = 'Draft' if self.validated_data['is_draft'] else 'Unpaid'
        
        invoice = Invoice.objects.create(
            tenant=tenant,
            water_reading=reading,
            amount_due=self.validated_data['total_amount'],
            is_sent=not self.validated_data['is_draft'],
            status=status
        )

        # 3. If the landlord clicked "Send", fire off the email!
        if invoice.is_sent:
            self._send_invoice_email(tenant, invoice)
            
        return invoice

    def _send_invoice_email(self, tenant, invoice):
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Calculate consumption safely
        consumption = invoice.water_reading.current_reading - invoice.water_reading.prev_reading
        
        message = f'''Hello {tenant.full_name},

Your new invoice for {invoice.created_at.strftime('%B %Y')} is ready.

--- BILLING SUMMARY ---
Rent: KES {self.validated_data['rent_amount']}
Water ({consumption} units): KES {self.validated_data['water_cost']}
Garbage: KES {self.validated_data['garbage_fee']}
-----------------------
TOTAL DUE: KES {invoice.amount_due}

Please log in to your tenant dashboard to view the full breakdown and pay via M-Pesa.

Thank you,
PangaRent Management
'''
        send_mail(
            subject=f'New Invoice Available - {invoice.created_at.strftime("%B %Y")}',
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[tenant.user.email],
            fail_silently=False,
        )

# billing/serializers.py
from rest_framework import serializers
from .models import MeterReading, Invoice, Payment
from properties.models import Unit
from tenants.models import TenantProfile, Lease

# ... [Keep your existing InvoiceGenerationSerializer here] ...

class TenantDashboardStatsSerializer(serializers.Serializer):
    """Formats the aggregated stats for the top of the dashboard."""
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    overpayment = serializers.DecimalField(max_digits=12, decimal_places=2)
    unread_notifications = serializers.IntegerField()
    invoice_id_to_pay = serializers.IntegerField(allow_null=True)

# billing/serializers.py
class InvoiceHistorySerializer(serializers.ModelSerializer):
    tenantName = serializers.CharField(source='tenant.full_name', read_only=True)
    propertyName = serializers.SerializerMethodField() # <-- NEW
    floorName = serializers.SerializerMethodField()    # <-- NEW
    unitName = serializers.SerializerMethodField()
    month = serializers.SerializerMethodField()
    consumption = serializers.SerializerMethodField()
    totalAmount = serializers.DecimalField(source='amount_due', max_digits=12, decimal_places=2, read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d")
    receipt_number = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        # <-- Added propertyName and floorName to the fields list -->
        fields = ['id', 'tenantName', 'propertyName', 'floorName', 'unitName', 'month', 'consumption', 'totalAmount', 'status', 'created_at', 'receipt_number']

    # <-- NEW: Get Property Name -->
    def get_propertyName(self, obj):
        lease = Lease.objects.filter(tenant=obj.tenant).first()
        return lease.unit.floor.property.name if lease and getattr(lease.unit, 'floor', None) else "N/A"

    # <-- NEW: Get Floor Name -->
    def get_floorName(self, obj):
        lease = Lease.objects.filter(tenant=obj.tenant).first()
        return lease.unit.floor.name if lease and getattr(lease.unit, 'floor', None) else "N/A"

    def get_unitName(self, obj):
        lease = Lease.objects.filter(tenant=obj.tenant).first()
        return lease.unit.unit_name if lease else "N/A"

    def get_month(self, obj):
        if obj.water_reading:
            return obj.water_reading.reading_date.strftime('%B %Y')
        return obj.created_at.strftime('%B %Y')

    def get_consumption(self, obj):
        if obj.water_reading:
            return obj.water_reading.current_reading - obj.water_reading.prev_reading
        return 0
        
    def get_receipt_number(self, obj):
        if obj.status.lower() == 'paid':
            payment = Payment.objects.filter(invoice=obj).first()
            return payment.mpesa_receipt_number if payment else None
        return None