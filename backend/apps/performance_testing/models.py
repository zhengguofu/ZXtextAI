import uuid
from django.db import models
from apps.users.models import User


class LoadTestTask(models.Model):
    TEST_TYPE_CHOICES = [
        ('api', '接口压测'),
        ('web', '网页压测'),
        ('app', 'APP压测'),
    ]
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='任务名称')
    test_type = models.CharField(max_length=20, choices=TEST_TYPE_CHOICES, verbose_name='测试类型')
    target_url = models.URLField(max_length=500, verbose_name='目标地址')
    concurrency = models.IntegerField(default=100, verbose_name='并发数')
    duration = models.IntegerField(default=60, verbose_name='持续时间(秒)')
    ramp_up = models.IntegerField(default=10, verbose_name=' Ramp-Up时间(秒)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    peak_rps = models.FloatField(default=0, verbose_name='峰值RPS')
    avg_response_time = models.FloatField(default=0, verbose_name='平均响应时间(ms)')
    error_rate = models.FloatField(default=0, verbose_name='错误率(%)')
    total_requests = models.IntegerField(default=0, verbose_name='总请求数')
    result_summary = models.TextField(blank=True, verbose_name='结果摘要')
    report_file = models.FileField(upload_to='performance_reports/%Y/%m/', blank=True, null=True, verbose_name='报告文件')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='load_test_tasks', verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    class Meta:
        db_table = 'performance_load_test_tasks'
        ordering = ['-created_at']
        verbose_name = '压测任务'
        verbose_name_plural = '压测任务'

    def __str__(self):
        return self.name