from django.urls import path
from .views import NotificationListView, MarkNotificationReadView

urlpatterns = [
    path('', NotificationListView.as_view(), name='notifications-list'),
    path('mark-read/', MarkNotificationReadView.as_view(), name='notifications-mark-all-read'),
    path('<int:pk>/mark-read/', MarkNotificationReadView.as_view(), name='notifications-mark-read'),
]