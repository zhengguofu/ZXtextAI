from fastapi import APIRouter

from pytools.config import get_settings

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.service_name,
        "easyocr": settings.enable_easyocr,
        "languages": settings.languages,
    }
