from rest_framework import serializers
from .models import TestReport, ReportTemplate


class TestReportSerializer(serializers.ModelSerializer):
    """测试报告序列化器"""
    generated_by_name = serializers.CharField(source='generated_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = TestReport
        fields = ['id', 'project', 'project_name', 'name', 'report_type', 'execution',
                  'summary', 'content', 'generated_by', 'generated_by_name', 'created_at']
        read_only_fields = ['generated_by', 'created_at']

    def create(self, validated_data):
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['generated_by'] = user
        return super().create(validated_data)


class ReportTemplateSerializer(serializers.ModelSerializer):
    """报告模板序列化器"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = ReportTemplate
        fields = ['id', 'name', 'description', 'template_config', 'is_default',
                  'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['created_by', 'created_at']

    def create(self, validated_data):
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['created_by'] = user
        return super().create(validated_data)
