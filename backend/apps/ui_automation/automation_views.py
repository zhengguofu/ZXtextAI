"""
自动化测试执行框架 - 视图
独立文件，不影响原 views.py。提供：
- 创建并执行测试
- 启动/恢复/暂停/取消
- 查询步骤/证据/日志
- 批量执行
- 执行需求评审生成的用例（一键执行）
- 获取报告
"""
import os
import logging
from django.utils import timezone
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import AutomationExecution, ExecutionStep, ExecutionEvidence, ExecutionLog
from .automation_serializers import (
    AutomationExecutionSerializer,
    AutomationExecutionListSerializer,
    CreateExecutionSerializer,
    BatchExecuteSerializer,
    ExecuteGeneratedCasesSerializer,
    ExecutionStepSerializer,
    ExecutionEvidenceSerializer,
    ExecutionLogSerializer,
)
from .tasks import (
    run_automation_test,
    resume_automation_test,
    run_batch_test,
    run_generated_testcases,
    parse_test_steps,
)

logger = logging.getLogger(__name__)


class AutomationExecutionViewSet(viewsets.ModelViewSet):
    """自动化执行记录视图集"""
    queryset = AutomationExecution.objects.all().order_by('-created_at')
    serializer_class = AutomationExecutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = AutomationExecution.objects.all().order_by('-created_at')
        # 普通用户只看自己的；可按需放开
        user = self.request.user
        if not user.is_staff:
            qs = qs.filter(created_by=user)
        # 过滤参数
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        source_type = self.request.query_params.get('source_type')
        if source_type:
            qs = qs.filter(source_type=source_type)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return AutomationExecutionListSerializer
        return AutomationExecutionSerializer

    @action(detail=False, methods=['post'])
    def create_and_execute(self, request):
        """创建执行记录并立即后台执行"""
        serializer = CreateExecutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        task_id = f"auto_{int(timezone.now().timestamp())}_{request.user.id}"

        execution = AutomationExecution.objects.create(
            task_id=task_id,
            case_name=data['case_name'],
            description=data.get('description', ''),
            source_type=data.get('source_type', 'manual'),
            source_id=data.get('source_id', ''),
            project_id=data.get('project'),
            generated_testcase_id=data.get('generated_testcase'),
            target_url=data.get('target_url', ''),
            browser_type=data.get('browser_type', 'chromium'),
            headless=data.get('headless', True),
            timeout=data.get('timeout', 300),
            created_by=request.user,
            executed_by=request.user,
            status='pending',
        )

        # 解析步骤：优先用传入的 steps，否则若有 target_url 则至少生成打开页面步骤
        steps = data.get('steps')
        if not steps:
            steps = parse_test_steps('', target_url=data.get('target_url', ''))
        else:
            # 规范化步骤结构
            norm = []
            target_url = data.get('target_url', '')
            if target_url:
                norm.append({'action_type': 'goto', 'target': target_url, 'value': '', 'desc': f'打开页面: {target_url}'})
            for s in steps:
                norm.append({
                    'action_type': (s.get('action_type') or 'custom'),
                    'target': s.get('target', '') or s.get('selector', ''),
                    'value': s.get('value', '') or s.get('text', ''),
                    'desc': s.get('desc', '') or s.get('action', '') or '自定义步骤',
                })
            steps = norm

        execution.total_steps = len(steps)
        execution.steps_definition = steps
        execution.save()

        for i, step in enumerate(steps):
            ExecutionStep.objects.create(
                execution=execution,
                step_id=f"step_{i+1}",
                step_name=step.get('desc', f'步骤{i+1}')[:200],
                step_desc=step.get('desc', ''),
                step_index=i,
                action_type=step.get('action_type', 'custom'),
            )

        async_result = run_automation_test.delay(task_id)
        execution.celery_task_id = async_result.id
        execution.save(update_fields=['celery_task_id'])

        return Response({
            'task_id': task_id,
            'celery_task_id': async_result.id,
            'message': '测试任务已创建并在后台执行',
            'status': 'running',
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """启动待执行任务"""
        execution = self.get_object()
        if execution.status not in ('pending',):
            return Response({'error': '只能启动待执行状态的任务'}, status=status.HTTP_400_BAD_REQUEST)
        execution.status = 'running'
        execution.started_at = timezone.now()
        execution.executed_by = request.user
        execution.save()
        async_result = run_automation_test.delay(execution.task_id)
        execution.celery_task_id = async_result.id
        execution.save(update_fields=['celery_task_id'])
        return Response({'message': '已启动', 'status': 'running'})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """从断点恢复执行"""
        execution = self.get_object()
        if not execution.can_resume:
            return Response({'error': '该任务不可恢复'}, status=status.HTTP_400_BAD_REQUEST)
        if execution.status not in ('interrupted', 'failed', 'blocked', 'paused'):
            return Response({'error': '只能恢复已中断/失败/阻塞/暂停的任务'}, status=status.HTTP_400_BAD_REQUEST)
        async_result = resume_automation_test.delay(execution.task_id)
        execution.celery_task_id = async_result.id
        execution.status = 'running'
        execution.save(update_fields=['celery_task_id', 'status'])
        return Response({
            'message': '已恢复执行',
            'status': 'running',
            'resume_from_step': execution.current_step_index,
        })

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """标记暂停（下次可续跑）"""
        execution = self.get_object()
        if execution.status != 'running':
            return Response({'error': '只能暂停执行中的任务'}, status=status.HTTP_400_BAD_REQUEST)
        execution.status = 'paused'
        execution.can_resume = True
        execution.save(update_fields=['status', 'can_resume'])
        return Response({'message': '已暂停', 'status': 'paused'})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消任务（尝试撤销 Celery 任务）"""
        execution = self.get_object()
        if execution.status not in ('running', 'pending', 'paused'):
            return Response({'error': '只能取消待执行/执行中/暂停的任务'}, status=status.HTTP_400_BAD_REQUEST)
        # 尝试撤销 celery 任务
        if execution.celery_task_id:
            try:
                from backend.celery import app as celery_app
                celery_app.control.revoke(execution.celery_task_id, terminate=True)
            except Exception as e:
                logger.warning(f"撤销Celery任务失败: {e}")
        execution.status = 'interrupted'
        execution.can_resume = True
        execution.save(update_fields=['status', 'can_resume'])
        return Response({'message': '已取消', 'status': 'interrupted'})

    @action(detail=True, methods=['get'])
    def steps(self, request, pk=None):
        execution = self.get_object()
        steps = ExecutionStep.objects.filter(execution=execution).order_by('step_index')
        return Response(ExecutionStepSerializer(steps, many=True).data)

    @action(detail=True, methods=['get'])
    def evidences(self, request, pk=None):
        execution = self.get_object()
        evidences = ExecutionEvidence.objects.filter(execution=execution)
        return Response(ExecutionEvidenceSerializer(evidences, many=True).data)

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        execution = self.get_object()
        logs = ExecutionLog.objects.filter(execution=execution).order_by('timestamp')
        return Response(ExecutionLogSerializer(logs, many=True).data)

    @action(detail=False, methods=['post'])
    def batch_execute(self, request):
        serializer = BatchExecuteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data['execution_ids']
        qs = AutomationExecution.objects.filter(task_id__in=ids, created_by=request.user)
        if qs.count() != len(ids):
            return Response({'error': '部分执行记录不存在或无权访问'}, status=status.HTTP_404_NOT_FOUND)
        run_batch_test.delay(ids)
        return Response({'message': '批量任务已启动', 'count': len(ids)})

    @action(detail=False, methods=['post'])
    def execute_generated_cases(self, request):
        """执行需求评审生成的测试用例（一键执行）"""
        serializer = ExecuteGeneratedCasesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        run_generated_testcases.delay(
            data['case_ids'],
            data.get('project_id'),
            data.get('target_url', ''),
            data.get('browser_type', 'chromium'),
            data.get('headless', True),
        )
        return Response({'message': '已开始执行生成的测试用例', 'count': len(data['case_ids'])})

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        qs = AutomationExecution.objects.filter(created_by=request.user)
        return Response({
            'total': qs.count(),
            'pending': qs.filter(status='pending').count(),
            'running': qs.filter(status='running').count(),
            'completed': qs.filter(status__in=['completed', 'passed']).count(),
            'failed': qs.filter(status='failed').count(),
            'interrupted': qs.filter(status='interrupted').count(),
            'blocked': qs.filter(status='blocked').count(),
        })

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """返回HTML报告内容"""
        execution = self.get_object()
        if not execution.report_path or not os.path.exists(execution.report_path):
            return Response({'error': '报告尚未生成或文件不存在'}, status=status.HTTP_404_NOT_FOUND)
        with open(execution.report_path, 'r', encoding='utf-8') as f:
            return HttpResponse(f.read(), content_type='text/html')

    @action(detail=True, methods=['get'])
    def video(self, request, pk=None):
        """返回录屏视频文件"""
        execution = self.get_object()
        if not execution.video_path or not os.path.exists(execution.video_path):
            return Response({'error': '视频不存在'}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(open(execution.video_path, 'rb'), content_type='video/webm')


class ExecutionEvidenceViewSet(viewsets.ReadOnlyModelViewSet):
    """证据查询 + 下载"""
    queryset = ExecutionEvidence.objects.all()
    serializer_class = ExecutionEvidenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExecutionEvidence.objects.filter(execution__created_by=self.request.user)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        evidence = self.get_object()
        if not os.path.exists(evidence.file_path):
            raise Http404('文件不存在')
        return FileResponse(open(evidence.file_path, 'rb'), as_attachment=True, filename=evidence.file_name)


class ExecutionLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExecutionLog.objects.all()
    serializer_class = ExecutionLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExecutionLog.objects.filter(execution__created_by=self.request.user)