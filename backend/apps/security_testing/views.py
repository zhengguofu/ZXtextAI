import threading
import logging
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import SecurityScanTask, SecurityFinding
from .serializers import SecurityScanTaskSerializer, SecurityFindingSerializer
from .security_scanner import SecurityScanner

logger = logging.getLogger(__name__)


class SecurityScanTaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SecurityScanTaskSerializer

    @action(detail=False, methods=['post'])
    def quick_start(self, request):
        """创建并立即启动安全扫描任务"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save(created_by=request.user)
        task.status = 'running'
        task.started_at = timezone.now()
        task.save(update_fields=['status', 'started_at'])

        thread = threading.Thread(target=self._run_scan, args=(task.id,))
        thread.daemon = True
        thread.start()

        return Response(self.get_serializer(task).data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        return SecurityScanTask.objects.filter(created_by=self.request.user)

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
        task.findings.all().delete()

        # 清除旧发现
        task.findings.all().delete()

        thread = threading.Thread(target=self._run_scan, args=(task.id,))
        thread.daemon = True
        thread.start()

        return Response({'message': '扫描任务已启动', 'task_id': str(task.id)})

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        task = self.get_object()
        if task.status != 'running':
            return Response({'error': '任务未在运行'}, status=status.HTTP_400_BAD_REQUEST)
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()
        return Response({'message': '扫描任务已停止'})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.get_queryset()
        return Response({
            'total': queryset.count(),
            'safe': queryset.filter(status='completed', high_risks=0).count(),
            'risk': queryset.filter(status='completed', high_risks__gt=0).count(),
            'high': queryset.filter(high_risks__gt=0).count(),
        })

    @action(detail=False, methods=['get'])
    def recent(self, request):
        queryset = self.get_queryset().order_by('-created_at')[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def findings(self, request):
        """获取发现列表，可按 task 过滤"""
        task_id = request.query_params.get('task')
        queryset = SecurityFinding.objects.filter(task__created_by=request.user)
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        serializer = SecurityFindingSerializer(queryset.order_by('-severity'), many=True)
        return Response(serializer.data)

    def _run_scan(self, task_id):
        """在后台执行真实安全扫描"""
        try:
            task = SecurityScanTask.objects.get(id=task_id)
        except SecurityScanTask.DoesNotExist:
            logger.error(f"扫描任务不存在: {task_id}")
            return

        try:
            logger.info(f"开始真实安全扫描: {task.target}")

            # 使用真实扫描引擎
            scanner = SecurityScanner(task.target, task_id=task.id)
            findings = scanner.run_full_scan()

            # 批量保存发现
            for fdata in findings:
                SecurityFinding.objects.create(
                    task=task,
                    title=fdata['title'],
                    detail=fdata['detail'],
                    severity=fdata['severity'],
                    target=fdata['target'],
                    remediation=fdata['remediation']
                )

            # 统计结果
            critical_high = sum(1 for f in findings if f['severity'] in ['critical', 'high'])
            medium = sum(1 for f in findings if f['severity'] == 'medium')
            low = sum(1 for f in findings if f['severity'] in ['low', 'info'])

            task.total_risks = len(findings)
            task.high_risks = critical_high
            task.medium_risks = medium
            task.low_risks = low

            if findings:
                task.result_summary = (
                    f"真实安全扫描完成。共发现 {len(findings)} 个风险，"
                    f"其中高危 {critical_high} 个，中危 {medium} 个，"
                    f"低危/信息 {low} 个。"
                )
            else:
                task.result_summary = "真实安全扫描完成。未发现明确安全风险，目标站点基本安全。"

            task.status = 'completed'
            logger.info(f"安全扫描完成 [{task.target}]: {task.result_summary}")

        except Exception as e:
            logger.error(f"安全扫描失败 [{task.target}]: {e}")
            task.status = 'failed'
            task.result_summary = f"扫描执行失败: {str(e)[:500]}"
        finally:
            task.completed_at = timezone.now()
            task.save()
