"""
Redis 客户端工具
从 Django settings 的 REDIS_URL 创建 Redis 连接
如果 Redis 不可用，使用内存字典作为 fallback
"""
import redis as redis_lib
from django.conf import settings


class MemoryRedis:
    """内存版 Redis fallback，用于本地开发无 Redis 环境"""

    def __init__(self):
        self._data = {}
        self._expiry = {}

    def _clean_expired(self, key):
        import time
        if key in self._expiry and time.time() > self._expiry[key]:
            del self._data[key]
            del self._expiry[key]
            return True
        return False

    def setex(self, key, ttl, value):
        import time
        self._data[key] = value
        self._expiry[key] = time.time() + ttl

    def get(self, key):
        if self._clean_expired(key):
            return None
        return self._data.get(key)

    def delete(self, key):
        self._data.pop(key, None)
        self._expiry.pop(key, None)


def get_redis():
    """获取 Redis 连接（懒加载，复用连接），Redis 不可用时自动降级为内存缓存"""
    if not hasattr(get_redis, '_client'):
        try:
            client = redis_lib.from_url(settings.REDIS_URL)
            client.ping()  # 测试连接
            get_redis._client = client
        except Exception:
            import warnings
            warnings.warn("Redis 不可用，使用内存缓存作为 fallback（重启后验证码等数据会丢失）")
            get_redis._client = MemoryRedis()
    return get_redis._client
