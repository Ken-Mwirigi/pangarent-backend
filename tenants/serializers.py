from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from .models import TenantProfile, Lease
from properties.models import Unit
from .models import TenantProfile # <-- Make sure TenantProfile is imported at the top!

User = get_user_model()

class TenantRegistrationSerializer(serializers.Serializer):
    # Match the camelCase keys coming from your React frontend
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    idNumber = serializers.CharField(max_length=50)
    unitId = serializers.IntegerField(required=False, allow_null=True)
    emergencyContact = serializers.CharField(max_length=255, required=False, allow_blank=True)
    emergencyPhone = serializers.CharField(max_length=20, required=False, allow_blank=True)

   

    class Meta:
        model = TenantProfile
        # Add accountStatus to the fields list
        fields = ['id', 'name', 'email', 'phone', 'idNumber', 'unitId', 'balance', 'accountStatus'] 

    def get_unitId(self, obj):
        lease = obj.leases.filter(is_active=True).first()
        return lease.unit.id if lease and lease.unit else None

    def get_balance(self, obj):
        return 0 

    # ADD THIS FUNCTION
    def get_accountStatus(self, obj):
        if obj.user.is_verified:
            return "Active"
        return "Pending Setup"

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def save(self):
        # transaction.atomic() ensures that if ANY step fails, ALL steps are undone
        with transaction.atomic():
            # 1. Create the User account
            user = User(
                email=self.validated_data['email'],
                username=self.validated_data['email'].split('@')[0],
                phone_number=self.validated_data['phone'],
                role='tenant'
            )
            # We set an unusable password so they MUST use the email link to log in
            user.set_unusable_password() 
            user.save()

            # 2. Create the Tenant Profile
            profile = TenantProfile.objects.create(
                user=user,
                full_name=self.validated_data['name'],
                id_number=self.validated_data['idNumber'],
                emergency_contact_name=self.validated_data.get('emergencyContact', ''),
                emergency_contact_phone=self.validated_data.get('emergencyPhone', '')
            )

            # 3. Handle the Lease and Unit update
            unit_id = self.validated_data.get('unitId')
            if unit_id:
                try:
                    unit = Unit.objects.get(id=unit_id)
                    # Create the active lease
                    Lease.objects.create(
                        tenant=profile,
                        unit=unit,
                        rent_amount_at_signing=unit.rent_amount,
                    )
                    # Flip the unit status to occupied
                    unit.is_occupied = True
                    unit.save()
                except Unit.DoesNotExist:
                    raise serializers.ValidationError({"unitId": "The selected unit does not exist."})

            # 4. Generate the Secure Invite Link
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = PasswordResetTokenGenerator().make_token(user)
            frontend_url = "http://localhost:8080" 
            
            # We are cleverly reusing your reset-password route for their initial setup!
            invite_link = f"{frontend_url}/reset-password/{uid}/{token}/" 

            # 5. Send the Welcome Email
            send_mail(
                subject='Welcome to PangaRent - Activate Your Account',
                message=f'''Hello {profile.full_name},

Your landlord has added you to the PangaRent system.

Please click the secure link below to set your password and access your new tenant dashboard:
{invite_link}

Welcome home!
The PangaRent Team
''',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            return profile



class TenantListSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='full_name')
    email = serializers.EmailField(source='user.email')
    phone = serializers.CharField(source='user.phone_number')
    idNumber = serializers.CharField(source='id_number')
    unitId = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    accountStatus = serializers.SerializerMethodField() 

    class Meta:
        model = TenantProfile
        # THE FIX: Make sure 'accountStatus' is included right here!
        fields = ['id', 'name', 'email', 'phone', 'idNumber', 'unitId', 'balance', 'accountStatus']

    def get_unitId(self, obj):
        lease = obj.leases.filter(is_active=True).first()
        return lease.unit.id if lease and lease.unit else None

    def get_balance(self, obj):
        return 0 

    def get_accountStatus(self, obj):
        if obj.user.is_verified:
            return "Active"
        return "Pending Setup"