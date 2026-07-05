"""
ASGI config for backend project.
支持 Daphne (WebSocket) 和 runserver (仅 HTTP) 两种模式
"""

import os
import sys
import logging
import signal

# Windows GBK 编码修复：强制 stdout/stderr 使用 UTF-8，避免 Emoji 导致 UnicodeEncodeError
if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

django_asgi_app = get_asgi_application()

logger = logging.getLogger(__name__)


def _graceful_shutdown(signum=None, frame=None):
    """优雅关闭：防止 I/O operation on closed file 异常"""
    try:
        logger.info(f"收到关闭信号 {signum}，正在优雅退出...")
        # 关闭所有日志 handler，避免写已关闭的文件
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            try:
                handler.flush()
                handler.close()
            except Exception:
                pass
    except Exception:
        pass
    sys.exit(0)


# 注册信号处理
for sig_name in ('SIGTERM', 'SIGINT', 'SIGHUP', 'SIGBREAK'):
    sig = getattr(signal, sig_name, None)
    if sig is not None:
        try:
            signal.signal(sig, _graceful_shutdown)
        except (ValueError, OSError):
            pass  # 非主线程中无法设置信号处理器

try:
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    from apps.app_automation import routing as app_automation_routing

    # WebSocket 路由（仅 APP 自动化）
    combined_websocket_patterns = app_automation_routing.websocket_urlpatterns

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(combined_websocket_patterns)
        ),
    })
    logger.info("ASGI 已启用 WebSocket 支持 (需通过 Daphne 启动)")
except ImportError:
    application = django_asgi_app
    logger.warning("channels 未安装，WebSocket 不可用，仅支持 HTTP")
except Exception as e:
    application = django_asgi_app
    logger.warning(f"WebSocket 初始化失败: {e}，降级为仅 HTTP 模式")