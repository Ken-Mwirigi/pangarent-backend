from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Notification
from .serializers import NotificationSerializer

class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch all in-app notifications for the logged-in user
        notifications = Notification.objects.filter(
            user=request.user, 
            notification_type='in_app'
        ).order_by('-created_at')
        
        # Count how many are unread
        unread_count = notifications.filter(is_read=False).count()
        
        # Let the serializer format the data!
        serializer = NotificationSerializer(notifications, many=True)
        
        return Response({
            "unread_count": unread_count,
            "notifications": serializer.data 
        }, status=status.HTTP_200_OK)


class MarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        if pk:
            # Mark a single notification as read
            try:
                notif = Notification.objects.get(pk=pk, user=request.user)
                notif.is_read = True
                notif.save()
            except Notification.DoesNotExist:
                pass
        else:
            # Mark ALL notifications as read
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            
        return Response({"status": "success"}, status=status.HTTP_200_OK)