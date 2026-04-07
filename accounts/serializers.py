from rest_framework import serializers
from .models import User, LandlordProfile
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings

class RegisterLandlordSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['email', 'phone_number', 'full_name', 'password']

    def create(self, validated_data):
        full_name = validated_data.pop('full_name')
        
        # create_user automatically hashes the password [cite: 76]
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['email'].split('@')[0],
            phone_number=validated_data['phone_number'],
            password=validated_data['password'],
            role='landlord',
            is_verified=False
        )
        
        LandlordProfile.objects.create(user=user, full_name=full_name)
        return user



# ... (keep your existing RegisterLandlordSerializer up here) ...

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # 1. Run the default email/password check
        data = super().validate(attrs)
        
        # 2. Check if the user successfully completed OTP verification
        if not self.user.is_verified:
            raise AuthenticationFailed('Account is not verified. Please check your email/phone for the OTP.')

        data['role'] = self.user.role
        
        # ---> THE FIX: Safely pull the name from the correct Profile <---
        if hasattr(self.user, 'landlordprofile'):
            data['full_name'] = self.user.landlordprofile.full_name
        elif hasattr(self.user, 'tenantprofile'):
            data['full_name'] = self.user.tenantprofile.full_name
        else:
            data['full_name'] = self.user.username or 'User'
            
        return data
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("We cannot find an account with that email address.")
        return value

    def save(self):
        email = self.validated_data['email']
        user = User.objects.get(email=email)
        
        # 1. Generate the secure token and encode the User ID
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = PasswordResetTokenGenerator().make_token(user)
        
        # Safely get the user's name (Admins/Superusers won't have a LandlordProfile!)
        greeting_name = "User"
        if hasattr(user, 'landlordprofile'):
            greeting_name = user.landlordprofile.full_name
        elif hasattr(user, 'tenantprofile'):
            greeting_name = user.tenantprofile.full_name
        elif user.username:
            greeting_name = user.username
        
        # 2. Build the link pointing back to your Lovable React frontend
        frontend_url = "http://localhost:8080" 
        reset_link = f"{frontend_url}/reset-password/{uid}/{token}/"
        
        # 3. Send the email
        send_mail(
            subject='PangaRent - Secure Password Reset Request',
            message=f'''Hello {greeting_name},

We received a request to reset the password for your PangaRent account associated with this email address.

Please click the secure link below to choose a new password:
{reset_link}

For your security, this link will expire in 24 hours. 

If you did not request a password reset, you can safely ignore this email. Your account remains secure.

Thank you,
The PangaRent Team
''',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            fail_silently=False,
        )
      

class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)
    uidb64 = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
            
        try:
            # Decode the user ID and find the user
            uid = force_str(urlsafe_base64_decode(attrs['uidb64']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"token": "Invalid or corrupted reset link."})
            
        # Check if the token is valid and hasn't been used or expired
        if not PasswordResetTokenGenerator().check_token(user, attrs['token']):
            raise serializers.ValidationError({"token": "This reset link is invalid or has expired."})
            
        self.user = user
        return attrs

    def save(self):
        # set_password safely hashes the new password
        self.user.set_password(self.validated_data['new_password'])
        self.user.save()