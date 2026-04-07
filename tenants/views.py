from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import TenantRegistrationSerializer, TenantListSerializer
from .models import TenantProfile
from accounts.models import LandlordProfile  # <-- Added explicit import

class RegisterTenantView(generics.CreateAPIView):
    serializer_class = TenantRegistrationSerializer
    permission_classes = [IsAuthenticated] 

    def create(self, request, *args, **kwargs):
        # Security: Bulletproof check to ensure only landlords can invite tenants
        try:
            landlord = LandlordProfile.objects.get(user=request.user)
        except LandlordProfile.DoesNotExist:
            return Response(
                {"error": "Only registered landlords can add tenants."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {"message": "Tenant registered and invite sent successfully."}, 
            status=status.HTTP_201_CREATED
        )

class TenantListView(generics.ListAPIView):
    serializer_class = TenantListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Security: Only show tenants belonging to this specific landlord
        try:
            landlord = LandlordProfile.objects.get(user=self.request.user)
            return TenantProfile.objects.filter(
                leases__unit__floor__property__landlord=landlord,
                leases__is_active=True
            ).distinct()
        except LandlordProfile.DoesNotExist:
            return TenantProfile.objects.none()