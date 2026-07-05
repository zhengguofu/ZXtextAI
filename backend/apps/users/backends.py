"""
自定义认证后端：支持明文密码自动升级
- 先用 Django 默认的哈希密码认证
- 如果失败，检查数据库里是否存的是明文密码
- 明文匹配成功后，自动将密码升级为哈希存储
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class PlainTextUpgradeBackend(ModelBackend):
    """明文密码兼容后端 —— 仅开发环境使用"""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        # 第一步：尝试 Django 默认的哈希密码认证
        user = super().authenticate(request, username=username, password=password, **kwargs)
        if user is not None:
            return user

        # 第二步：用户名不存在也直接返回
        try:
            user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            return None

        # 第三步：密码字段直接和用户输入比对（明文密码场景）
        if user.password == password:
            # 自动升级为哈希密码
            user.set_password(password)
            user.save(update_fields=['password'])
            return user

        return None
