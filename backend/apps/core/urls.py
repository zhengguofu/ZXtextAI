"""
Core 应用路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UnifiedNotificationConfigViewSet, health_check

router = DefaultRouter()
router.register(r'notification-configs', UnifiedNotificationConfigViewSet, basename='unified-notification-config')

urlpatterns = [
    path('', include(router.urls)),
    path('health/', health_check, name='health-check'),
]
