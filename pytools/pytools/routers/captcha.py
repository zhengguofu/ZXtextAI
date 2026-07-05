from fastapi import APIRouter, HTTPException

from pytools.schemas import (
    CaptchaAnalyzeRequest,
    CaptchaAnalyzeResponse,
    CaptchaOcrRequest,
    CaptchaOcrResponse,
    SliderDistanceRequest,
    SliderDistanceResponse,
)
from pytools.services.captcha_service import captcha_service

router = APIRouter()


@router.post("/analyze", response_model=CaptchaAnalyzeResponse)
def analyze_captcha(payload: CaptchaAnalyzeRequest) -> dict:
    try:
        return captcha_service.analyze(payload.image_base64, payload.page_html)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ocr", response_model=CaptchaOcrResponse)
def ocr_captcha(payload: CaptchaOcrRequest) -> dict:
    try:
        result = captcha_service.ocr(payload.image_base64, payload.allow_digits_only)
        return {
            "text": result.text,
            "confidence": result.confidence,
            "provider": result.provider,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/slider-distance", response_model=SliderDistanceResponse)
def slider_distance(payload: SliderDistanceRequest) -> dict:
    try:
        return captcha_service.slider_distance(
            payload.background_base64,
            payload.slider_base64,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
