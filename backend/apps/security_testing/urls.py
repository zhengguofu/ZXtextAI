from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SecurityScanTaskViewSet

router = DefaultRouter()
router.register(r'tasks', SecurityScanTaskViewSet, basename='securityscantask')

urlpatterns = [
    path('', include(router.urls)),
]