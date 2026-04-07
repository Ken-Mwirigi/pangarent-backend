import random
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import User, OTPVerification

@receiver(post_save, sender=User)
def create_user_otp(sender, instance, created, **kwargs):
    if created and not instance.is_verified:
        # 1. Generate the 6-digit OTP
        otp = str(random.randint(100000, 999999))
        OTPVerification.objects.create(user=instance, otp_code=otp)
        
        # 2. Send the Email
        try:
            send_mail(
                subject='Welcome to PangaRent - Verify Your Account',
                message=f'Hello,\n\nYour PangaRent verification code is: {otp}\n\nPlease enter this code on the verification screen to complete your registration.',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[instance.email],
                fail_silently=False,
            )
            print(f"✅ OTP Email successfully sent to {instance.email}")
            print(f"🔑 OTP Code (for testing): {otp}")
        except Exception as e:
            print(f"❌ Failed to send email. Error: {e}")