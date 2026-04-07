from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    # This automatically handles that nice date formatting you wrote!
    created_at = serializers.DateTimeField(format="%b %d, %Y %I:%M %p")

    class Meta:
        model = Notification
        fields = ['id', 'purpose', 'message', 'is_read', 'created_at']