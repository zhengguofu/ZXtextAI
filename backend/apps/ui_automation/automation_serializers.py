"""
自动化测试执行框架 - 序列化器
独立文件，不影响原 serializers.py
"""
from rest_framework import serializers
from .models import AutomationExecution, ExecutionStep, ExecutionEvidence, ExecutionLog


class ExecutionStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionStep
        fields = [
            'id', 'step_id', 'step_name', 'step_desc', 'step_index', 'action_type',
            'status', 'started_at', 'completed_at', 'duration',
            'url', 'page_title', 'screenshot_before', 'screenshot_after',
            'error_message', 'dom_path', 'console_log_path', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ExecutionEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionEvidence
        fields = ['id', 'evidence_type', 'file_path', 'file_name', 'description', 'step', 'created_at']
        read_only_fields = ['id', 'created_at']


class ExecutionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionLog
        fields = ['id', 'log_level', 'message', 'step', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class AutomationExecutionSerializer(serializers.ModelSerializer):
    """执行记录详情（含步骤、证据、日志）"""
    steps = ExecutionStepSerializer(many=True, read_only=True)
    evidences = ExecutionEvidenceSerializer(many=True, read_only=True)
    progress = serializers.ReadOnlyField()

    class Meta:
        model = AutomationExecution
        fields = [
            'id', 'task_id', 'case_name', 'description',
            'source_type', 'source_id', 'project', 'generated_testcase',
            'status', 'execution_mode', 'progress',
            'current_step_index', 'current_case_index', 'last_executed_step_id',
            'target_url', 'browser_type', 'headless', 'timeout', 'steps_definition',
            'artifact_dir', 'video_path', 'report_path', 'trace_path', 'har_path',
            'total_cases', 'passed_cases', 'failed_cases', 'blocked_cases',
            'total_steps', 'passed_steps', 'failed_steps', 'duration',
            'error_message', 'blocking_reason',
            'created_by', 'executed_by',
            'started_at', 'completed_at', 'created_at', 'updated_at',
            'can_resume', 'celery_task_id',
            'steps', 'evidences',
        ]
        read_only_fields = ['id', 'task_id', 'created_at', 'updated_at', 'created_by']


class AutomationExecutionListSerializer(serializers.ModelSerializer):
    """执行记录列表（精简，不含步骤明细）"""
    progress = serializers.ReadOnlyField()

    class Meta:
        model = AutomationExecution
        fields = [
            'id', 'task_id', 'case_name', 'source_type', 'status', 'execution_mode',
            'progress', 'browser_type', 'headless',
            'total_steps', 'passed_steps', 'failed_steps', 'duration',
            'video_path', 'report_path', 'can_resume', 'current_step_index',
            'started_at', 'completed_at', 'created_at',
        ]


class CreateExecutionSerializer(serializers.Serializer):
    """创建执行任务入参"""
    case_name = serializers.CharField(max_length=200, required=True)
    description = serializers.CharField(allow_blank=True, required=False)
    target_url = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    source_type = serializers.CharField(max_length=20, default='manual', required=False)
    source_id = serializers.CharField(max_length=100, allow_blank=True, required=False)
    project = serializers.IntegerField(required=False, allow_null=True)
    generated_testcase = serializers.IntegerField(required=False, allow_null=True)
    browser_type = serializers.CharField(max_length=20, default='chromium', required=False)
    headless = serializers.BooleanField(default=True, required=False)
    timeout = serializers.IntegerField(default=300, required=False)
    steps = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="步骤列表: [{'action_type':'goto','target':'https://...','desc':'...'}]",
    )


class BatchExecuteSerializer(serializers.Serializer):
    execution_ids = serializers.ListField(child=serializers.CharField(max_length=100), required=True)


class ExecuteGeneratedCasesSerializer(serializers.Serializer):
    case_ids = serializers.ListField(child=serializers.IntegerField(), required=True)
    project_id = serializers.IntegerField(required=False, allow_null=True)
    target_url = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    browser_type = serializers.CharField(max_length=20, default='chromium', required=False)
    headless = serializers.BooleanField(default=True, required=False)