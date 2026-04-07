from django.contrib import admin
from .models import MeterReading, Invoice, Payment

@admin.register(MeterReading)
class MeterReadingAdmin(admin.ModelAdmin):
    list_display = ('unit', 'reading_date', 'prev_reading', 'current_reading')
    list_filter = ('reading_date',)
    search_fields = ('unit__unit_name',)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'amount_due', 'status', 'is_sent', 'created_at')
    list_filter = ('status', 'is_sent')
    search_fields = ('tenant__user__email',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('mpesa_receipt_number', 'invoice', 'amount', 'payment_date')
    search_fields = ('mpesa_receipt_number', 'invoice__tenant__user__email')