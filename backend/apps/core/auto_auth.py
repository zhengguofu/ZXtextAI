"""
自动认证中间件：移除登录功能后，自动设置默认系统用户。
确保 request.user 始终可用，避免全系统 401 报错。
"""
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
import logging

logger = logging.getLogger('django')

User = get_user_model()

DEFAULT_USERNAME = 'zxplatform'
DEFAULT_PASSWORD = 'ZXplatform@2024'


class AutoAuthMiddleware(MiddlewareMixin):
    """自动认证中间件：没有用户登录时自动使用系统默认用户"""

    _default_user = None
    _create_failed = False

    @classmethod
    def get_default_user(cls):
        if cls._default_user is not None:
            return cls._default_user

        # 如果之前创建失败过，直接返回 None
        if cls._create_failed:
            return None

        try:
            user = User.objects.filter(username=DEFAULT_USERNAME).first()
            if not user:
                user = User.objects.create_superuser(
                    username=DEFAULT_USERNAME,
                    email='platform@zx.local',
                    password=DEFAULT_PASSWORD,
                    first_name='ZX',
                    last_name='Platform'
                )
                logger.info(f"Created default system user: {DEFAULT_USERNAME}")
            cls._default_user = user
            return user
        except Exception as e:
            logger.warning(f"Failed to get/create default user: {e}")
            cls._create_failed = True
            return None

    def process_request(self, request):
        # 确保 request.user 始终有值
        if not hasattr(request, 'user'):
            request.user = AnonymousUser()

        if not request.user.is_authenticated:
            user = self.get_default_user()
            if user:
                request.user = user
