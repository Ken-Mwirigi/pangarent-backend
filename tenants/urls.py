from django.urls import path
from .views import RegisterTenantView, TenantListView

urlpatterns = [
    path('register/', RegisterTenantView.as_view(), name='register-tenant'),
    path('', TenantListView.as_view(), name='list-tenants'),
]