"""
Core 应用视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import connection

from .models import UnifiedNotificationConfig
from .serializers import UnifiedNotificationConfigSerializer

import logging
import traceback
logger = logging.getLogger(__name__)


class UnifiedNotificationConfigViewSet(viewsets.ModelViewSet):
    """统一通知配置视图集"""
    queryset = UnifiedNotificationConfig.objects.all()
    serializer_class = UnifiedNotificationConfigSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['config_type', 'is_default', 'is_active']
    search_fields = ['name']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        """创建通知配置"""
        instance = serializer.save(created_by=self.request.user)
        logger.info(f"创建统一通知配置: {instance.name}")

    def perform_update(self, serializer):
        """更新通知配置"""
        instance = serializer.save()
        logger.info(f"更新统一通知配置: {instance.name}")

    def perform_destroy(self, instance):
        """删除通知配置"""
        logger.info(f"删除统一通知配置: {instance.name}")
        instance.delete()

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """设置为默认配置"""
        config = self.get_object()
        # 取消其他默认配置
        UnifiedNotificationConfig.objects.filter(is_default=True).update(is_default=False)
        # 设置当前为默认
        config.is_default = True
        config.save()
        return Response({'message': '已设置为默认配置'})

    @action(detail=False, methods=['get'])
    def active_configs(self, request):
        """获取所有启用的配置"""
        configs = UnifiedNotificationConfig.objects.filter(is_active=True)
        serializer = self.get_serializer(configs, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """健康检查接口"""
    try:
        # 检查数据库连接
        db_status = 'ok'
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            db_status = f'error: {str(e)}'
            logger.error(f"数据库连接检查失败: {e}")

        # 检查用户认证中间件
        user_status = 'anonymous'
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_status = f'authenticated as {request.user.username}'

        return Response({
            'status': 'ok' if db_status == 'ok' else 'degraded',
            'database': db_status,
            'user': user_status,
            'message': '后端服务正常运行'
        })
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        logger.error(f"错误堆栈:\n{traceback.format_exc()}")
        return Response({
            'status': 'error',
            'error': str(e),
            'detail': traceback.format_exc()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
