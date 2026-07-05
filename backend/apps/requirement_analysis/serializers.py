from rest_framework import serializers
from .models import (
    RequirementDocument, RequirementAnalysis, BusinessRequirement,
    GeneratedTestCase, AnalysisTask, AIModelConfig, PromptConfig, TestCaseGenerationTask,
    GenerationConfig
)


class RequirementDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = RequirementDocument
        fields = ['id', 'title', 'file', 'file_url', 'document_type', 'document_type_display', 
                 'status', 'status_display', 'uploaded_by', 'uploaded_by_name', 'project', 
                 'project_name', 'created_at', 'updated_at', 'file_size', 'extracted_text']
        read_only_fields = ['uploaded_by', 'file_size', 'extracted_text']
    
    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class BusinessRequirementSerializer(serializers.ModelSerializer):
    requirement_type_display = serializers.CharField(source='get_requirement_type_display', read_only=True)
    requirement_level_display = serializers.CharField(source='get_requirement_level_display', read_only=True)
    parent_requirement_name = serializers.CharField(source='parent_requirement.requirement_name', read_only=True)
    
    class Meta:
        model = BusinessRequirement
        fields = ['id', 'requirement_id', 'requirement_name', 'requirement_type', 
                 'requirement_type_display', 'parent_requirement', 'parent_requirement_name',
                 'module', 'requirement_level', 'requirement_level_display', 'reviewer', 
                 'estimated_hours', 'description', 'acceptance_criteria', 'created_at', 'updated_at']


class RequirementAnalysisSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)
    document_id = serializers.IntegerField(source='document.id', read_only=True)
    requirements = BusinessRequirementSerializer(many=True, read_only=True)
    
    class Meta:
        model = RequirementAnalysis
        fields = ['id', 'document_id', 'document_title', 'analysis_report', 
                 'requirements_count', 'analysis_time', 'created_at', 'updated_at', 'requirements']


class GeneratedTestCaseSerializer(serializers.ModelSerializer):
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    requirement_name = serializers.CharField(source='requirement.requirement_name', read_only=True)
    requirement_id_display = serializers.CharField(source='requirement.requirement_id', read_only=True)
    
    class Meta:
        model = GeneratedTestCase
        fields = ['id', 'case_id', 'title', 'priority', 'priority_display', 'precondition',
                 'test_steps', 'expected_result', 'status', 'status_display', 'generated_by_ai',
                 'reviewed_by_ai', 'review_comments', 'requirement', 'requirement_name', 
                 'requirement_id_display', 'created_at', 'updated_at']


class AnalysisTaskSerializer(serializers.ModelSerializer):
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    document_title = serializers.CharField(source='document.title', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = AnalysisTask
        fields = ['id', 'task_id', 'task_type', 'task_type_display', 'document', 'document_title',
                 'status', 'status_display', 'progress', 'result', 'error_message', 
                 'started_at', 'completed_at', 'created_at', 'duration']
        read_only_fields = ['task_id', 'result', 'error_message', 'started_at', 'completed_at']
    
    def get_duration(self, obj):
        if obj.started_at and obj.completed_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None


class DocumentUploadSerializer(serializers.ModelSerializer):
    """文档上传专用序列化器"""
    class Meta:
        model = RequirementDocument
        fields = ['id', 'title', 'file', 'project']
    
    def create(self, validated_data):
        # 自动设置上传者（如果用户已登录）
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['uploaded_by'] = user
        else:
            # 如果是匿名用户，使用第一个超级用户作为默认用户
            from apps.users.models import User
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
            validated_data['uploaded_by'] = default_user
        
        # 根据文件扩展名设置文档类型
        file = validated_data['file']
        if file.name.lower().endswith('.pdf'):
            validated_data['document_type'] = 'pdf'
        elif file.name.lower().endswith(('.doc', '.docx')):
            validated_data['document_type'] = 'docx'
        elif file.name.lower().endswith('.txt'):
            validated_data['document_type'] = 'txt'
        elif file.name.lower().endswith('.md'):
            validated_data['document_type'] = 'md'
        
        # 设置文件大小
        validated_data['file_size'] = file.size
        
        return super().create(validated_data)


class TestCaseGenerationRequestSerializer(serializers.Serializer):
    """测试用例生成请求序列化器"""
    requirement_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="需求ID列表"
    )
    test_level = serializers.ChoiceField(
        choices=[('unit', '单元测试'), ('integration', '集成测试'), ('system', '系统测试'), ('acceptance', '验收测试')],
        default='system',
        help_text="测试级别"
    )
    test_priority = serializers.ChoiceField(
        choices=[('P0', '最高优先级'), ('P1', '高优先级'), ('P2', '中优先级'), ('P3', '低优先级')],
        default='P1',
        help_text="测试优先级"
    )
    test_case_count = serializers.IntegerField(
        min_value=1,
        max_value=200,
        default=50,
        help_text="生成测试用例数量"
    )


