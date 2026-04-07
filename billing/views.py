import os
import requests
from datetime import datetime, date # Fixed datetime import!
from django.utils import timezone
from django.db.models import Sum, Q

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from tenants.models import Lease, TenantProfile
from properties.models import Unit
from accounts.models import LandlordProfile
from notifications.models import Notification

from .models import Invoice, MeterReading, Payment
from .serializers import TenantDashboardStatsSerializer, InvoiceHistorySerializer
from .utils import get_mpesa_access_token, generate_mpesa_password, format_phone_number


class DraftBillingListView(APIView):
    """
    THE BILLING ENGINE:
    Continuous Forward Billing. Looks at the latest invoice.
    If paid, instantly queues up a draft for the next month.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            landlord = LandlordProfile.objects.get(user=request.user)
        except LandlordProfile.DoesNotExist:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        active_leases = Lease.objects.filter(
            unit__floor__property__landlord=landlord,
            is_active=True
        ).select_related('tenant', 'unit')

        billing_records = []

        for lease in active_leases:
            # 1. Grab the absolute newest invoice for this tenant
            latest_invoice = Invoice.objects.filter(tenant=lease.tenant).order_by('-created_at').first()

            if latest_invoice and latest_invoice.status.lower() in ['draft', 'unpaid']:
                # ACTION REQUIRED: The current bill is not settled yet. Show it.
                consumption = latest_invoice.water_reading.current_reading - latest_invoice.water_reading.prev_reading if latest_invoice.water_reading else 0
                water_cost = (consumption * lease.unit.water_rate_per_unit) if consumption > 0 else 0
                
                # Get the month string from the invoice
                month_str = latest_invoice.water_reading.reading_date.strftime('%B %Y') if latest_invoice.water_reading else latest_invoice.created_at.strftime('%B %Y')

                billing_records.append({
                    "id": str(latest_invoice.id),
                    "tenantId": str(lease.tenant.id),
                    "tenantName": lease.tenant.full_name,
                    "unitId": str(lease.unit.id),
                    "unitName": lease.unit.unit_name,
                    "month": month_str,
                    "previousWaterReading": latest_invoice.water_reading.prev_reading if latest_invoice.water_reading else 0,
                    "currentWaterReading": latest_invoice.water_reading.current_reading if latest_invoice.water_reading else 0,
                    "waterConsumption": consumption,
                    "waterPerUnit": lease.unit.water_rate_per_unit, 
                    "rent": lease.rent_amount_at_signing,
                    "garbageFee": lease.unit.garbage_fee,
                    "waterCost": water_cost,
                    "totalAmount": latest_invoice.amount_due,
                    "status": latest_invoice.status.lower() 
                })
            else:
                # QUEUE NEXT MONTH: The tenant is fully paid up! Prep the next cycle.
                last_reading = MeterReading.objects.filter(unit=lease.unit).order_by('-reading_date').first()
                prev_reading = last_reading.current_reading if last_reading else 0

                # Calculate the Target Month
                if latest_invoice:
                    # Look at the paid invoice, and add 1 month to the calendar
                    last_date = latest_invoice.water_reading.reading_date if latest_invoice.water_reading else latest_invoice.created_at.date()
                    next_month = last_date.month % 12 + 1
                    next_year = last_date.year + (last_date.month // 12)
                    target_date = date(next_year, next_month, 1) # Using the fixed 'date' import
                    month_str = target_date.strftime('%B %Y')
                else:
                    # Brand new tenant, never billed before. Use current month.
                    month_str = timezone.now().strftime('%B %Y')

                # Calculate any Overpayments to apply as a discount
                total_billed = Invoice.objects.filter(tenant=lease.tenant).aggregate(Sum('amount_due'))['amount_due__sum'] or 0
                total_paid = Payment.objects.filter(invoice__tenant=lease.tenant).aggregate(Sum('amount'))['amount__sum'] or 0
                overpayment = max(0, total_paid - total_billed)

                base_amount = lease.rent_amount_at_signing + lease.unit.garbage_fee
                adjusted_amount = max(0, base_amount - overpayment)

                billing_records.append({
                    "id": f"draft-{lease.id}", 
                    "tenantId": str(lease.tenant.id),
                    "tenantName": lease.tenant.full_name,
                    "unitId": str(lease.unit.id),
                    "unitName": lease.unit.unit_name,
                    "month": month_str, 
                    "previousWaterReading": prev_reading,
                    "currentWaterReading": 0,
                    "waterConsumption": 0,
                    "waterPerUnit": lease.unit.water_rate_per_unit, 
                    "rent": lease.rent_amount_at_signing,
                    "garbageFee": lease.unit.garbage_fee,
                    "waterCost": 0,
                    "totalAmount": adjusted_amount, 
                    "status": "pending_input" 
                })

        # Sort so un-actioned drafts sit at the top of the queue
        billing_records.sort(key=lambda x: x['status'] != 'pending_input')
        return Response(billing_records, status=status.HTTP_200_OK)


class GenerateInvoiceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        unit_id = data.get('unit_id')
        tenant_id = data.get('tenant_id')
        is_draft = data.get('is_draft', True)
        reading_date = data.get('reading_date')
        
        raw_invoice_id = data.get('invoice_id')
        invoice_id = None if str(raw_invoice_id).startswith('draft-') else raw_invoice_id
        
        try:
            unit = Unit.objects.get(id=unit_id)
            tenant = TenantProfile.objects.get(id=tenant_id)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        dt = datetime.strptime(reading_date, "%Y-%m-%d")

        # Recalculate overpayment dynamically safely
        if invoice_id:
            total_billed = Invoice.objects.filter(tenant=tenant).exclude(id=invoice_id).aggregate(Sum('amount_due'))['amount_due__sum'] or 0
        else:
            total_billed = Invoice.objects.filter(tenant=tenant).aggregate(Sum('amount_due'))['amount_due__sum'] or 0
            
        total_paid = Payment.objects.filter(invoice__tenant=tenant).aggregate(Sum('amount'))['amount__sum'] or 0
        overpayment = max(0, total_paid - total_billed)

        raw_total = data.get('total_amount')
        adjusted_total = max(0, raw_total - overpayment)

        invoice = None
        
        if invoice_id:
            invoice = Invoice.objects.filter(id=invoice_id).first()
            if invoice:
                old_month = invoice.water_reading.reading_date.month if invoice.water_reading else invoice.created_at.month
                old_year = invoice.water_reading.reading_date.year if invoice.water_reading else invoice.created_at.year
                if old_month != dt.month or old_year != dt.year:
                    invoice = None 
            
        if not invoice:
            invoice = Invoice.objects.filter(
                tenant=tenant,
                water_reading__reading_date__month=dt.month,
                water_reading__reading_date__year=dt.year
            ).first()

        if invoice:
            # ---> THE LEDGER LOCK <---
            if invoice.status.lower() == 'paid':
                return Response({
                    "error": f"A paid invoice for {dt.strftime('%B %Y')} already exists. You cannot overwrite a settled ledger."
                }, status=status.HTTP_400_BAD_REQUEST)

            if invoice.water_reading:
                invoice.water_reading.current_reading = data.get('current_reading')
                invoice.water_reading.prev_reading = data.get('prev_reading')
                invoice.water_reading.reading_date = dt.date()
                invoice.water_reading.save()
            else:
                new_reading = MeterReading.objects.create(
                    unit=unit,
                    prev_reading=data.get('prev_reading', 0),
                    current_reading=data.get('current_reading'),
                    reading_date=dt.date()
                )
                invoice.water_reading = new_reading

            invoice.amount_due = adjusted_total
            invoice.is_sent = not is_draft
            invoice.status = 'Draft' if is_draft else 'Unpaid'
            invoice.save()
        else:
            reading = MeterReading.objects.create(
                unit=unit,
                prev_reading=data.get('prev_reading'),
                current_reading=data.get('current_reading'),
                reading_date=dt.date()
            )
            invoice = Invoice.objects.create(
                tenant=tenant,
                water_reading=reading,
                amount_due=adjusted_total,
                is_sent=not is_draft,
                status='Draft' if is_draft else 'Unpaid'
            )

        if invoice.is_sent:
            from django.core.mail import send_mail
            from django.conf import settings
            
            consumption = invoice.water_reading.current_reading - invoice.water_reading.prev_reading
            overpayment_note = f"\n*An overpayment credit of KES {overpayment} was applied to this bill.*" if overpayment > 0 else ""

            # Calculate True Balance for the Email
            final_billed = Invoice.objects.filter(tenant=tenant).aggregate(Sum('amount_due'))['amount_due__sum'] or 0
            final_paid = Payment.objects.filter(invoice__tenant=tenant).aggregate(Sum('amount'))['amount__sum'] or 0
            true_balance = max(0, final_billed - final_paid)

            message = f'''Hello {tenant.full_name},

Your new invoice for {dt.strftime('%B %Y')} is ready.

--- THIS MONTH'S CHARGES ---
Rent: KES {data.get('rent_amount')}
Water ({consumption} units): KES {data.get('water_cost')}
Garbage: KES {data.get('garbage_fee')}
-----------------------
SUBTOTAL: KES {raw_total}{overpayment_note}
=======================
THIS INVOICE TOTAL: KES {invoice.amount_due}

YOUR OVERALL ACCOUNT BALANCE TO PAY: KES {true_balance}

Please log in to your tenant dashboard to pay via M-Pesa.

Thank you,
PangaRent Management
'''
            try:
                send_mail(
                    subject=f'New Invoice Available - {dt.strftime("%B %Y")}',
                    message=message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[tenant.user.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Email failed to send: {e}")

            Notification.objects.create(
                user=tenant.user,
                notification_type='email',
                purpose='billing',
                message=f"Invoice email sent to {tenant.user.email}",
                is_read=True 
            )

            Notification.objects.create(
                user=tenant.user,
                notification_type='in_app',
                purpose='billing',
                message=f"Your invoice for {dt.strftime('%B %Y')} is ready. Total due: KES {invoice.amount_due}.",
                is_read=False 
            )

        return Response({"message": "Billing processed successfully", "status": invoice.status}, status=status.HTTP_200_OK)


class InvoiceManageView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, invoice_id):
        try:
            invoice = Invoice.objects.get(id=invoice_id)
            if invoice.water_reading:
                invoice.water_reading.delete()
            invoice.delete()
            return Response({"message": "Invoice deleted successfully"}, status=status.HTTP_200_OK)
        except Invoice.DoesNotExist:
            return Response({"error": "Invoice not found"}, status=status.HTTP_404_NOT_FOUND)


class PreviousReadingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unit_id = request.query_params.get('unit_id')
        date_str = request.query_params.get('date')
        
        if not unit_id or not date_str:
            return Response({"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            last_reading = MeterReading.objects.filter(
                unit_id=unit_id,
                reading_date__lt=dt
            ).order_by('-reading_date').first()
            
            prev_reading = last_reading.current_reading if last_reading else 0
            return Response({"previous_reading": prev_reading}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InitiateSTKPushView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        invoice_id = request.data.get('invoice_id')
        raw_phone = request.data.get('phone_number')

        if not invoice_id or not raw_phone:
            return Response({"error": "Invoice ID and Phone Number are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tenant_profile = TenantProfile.objects.get(user=request.user)
            invoice = Invoice.objects.get(id=invoice_id, tenant=tenant_profile)
        except (TenantProfile.DoesNotExist, Invoice.DoesNotExist):
            return Response({"error": "Invalid invoice or unauthorized."}, status=status.HTTP_404_NOT_FOUND)

        # TRUE BALANCE LOGIC
        total_billed = Invoice.objects.filter(tenant=tenant_profile).aggregate(Sum('amount_due'))['amount_due__sum'] or 0
        total_paid = Payment.objects.filter(invoice__tenant=tenant_profile).aggregate(Sum('amount'))['amount__sum'] or 0
        true_balance = int(total_billed - total_paid)

        if true_balance <= 0:
            return Response({"error": "Your account balance is fully cleared."}, status=status.HTTP_400_BAD_REQUEST)

        amount = true_balance 
        phone_number = format_phone_number(raw_phone)
        
        access_token = get_mpesa_access_token()
        if not access_token:
            return Response({"error": "Failed to authenticate with M-Pesa."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        shortcode = os.getenv('MPESA_SHORTCODE') 
        till_number = os.getenv('MPESA_TILL_NUMBER') 
        passkey = os.getenv('MPESA_PASSKEY')
        password = generate_mpesa_password(shortcode, passkey, timestamp)

        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Don't forget to update your Ngrok URL when testing!
        callback_url = "https://nongeographical-hoveringly-lovie.ngrok-free.dev/api/billing/mpesa/callback/"

        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": till_number,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": f"INV-{invoice.id}",
            "TransactionDesc": "Rent Payment"
        }

        try:
            response = requests.post(api_url, json=payload, headers=headers)
            response_data = response.json()

            if response_data.get('ResponseCode') == '0':
                checkout_id = response_data.get('CheckoutRequestID')

                Payment.objects.create(
                    invoice=invoice,
                    amount=amount,
                    mpesa_receipt_number=checkout_id 
                )

                return Response({
                    "message": "Payment prompt sent to your phone. Please enter your PIN.",
                    "checkout_id": checkout_id
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": response_data.get('errorMessage', 'Failed to initiate STK Push.')
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TenantDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            tenant = TenantProfile.objects.get(user=request.user)
        except TenantProfile.DoesNotExist:
            return Response({"error": "Tenant profile not found."}, status=status.HTTP_404_NOT_FOUND)

        unpaid_invoices = Invoice.objects.filter(tenant=tenant, status__iexact='unpaid')
        
        total_billed = Invoice.objects.filter(tenant=tenant).aggregate(Sum('amount_due'))['amount_due__sum'] or 0
        total_paid = Payment.objects.filter(invoice__tenant=tenant).aggregate(Sum('amount'))['amount__sum'] or 0
        
        total_balance = max(0, total_billed - total_paid)
        overpayment = max(0, total_paid - total_billed)

        unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()

        target_invoice = unpaid_invoices.order_by('created_at').first()
        invoice_id_to_pay = target_invoice.id if target_invoice else None

        data = {
            "balance": total_balance,
            "overpayment": overpayment,
            "unread_notifications": unread_notifications,
            "invoice_id_to_pay": invoice_id_to_pay
        }
        
        serializer = TenantDashboardStatsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InvoiceHistoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        landlord = LandlordProfile.objects.filter(user=request.user).first()
        tenant_profile = TenantProfile.objects.filter(user=request.user).first()

        if landlord:
            from properties.models import Unit
            landlord_units = Unit.objects.filter(floor__property__landlord=landlord)
            tenant_ids = Lease.objects.filter(unit__in=landlord_units).values_list('tenant_id', flat=True)
            all_invoices = Invoice.objects.filter(
                tenant_id__in=tenant_ids
            ).select_related('tenant', 'water_reading').order_by('-created_at')

        elif tenant_profile:
            all_invoices = Invoice.objects.filter(
                tenant=tenant_profile
            ).select_related('tenant', 'water_reading').order_by('-created_at')
        else:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = InvoiceHistorySerializer(all_invoices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MpesaCallbackView(APIView):
    permission_classes = [AllowAny] 

    def post(self, request):
        callback_data = request.data
        body = callback_data.get('Body', {}).get('stkCallback', {})
        result_code = body.get('ResultCode')
        checkout_id = body.get('CheckoutRequestID')

        if result_code == 0:
            meta = body.get('CallbackMetadata', {}).get('Item', [])
            receipt_number = next((item['Value'] for item in meta if item['Name'] == 'MpesaReceiptNumber'), None)
            amount_paid = next((item['Value'] for item in meta if item['Name'] == 'Amount'), None)
            
            payment = Payment.objects.filter(mpesa_receipt_number=checkout_id).first()

            if payment:
                payment.mpesa_receipt_number = receipt_number
                payment.amount = amount_paid
                payment.save()

                tenant = payment.invoice.tenant
                total_billed = Invoice.objects.filter(tenant=tenant).aggregate(Sum('amount_due'))['amount_due__sum'] or 0
                total_paid = Payment.objects.filter(invoice__tenant=tenant).aggregate(Sum('amount'))['amount__sum'] or 0
                
                if total_paid >= total_billed:
                    Invoice.objects.filter(tenant=tenant, status__iexact='unpaid').update(status='paid')
                else:
                    payment.invoice.status = 'paid'
                    payment.invoice.save()

                # 1. Notify the Tenant (You already have this)
                Notification.objects.create(
                    user=tenant.user,
                    notification_type='in_app',
                    purpose='payment',
                    message=f"Your payment of KES {amount_paid} was successful! Receipt: {receipt_number}",
                    is_sent=True,
                    is_read=False
                )

                # 2. ---> NEW: Notify the Landlord <---
                active_lease = Lease.objects.filter(tenant=tenant, is_active=True).select_related('unit__floor__property__landlord__user').first()
                
                if active_lease:
                    landlord_user = active_lease.unit.floor.property.landlord.user
                    unit_name = active_lease.unit.unit_name
                    
                    Notification.objects.create(
                        user=landlord_user,
                        notification_type='in_app',
                        purpose='payment',
                        message=f"Payment Received: {tenant.full_name} ({unit_name}) paid KES {amount_paid}. Ref: {receipt_number}",
                        is_sent=True,
                        is_read=False
                    )

        else:
            # Payment Failed Logic...
            payment = Payment.objects.filter(mpesa_receipt_number=checkout_id).first()
            if payment:
                # Notify Tenant of failure
                Notification.objects.create(
                    user=payment.invoice.tenant.user,
                    notification_type='in_app',
                    purpose='payment',
                    message=f"M-Pesa payment failed or was cancelled. Reason: {body.get('ResultDesc')}",
                    is_sent=True,
                    is_read=False
                )
                
                # ---> NEW: Notify Landlord of failure <---
                tenant = payment.invoice.tenant
                active_lease = Lease.objects.filter(tenant=tenant, is_active=True).first()
                if active_lease:
                    landlord_user = active_lease.unit.floor.property.landlord.user
                    Notification.objects.create(
                        user=landlord_user,
                        notification_type='in_app',
                        purpose='alert',
                        message=f"Failed Payment Attempt: {tenant.full_name} tried to pay, but the transaction was cancelled or timed out.",
                        is_sent=True,
                        is_read=False
                    )
                    
                payment.delete()

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

class LandlordReportsAnalyticsView(APIView):
    """
    REPORTS ENGINE:
    Calculates the aggregate financial health of the landlord's portfolio,
    including exact overpayment wallets.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            landlord = LandlordProfile.objects.get(user=request.user)
        except LandlordProfile.DoesNotExist:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        active_leases = Lease.objects.filter(
            unit__floor__property__landlord=landlord,
            is_active=True
        ).select_related('tenant')

        overpaid_tenants = []
        cleared_count = 0
        arrears_count = 0
        overpaid_count = 0

        for lease in active_leases:
            tenant = lease.tenant
            total_billed = Invoice.objects.filter(tenant=tenant).aggregate(Sum('amount_due'))['amount_due__sum'] or 0
            total_paid = Payment.objects.filter(invoice__tenant=tenant).aggregate(Sum('amount'))['amount__sum'] or 0
            
            # Categorize the tenant based on their true balance
            if total_paid > total_billed:
                overpaid_count += 1
                overpaid_tenants.append({
                    "id": str(tenant.id),
                    "name": tenant.full_name,
                    "overpayment": float(total_paid - total_billed) # Safe float conversion for JSON
                })
            elif total_billed > total_paid:
                arrears_count += 1
            else:
                cleared_count += 1

        # Sort the overpaid list so the biggest wallets appear at the top
        overpaid_tenants.sort(key=lambda x: x['overpayment'], reverse=True)

        return Response({
            "status_counts": {
                "cleared": cleared_count,
                "in_arrears": arrears_count,
                "overpaid": overpaid_count
            },
            "overpaid_tenants": overpaid_tenants
        }, status=status.HTTP_200_OK)