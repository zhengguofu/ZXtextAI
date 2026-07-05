from django.apps import AppConfig

class SecurityTestingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.security_testing'
    verbose_name = '安全测试'