class TestCaseReviewRequestSerializer(serializers.Serializer):
    """测试用例评审请求序列化器"""
    test_case_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="测试用例ID列表"
    )
    review_criteria = serializers.CharField(
        max_length=500,
        default="检查测试用例的完整性、准确性和可执行性",
        help_text="评审标准"
    )


class AIModelConfigSerializer(serializers.ModelSerializer):
    """AI模型配置序列化器"""
    model_type_display = serializers.CharField(source='get_model_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    api_key_masked = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = AIModelConfig
        fields = ['id', 'name', 'model_type', 'model_type_display',
                 'api_key', 'api_key_masked', 'base_url', 'model_name', 'max_tokens', 'temperature', 'top_p', 
                 'is_active', 'is_builtin', 'speed_ms', 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_by_name', 'is_builtin', 'speed_ms']
        extra_kwargs = {
            'api_key': {'write_only': True, 'required': False, 'allow_blank': True},
        }

    def get_api_key_masked(self, obj):
        """返回掩码版本的API Key —— 内置模型的密钥完全隐藏"""
        if obj.is_builtin:
            return '******（内置密钥，不可查看）'
        if obj.api_key:
            # 显示前3个字符和后4个字符，中间用*替代
            if len(obj.api_key) > 7:
                return f"{obj.api_key[:3]}{'*' * (len(obj.api_key) - 7)}{obj.api_key[-4:]}"
            else:
                return '*' * len(obj.api_key)
        return ''
    
    def validate(self, data):
        """验证：内置配置不可修改关键字段"""
        if self.instance and self.instance.is_builtin:
            protected_fields = ['api_key', 'base_url', 'model_name', 'name', 'model_type']
            for field in protected_fields:
                if field in data and data[field] != getattr(self.instance, field):
                    raise serializers.ValidationError({field: f'内置模型不可修改 {field} 字段'})
        return data
    
    def validate_api_key(self, value):
        """验证 API Key，如果包含掩码字符(*)则使用旧值"""
        if value and '*' in value and len(value) > 10:
            if self.instance and self.instance.api_key:
                return self.instance.api_key
            raise serializers.ValidationError('API Key 不能为掩码值')
        return value

    def create(self, validated_data):
        # 创建时必须提供 api_key
        if not validated_data.get('api_key'):
            raise serializers.ValidationError({'api_key': '创建配置时必须提供 API Key'})
        # 自动设置创建者
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['created_by'] = user
        else:
            # 如果是匿名用户，使用第一个超级用户作为默认用户
            from apps.users.models import User
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
            validated_data['created_by'] = default_user
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # 内置模型不允许修改
        if instance.is_builtin:
            raise serializers.ValidationError({'error': '内置模型配置不可修改'})
        # 如果没有传 api_key，保持原来的值
        if 'api_key' not in validated_data or not validated_data.get('api_key'):
            validated_data.pop('api_key', None)
        return super().update(instance, validated_data)


class PromptConfigSerializer(serializers.ModelSerializer):
    """提示词配置序列化器"""
    prompt_type_display = serializers.CharField(source='get_prompt_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = PromptConfig
        fields = ['id', 'name', 'prompt_type', 'prompt_type_display', 'content', 'is_active',
                 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_by_name']
    
    def create(self, validated_data):
        # 自动设置创建者
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['created_by'] = user
        else:
            from apps.users.models import User
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
            validated_data['created_by'] = default_user
        
        return super().create(validated_data)


class TestCaseGenerationTaskSerializer(serializers.ModelSerializer):
    """测试用例生成任务序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    writer_model_name = serializers.CharField(source='writer_model_config.name', read_only=True)
    reviewer_model_name = serializers.CharField(source='reviewer_model_config.name', read_only=True)
    writer_prompt_name = serializers.CharField(source='writer_prompt_config.name', read_only=True)
    reviewer_prompt_name = serializers.CharField(source='reviewer_prompt_config.name', read_only=True)
    workflow_stage_display = serializers.CharField(source='get_workflow_stage_display', read_only=True)
    
    class Meta:
        model = TestCaseGenerationTask
        fields = ['id', 'task_id', 'title', 'requirement_text', 'target_url', 'status', 'status_display',
                 'progress', 'project', 'project_name', 'writer_model_config', 'writer_model_name',
                 'reviewer_model_config', 'reviewer_model_name', 'writer_prompt_config', 'writer_prompt_name',
                 'reviewer_prompt_config', 'reviewer_prompt_name', 'generated_test_cases',
                 'review_feedback', 'final_test_cases', 'generation_log', 'error_message',
                 'is_saved_to_records', 'saved_at', 'created_by', 'created_by_name',
                 'created_at', 'updated_at', 'completed_at',
                 'workflow_stage', 'workflow_stage_display', 'reviewer_notes',
                 'approver_notes', 'approved_at', 'rejected_at', 'executed_at',
                 'output_mode']
        read_only_fields = ['task_id', 'status', 'progress', 'generated_test_cases',
                          'review_feedback', 'final_test_cases', 'generation_log',
                          'error_message', 'is_saved_to_records', 'saved_at', 'created_by', 'completed_at',
                          'approved_at', 'rejected_at', 'executed_at']
    
    def create(self, validated_data):
        # 自动设置创建者和任务ID
        import uuid
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['created_by'] = user
        else:
            from apps.users.models import User
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
            validated_data['created_by'] = default_user
        
        validated_data['task_id'] = f"TASK_{uuid.uuid4().hex[:8].upper()}"
        
        return super().create(validated_data)


class TestCaseGenerationRequestSerializer(serializers.Serializer):
    """新的测试用例生成请求序列化器"""
    title = serializers.CharField(max_length=200, help_text="任务标题")
    requirement_text = serializers.CharField(help_text="需求描述")
    target_url = serializers.URLField(required=False, allow_blank=True, help_text="目标测试网址（AI会爬取页面内容）")
    project = serializers.IntegerField(required=False, allow_null=True, help_text="关联项目ID")
    requirement_review = serializers.CharField(required=False, allow_blank=True, help_text="已采纳的需求评审内容")
    review_adopted = serializers.BooleanField(default=False, help_text="需求评审是否已被用户采纳")
    output_mode = serializers.ChoiceField(
        choices=[('stream', '实时流式输出'), ('complete', '完整输出')],
        required=False,
        help_text="输出模式"
    )
    use_writer_model = serializers.BooleanField(default=True, help_text="是否使用编写模型")
    use_reviewer_model = serializers.BooleanField(default=True, help_text="是否使用评审模型")


class GenerationConfigSerializer(serializers.ModelSerializer):
    """生成行为配置序列化器"""
    default_output_mode_display = serializers.CharField(source='get_default_output_mode_display', read_only=True)

    class Meta:
        model = GenerationConfig
        fields = [
            'id', 'name', 'default_output_mode', 'default_output_mode_display',
            'enable_auto_review', 'review_timeout',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
