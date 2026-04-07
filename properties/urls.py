from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropertyViewSet, FloorViewSet, UnitViewSet

router = DefaultRouter()
router.register(r'properties', PropertyViewSet, basename='property')
router.register(r'floors', FloorViewSet, basename='floor')
router.register(r'units', UnitViewSet, basename='unit')

urlpatterns = [
    path('', include(router.urls)),
]