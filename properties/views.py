from rest_framework import viewsets, exceptions
from rest_framework.permissions import IsAuthenticated
from .models import Property, Floor, Unit
from .serializers import PropertySerializer, FloorSerializer, UnitSerializer
from accounts.models import LandlordProfile  # <-- Added direct import

class PropertyViewSet(viewsets.ModelViewSet):
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated]

    # Helper function to explicitly find the profile
    def get_landlord_profile(self):
        try:
            return LandlordProfile.objects.get(user=self.request.user)
        except LandlordProfile.DoesNotExist:
            return None

    def get_queryset(self):
        profile = self.get_landlord_profile()
        if profile:
            return Property.objects.filter(landlord=profile)
        return Property.objects.none()

    def perform_create(self, serializer):
        profile = self.get_landlord_profile()
        if profile:
            serializer.save(landlord=profile)
        else:
            raise exceptions.ValidationError({"error": "Your account is missing a Landlord Profile. Ensure you are logged in with a landlord account."})


class FloorViewSet(viewsets.ModelViewSet):
    serializer_class = FloorSerializer
    permission_classes = [IsAuthenticated]

    def get_landlord_profile(self):
        try:
            return LandlordProfile.objects.get(user=self.request.user)
        except LandlordProfile.DoesNotExist:
            return None

    def get_queryset(self):
        profile = self.get_landlord_profile()
        if profile:
            return Floor.objects.filter(property__landlord=profile)
        return Floor.objects.none()


class UnitViewSet(viewsets.ModelViewSet):
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated]

    def get_landlord_profile(self):
        try:
            return LandlordProfile.objects.get(user=self.request.user)
        except LandlordProfile.DoesNotExist:
            return None

    def get_queryset(self):
        profile = self.get_landlord_profile()
        if profile:
            return Unit.objects.filter(floor__property__landlord=profile)
        return Unit.objects.none()