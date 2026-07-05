import re
from dataclasses import dataclass

import cv2
import numpy as np

from pytools.config import get_settings
from pytools.services.image_utils import decode_image, to_cv_gray


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float
    provider: str


class CaptchaService:
    _reader = None

    def analyze(self, image_base64: str, page_html: str = "") -> dict:
        html = page_html.lower()
        image = decode_image(image_base64)
        width, height = image.size

        hints = [
            "captcha",
            "verify",
            "验证码",
            "geetest",
            "aliyun",
            "tencentcaptcha",
            "slider",
        ]
        html_hit = any(keyword in html for keyword in hints)
        aspect_ratio = width / max(height, 1)

        if "slider" in html or "geetest" in html or aspect_ratio > 2.8:
            captcha_type = "slider"
            strategy = "manual_or_test_bypass"
            message = "检测到滑块/行为验证码，建议在测试环境使用白名单或人工接管。"
            confidence = 0.82 if html_hit else 0.66
        else:
            captcha_type = "image_text"
            strategy = "ocr_then_manual_review"
            message = "检测到图形验证码，可先 OCR 识别，低置信度时人工确认。"
            confidence = 0.76 if html_hit else 0.58

        return {
            "detected": html_hit or width <= 420,
            "captcha_type": captcha_type,
            "confidence": confidence,
            "recommended_strategy": strategy,
            "message": message,
        }

    def ocr(self, image_base64: str, allow_digits_only: bool = False) -> OcrResult:
        settings = get_settings()
        image = decode_image(image_base64)
        if settings.enable_easyocr:
            try:
                reader = self._get_reader()
                results = reader.readtext(np.array(image))
                if results:
                    parts: list[str] = []
                    confidences: list[float] = []
                    for _, text, confidence in results:
                        cleaned = str(text).strip()
                        if cleaned:
                            parts.append(cleaned)
                            confidences.append(float(confidence))
                    text = "".join(parts)
                    if allow_digits_only:
                        text = re.sub(r"\D+", "", text)
                    confidence = sum(confidences) / len(confidences) if confidences else 0.0
                    return OcrResult(text=text, confidence=confidence, provider="easyocr")
            except Exception:
                pass

        gray = to_cv_gray(image)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        dark_ratio = float(np.mean(binary < 128))
        return OcrResult(
            text="",
            confidence=max(0.05, min(0.35, dark_ratio)),
            provider="fallback-threshold",
        )

    def slider_distance(self, background_base64: str, slider_base64: str) -> dict:
        background = to_cv_gray(decode_image(background_base64))
        slider = to_cv_gray(decode_image(slider_base64))
        if background.shape[0] < slider.shape[0] or background.shape[1] < slider.shape[1]:
            return {
                "distance": None,
                "confidence": 0.0,
                "message": "滑块图片尺寸大于背景图，无法匹配。",
            }

        result = cv2.matchTemplate(background, slider, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        distance = int(max_loc[0])
        return {
            "distance": distance,
            "confidence": float(max_val),
            "message": "仅用于内部测试环境的滑块距离辅助识别；第三方验证码请使用人工接管或测试白名单。",
        }

    @classmethod
    def _get_reader(cls):
        if cls._reader is not None:
            return cls._reader
        settings = get_settings()
        import easyocr

        cls._reader = easyocr.Reader(settings.languages, gpu=settings.easyocr_gpu)
        return cls._reader


captcha_service = CaptchaService()
