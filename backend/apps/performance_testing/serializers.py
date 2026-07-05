from rest_framework import serializers
from .models import LoadTestTask


class LoadTestTaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    test_type_display = serializers.CharField(source='get_test_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = LoadTestTask
        fields = [
            'id', 'name', 'test_type', 'test_type_display', 'target_url',
            'concurrency', 'duration', 'ramp_up', 'status', 'status_display',
            'peak_rps', 'avg_response_time', 'error_rate', 'total_requests',
            'result_summary', 'report_file', 'created_by_name',
            'created_at', 'started_at', 'completed_at'
        ]
        read_only_fields = ['status', 'peak_rps', 'avg_response_time', 'error_rate', 'total_requests', 'result_summary']