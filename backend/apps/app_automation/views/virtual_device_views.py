# -*- coding: utf-8 -*-
"""虚拟设备管理视图"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .test_case_views import AppPagination
from ..models import VirtualDevice, VirtualDevicePool, AppDevice
from ..serializers import (
    VirtualDeviceSerializer,
    VirtualDevicePoolSerializer,
)

logger = logging.getLogger(__name__)


class VirtualDeviceViewSet(viewsets.ModelViewSet):
    """虚拟Android设备管理 ViewSet"""
    queryset = VirtualDevice.objects.all()
    serializer_class = VirtualDeviceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AppPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'brand']
    search_fields = ['name', 'model', 'device_id']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    # ========== 设备生命周期操作 ==========

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """启动虚拟设备"""
        device = self.get_object()

        if device.status == 'running':
            return Response({
                'success': False,
                'message': '设备已在运行中'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 更新状态
        device.status = 'running'
        device.started_at = timezone.now()
        device.save(update_fields=['status', 'started_at', 'updated_at'])

        logger.info(f"虚拟设备已启动: {device.name} ({device.device_id})")

        return Response({
            'success': True,
            'message': f'设备 {device.name} 已启动',
            'data': VirtualDeviceSerializer(device).data
        })

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止虚拟设备"""
        device = self.get_object()

        if device.status == 'stopped':
            return Response({
                'success': False,
                'message': '设备已停止'
            }, status=status.HTTP_400_BAD_REQUEST)

        device.status = 'stopped'
        device.save(update_fields=['status', 'updated_at'])

        logger.info(f"虚拟设备已停止: {device.name} ({device.device_id})")

        return Response({
            'success': True,
            'message': f'设备 {device.name} 已停止',
            'data': VirtualDeviceSerializer(device).data
        })

    @action(detail=True, methods=['post'])
    def restart(self, request, pk=None):
        """重启虚拟设备"""
        device = self.get_object()

        # 先停后启
        device.status = 'stopped'
        device.save(update_fields=['status', 'updated_at'])

        device.status = 'running'
        device.started_at = timezone.now()
        device.save(update_fields=['status', 'started_at', 'updated_at'])

        logger.info(f"虚拟设备已重启: {device.name} ({device.device_id})")

        return Response({
            'success': True,
            'message': f'设备 {device.name} 已重启',
            'data': VirtualDeviceSerializer(device).data
        })

    # ========== 设备池/模板操作 ==========

    @action(detail=False, methods=['get'])
    def templates(self, request):
        """获取预定义的设备模板列表"""
        templates = VirtualDevicePool.get_predefined_devices()

        return Response({
            'success': True,
            'data': {
                'count': len(templates),
                'templates': templates
            }
        })

    @action(detail=False, methods=['post'])
    def init_pool(self, request):
        """初始化设备池：从预定义模板批量创建虚拟设备"""
        templates = VirtualDevicePool.get_predefined_devices()
        created_devices = []
        existing_devices = []

        for template in templates:
            device_id = f"virtual-{template['brand']}-{template['model'].lower().replace(' ', '-')}"

            # 检查是否已存在
            if VirtualDevice.objects.filter(device_id=device_id).exists():
                existing = VirtualDevice.objects.get(device_id=device_id)
                existing_devices.append(VirtualDeviceSerializer(existing).data)
                continue

            device = VirtualDevice.objects.create(
                device_id=device_id,
                name=template['name'],
                status='stopped',
                brand=template['brand'],
                model=template['model'],
                android_version=template['android_version'],
                api_level=template['api_level'],
                cpu=template['cpu'],
                ram_gb=template['ram_gb'],
                storage_gb=template['storage_gb'],
                screen_resolution=template['screen_resolution'],
                screen_density=template['screen_density'],
                created_by=request.user,
            )

            # 创建池记录
            VirtualDevicePool.objects.get_or_create(
                device=device,
                defaults={'is_active': True}
            )

            created_devices.append(VirtualDeviceSerializer(device).data)

        return Response({
            'success': True,
            'message': f'初始化完成：新增 {len(created_devices)} 台，已存在 {len(existing_devices)} 台',
            'data': {
                'created': created_devices,
                'existing': existing_devices,
                'total': len(created_devices) + len(existing_devices)
            }
        })

    @action(detail=False, methods=['post'])
    def batch_start(self, request):
        """批量启动所有虚拟设备"""
        ids = request.data.get('ids', [])
        if ids:
            queryset = VirtualDevice.objects.filter(id__in=ids, status='stopped')
        else:
            queryset = VirtualDevice.objects.filter(status='stopped')

        count = queryset.count()
        now = timezone.now()
        queryset.update(status='running', started_at=now, updated_at=now)

        return Response({
            'success': True,
            'message': f'已启动 {count} 台设备',
            'data': {'started_count': count}
        })

    @action(detail=False, methods=['post'])
    def batch_stop(self, request):
        """批量停止所有虚拟设备"""
        ids = request.data.get('ids', [])
        if ids:
            queryset = VirtualDevice.objects.filter(id__in=ids, status='running')
        else:
            queryset = VirtualDevice.objects.filter(status='running')

        count = queryset.count()
        queryset.update(status='stopped', updated_at=timezone.now())

        return Response({
            'success': True,
            'message': f'已停止 {count} 台设备',
            'data': {'stopped_count': count}
        })

    @action(detail=False, methods=['get'])
    def pool_status(self, request):
        """获取设备池整体状态"""
        total = VirtualDevice.objects.count()
        running = VirtualDevice.objects.filter(status='running').count()
        stopped = VirtualDevice.objects.filter(status='stopped').count()
        error_count = VirtualDevice.objects.filter(status='error').count()

        # 按品牌统计
        from django.db.models import Count
        brand_stats = VirtualDevice.objects.values('brand').annotate(count=Count('id'))

        return Response({
            'success': True,
            'data': {
                'total': total,
                'running': running,
                'stopped': stopped,
                'error': error_count,
                'brand_stats': list(brand_stats),
            }
        })
