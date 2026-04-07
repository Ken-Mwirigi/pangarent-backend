from django.urls import path
from .views import (
    DraftBillingListView, GenerateInvoiceView, InvoiceManageView, 
    PreviousReadingView, InvoiceHistoryListView, InitiateSTKPushView,
    TenantDashboardStatsView, MpesaCallbackView, LandlordReportsAnalyticsView
)

urlpatterns = [
    path('records/', DraftBillingListView.as_view(), name='billing-records'),
    path('invoice/', GenerateInvoiceView.as_view(), name='generate-invoice'),
    path('invoice/<int:invoice_id>/', InvoiceManageView.as_view(), name='manage-invoice'),
    path('previous-reading/', PreviousReadingView.as_view(), name='previous-reading'),
    path('history/', InvoiceHistoryListView.as_view(), name='invoice-history'),
    path('mpesa/pay/', InitiateSTKPushView.as_view(), name='mpesa_pay'),
    
    path('dashboard-stats/', TenantDashboardStatsView.as_view(), name='dashboard-stats'),
    path('mpesa/callback/', MpesaCallbackView.as_view(), name='mpesa_callback'),
    
    # FIXED: Removed the "views." prefix since it's imported directly above!
    path('reports/analytics/', LandlordReportsAnalyticsView.as_view(), name='reports-analytics'),
]