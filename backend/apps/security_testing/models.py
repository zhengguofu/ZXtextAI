import uuid
from django.db import models
from apps.users.models import User


class SecurityScanTask(models.Model):
    SCAN_TYPE_CHOICES = [
        ('penetration', '渗透测试'),
        ('vulnerability', '漏洞扫描'),
    ]
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    SEVERITY_CHOICES = [
        ('critical', '严重'),
        ('high', '高危'),
        ('medium', '中危'),
        ('low', '低危'),
        ('info', '信息'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='任务名称')
    scan_type = models.CharField(max_length=20, choices=SCAN_TYPE_CHOICES, verbose_name='扫描类型')
    target = models.URLField(max_length=500, verbose_name='目标地址')
    tool = models.CharField(max_length=50, default='comprehensive', verbose_name='扫描工具')
    depth = models.IntegerField(default=1, verbose_name='扫描深度')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    total_risks = models.IntegerField(default=0, verbose_name='发现风险数')
    high_risks = models.IntegerField(default=0, verbose_name='高危风险数')
    medium_risks = models.IntegerField(default=0, verbose_name='中危风险数')
    low_risks = models.IntegerField(default=0, verbose_name='低危风险数')
    result_summary = models.TextField(blank=True, verbose_name='结果摘要')
    report_file = models.FileField(upload_to='security_reports/%Y/%m/', blank=True, null=True, verbose_name='报告文件')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='security_scan_tasks', verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    class Meta:
        db_table = 'security_scan_tasks'
        ordering = ['-created_at']
        verbose_name = '安全扫描任务'
        verbose_name_plural = '安全扫描任务'

    def __str__(self):
        return self.name


class SecurityFinding(models.Model):
    SEVERITY_CHOICES = [
        ('critical', '严重'),
        ('high', '高危'),
        ('medium', '中危'),
        ('low', '低危'),
        ('info', '信息'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(SecurityScanTask, on_delete=models.CASCADE, related_name='findings', verbose_name='所属任务')
    title = models.CharField(max_length=300, verbose_name='漏洞标题')
    detail = models.TextField(verbose_name='漏洞详情')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, verbose_name='严重程度')
    target = models.CharField(max_length=500, verbose_name='受影响目标')
    remediation = models.TextField(blank=True, verbose_name='修复建议')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='发现时间')

    class Meta:
        db_table = 'security_findings'
        ordering = ['-created_at']
        verbose_name = '安全发现'
        verbose_name_plural = '安全发现'