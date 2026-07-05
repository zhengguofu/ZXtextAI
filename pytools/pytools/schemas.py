from pydantic import BaseModel, Field


class ImagePayload(BaseModel):
    image_base64: str = Field(..., description="图片 Base64，允许带 data:image 前缀")


class CaptchaAnalyzeRequest(ImagePayload):
    page_html: str = Field(default="", description="可选页面 HTML，用于识别验证码类型")


class CaptchaOcrRequest(ImagePayload):
    allow_digits_only: bool = Field(default=False, description="是否只保留数字")


class CaptchaAnalyzeResponse(BaseModel):
    detected: bool
    captcha_type: str
    confidence: float
    recommended_strategy: str
    message: str


class CaptchaOcrResponse(BaseModel):
    text: str
    confidence: float
    provider: str


class SliderDistanceRequest(BaseModel):
    background_base64: str
    slider_base64: str


class SliderDistanceResponse(BaseModel):
    distance: int | None
    confidence: float
    message: str
