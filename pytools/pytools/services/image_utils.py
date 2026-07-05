import base64
import io
from typing import Final

import numpy as np
from PIL import Image, ImageOps

from pytools.config import get_settings

DATA_PREFIX: Final[str] = "base64,"


def decode_image(image_base64: str) -> Image.Image:
    settings = get_settings()
    payload = image_base64.strip()
    if DATA_PREFIX in payload:
        payload = payload.split(DATA_PREFIX, 1)[1]
    raw = base64.b64decode(payload, validate=False)
    if len(raw) > settings.max_image_bytes:
        raise ValueError(f"图片大小超过限制：{settings.max_image_bytes} bytes")
    image = Image.open(io.BytesIO(raw))
    return ImageOps.exif_transpose(image).convert("RGB")


def to_cv_gray(image: Image.Image) -> np.ndarray:
    rgb = np.array(image)
    return np.mean(rgb, axis=2).astype(np.uint8)
