from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoadTestTaskViewSet

router = DefaultRouter()
router.register(r'tasks', LoadTestTaskViewSet, basename='loadtesttask')

urlpatterns = [
    path('', include(router.urls)),
]