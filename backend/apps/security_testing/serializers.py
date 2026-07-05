from rest_framework import serializers
from .models import SecurityScanTask, SecurityFinding


class SecurityFindingSerializer(serializers.ModelSerializer):
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model = SecurityFinding
        fields = '__all__'


class SecurityScanTaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    scan_type_display = serializers.CharField(source='get_scan_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    findings = SecurityFindingSerializer(many=True, read_only=True)

    class Meta:
        model = SecurityScanTask
        fields = [
            'id', 'name', 'scan_type', 'scan_type_display', 'target', 'tool', 'depth',
            'status', 'status_display', 'total_risks', 'high_risks', 'medium_risks', 'low_risks',
            'result_summary', 'report_file', 'created_by_name', 'created_at', 'started_at', 'completed_at',
            'findings'
        ]
        read_only_fields = ['status', 'total_risks', 'high_risks', 'medium_risks', 'low_risks', 'result_summary']