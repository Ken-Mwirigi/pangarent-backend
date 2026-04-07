from django.db import models
from django.conf import settings

class Notification(models.Model):
    CHANNEL_CHOICES = (
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('in_app', 'In-App'), # Added to keep alerts inside the platform
    )
    
    PURPOSE_CHOICES = (
        ('verification', 'Account Verification'),
        ('credentials', 'Account Credentials'),
        ('billing', 'Monthly Invoice'),
        ('payment', 'Payment Confirmation'),
        ('reminder', 'Rent Reminder'),
    )

    # Links to the User table for auth
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    message = models.TextField()
    
    # Tracking for Twilio/Email delivery status 
    is_sent = models.BooleanField(default=False)
    status_code = models.CharField(max_length=100, blank=True, null=True) # From API response
    
    # Tracking for React frontend (powers the red "Unread" badge)
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.purpose} to {self.user.email} via {self.notification_type}"