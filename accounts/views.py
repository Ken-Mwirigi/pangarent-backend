from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .models import User, OTPVerification
from .serializers import RegisterLandlordSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer,PasswordResetRequestSerializer, PasswordResetConfirmSerializer
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

class RegisterLandlordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterLandlordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            # The post_save signal we wrote earlier will automatically generate the OTP 
            # and send the SMS/Email here.
            return Response({"message": "Account created. Please verify your OTP."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp_code')

        try:
            user = User.objects.get(email=email)
            otp_record = OTPVerification.objects.get(user=user)

            if otp_record.otp_code == str(otp):
                user.is_verified = True
                user.save()
                otp_record.delete()
                return Response({"message": "Verified successfully."}, status=status.HTTP_200_OK)
            return Response({"error": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)
        except (User.DoesNotExist, OTPVerification.DoesNotExist):
            return Response({"error": "User/OTP not found."}, status=status.HTTP_404_NOT_FOUND)
      

# ... (keep your existing RegisterLandlordView and VerifyOTPView up here) ...

class CustomTokenObtainPairView(TokenObtainPairView):
    # This tells the login view to use our strict verification check
    serializer_class = CustomTokenObtainPairSerializer

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "If that email exists, a password reset link has been sent."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()

            # The magic fix: Automatically verify the tenant because they clicked the email link!
           # The magic fix: Automatically verify the tenant safely
            try:
                # CHANGED: Use serializer.validated_data['uidb64'] instead of request.data.get
                uid = force_str(urlsafe_base64_decode(serializer.validated_data['uidb64']))
                user = User.objects.get(pk=uid)
                user.is_verified = True
                user.save()
            except Exception as e:
                print("Verification failed during password reset:", e)
            return Response({"message": "Your password has been reset successfully. You can now log in."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)