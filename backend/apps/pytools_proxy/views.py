import logging
from typing import Any

import httpx
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def _pytools_url(path: str) -> str:
    base_url = getattr(settings, "PYTOOLS_BASE_URL", "http://127.0.0.1:8010").rstrip("/")
    return f"{base_url}/{path.lstrip('/')}"


def _forward(method: str, path: str, payload: dict[str, Any] | None = None) -> Response:
    try:
        with httpx.Client(timeout=getattr(settings, "PYTOOLS_TIMEOUT", 60.0)) as client:
            response = client.request(method, _pytools_url(path), json=payload)
        content_type = response.headers.get("content-type", "")
        data: Any = response.json() if "application/json" in content_type else {"detail": response.text}
        return Response(data, status=response.status_code)
    except httpx.ConnectError:
        return Response(
            {"detail": "pytools 服务未启动，请先启动 Python 工具服务。"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except httpx.TimeoutException:
        return Response(
            {"detail": "pytools 服务调用超时。"},
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    except Exception as exc:
        logger.exception("pytools proxy failed")
        return Response(
            {"detail": f"pytools 服务调用失败：{exc}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pytools_health(request):
    return _forward("GET", "/health")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def captcha_analyze(request):
    return _forward("POST", "/captcha/analyze", request.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def captcha_ocr(request):
    return _forward("POST", "/captcha/ocr", request.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def captcha_slider_distance(request):
    return _forward("POST", "/captcha/slider-distance", request.data)
