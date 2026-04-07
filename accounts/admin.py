from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, LandlordProfile,OTPVerification

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # What columns to show in the list view
    list_display = ('email', 'username', 'role', 'phone_number', 'is_verified', 'is_staff')
    search_fields = ('email', 'username', 'phone_number')
    list_filter = ('role', 'is_verified', 'is_staff')
    
    # Required to prevent errors when viewing the custom user in the admin
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'phone_number', 'is_verified')}),
    )

@admin.register(LandlordProfile)
class LandlordProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user')
    search_fields = ('full_name', 'user__email')

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp_code', 'created_at')
    search_fields = ('user__email', 'user__phone_number', 'otp_code')
    list_filter = ('created_at',)