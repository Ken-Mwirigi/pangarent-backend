from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
# Change the import here to use our new view instead of the default
from .views import RegisterLandlordView, VerifyOTPView, CustomTokenObtainPairView, PasswordResetRequestView, PasswordResetConfirmView

urlpatterns = [
    path('register/landlord/', RegisterLandlordView.as_view(), name='register_landlord'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    
    # Update this route to use the custom view
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]