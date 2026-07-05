import random
import time
import threading
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import LoadTestTask
from .serializers import LoadTestTaskSerializer


class LoadTestTaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LoadTestTaskSerializer

    def get_queryset(self):
        return LoadTestTask.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        task = self.get_object()
        if task.status == 'running':
            return Response({'error': '任务正在运行中'}, status=status.HTTP_400_BAD_REQUEST)

        task.status = 'running'
        task.started_at = timezone.now()
        task.save()

        # 在后台线程执行压测模拟
        thread = threading.Thread(target=self._run_load_test, args=(task.id,))
        thread.daemon = True
        thread.start()

        return Response({'message': '压测任务已启动', 'task_id': str(task.id)})

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        task = self.get_object()
        if task.status != 'running':
            return Response({'error': '任务未在运行'}, status=status.HTTP_400_BAD_REQUEST)
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()
        return Response({'message': '压测任务已停止'})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.get_queryset()
        return Response({
            'total': queryset.count(),
            'completed': queryset.filter(status='completed').count(),
            'running': queryset.filter(status='running').count(),
            'peak_rps': max([t.peak_rps for t in queryset.filter(status='completed')] or [0]),
        })

    @action(detail=False, methods=['get'])
    def recent(self, request):
        queryset = self.get_queryset().order_by('-created_at')[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def _run_load_test(self, task_id):
        """在后台执行压测模拟"""
        task = LoadTestTask.objects.get(id=task_id)
        try:
            # 模拟压测执行
            time.sleep(min(task.duration, 30))  # 最多模拟30秒

            # 生成模拟结果
            task.peak_rps = round(random.uniform(task.concurrency * 0.5, task.concurrency * 2), 2)
            task.avg_response_time = round(random.uniform(20, 500), 2)
            task.error_rate = round(random.uniform(0, 5), 2)
            task.total_requests = int(task.concurrency * task.duration * random.uniform(0.8, 1.2))
            task.result_summary = f"压测完成。峰值RPS: {task.peak_rps}, 平均响应时间: {task.avg_response_time}ms, 错误率: {task.error_rate}%, 总请求: {task.total_requests}"
            task.status = 'completed'
        except Exception as e:
            task.status = 'failed'
            task.result_summary = f"压测失败: {str(e)}"
        finally:
            task.completed_at = timezone.now()
            task.save()