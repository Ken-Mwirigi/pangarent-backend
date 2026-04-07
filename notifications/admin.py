from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'purpose', 'is_sent', 'created_at')
    list_filter = ('notification_type', 'purpose', 'is_sent')
    search_fields = ('user__email',)