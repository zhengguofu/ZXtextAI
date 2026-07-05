"""
验证码高级工具集
提供更强大的验证码处理能力
"""
import asyncio
import base64
import io
import json
import logging
import random
import re
import time
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False


class CaptchaToolType(Enum):
    """验证码工具类型"""
    SLIDER_GAP_FINDER = auto()
    IMAGE_ENHANCER = auto()
    TEXT_RECOGNIZER = auto()
    CLICK_POINT_FINDER = auto()
    PATTERN_MATCHER = auto()


@dataclass
class SliderGapResult:
    """滑块缺口结果"""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.0
    method: str = ""
    debug_image: Optional[bytes] = None


@dataclass
class TextRecognitionResult:
    """文本识别结果"""
    text: str = ""
    confidence: float = 0.0
    method: str = ""
    candidates: List[Tuple[str, float]] = None

    def __post_init__(self):
        if self.candidates is None:
            self.candidates = []


class ImageProcessorTool:
    """图像处理工具"""

    @staticmethod
    def bytes_to_cv2(image_bytes: bytes) -> Optional['np.ndarray']:
        """字节转OpenCV图像"""
        if not OPENCV_AVAILABLE:
            return None
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            logger.debug(f"bytes_to_cv2 failed: {e}")
            return None

    @staticmethod
    def cv2_to_bytes(img: 'np.ndarray', format: str = '.png') -> Optional[bytes]:
        """OpenCV图像转字节"""
        if not OPENCV_AVAILABLE:
            return None
        try:
            success, buffer = cv2.imencode(format, img)
            if success:
                return buffer.tobytes()
            return None
        except Exception as e:
            logger.debug(f"cv2_to_bytes failed: {e}")
            return None

    @staticmethod
    def bytes_to_pillow(image_bytes: bytes) -> Optional['Image.Image']:
        """字节转Pillow图像"""
        if not PILLOW_AVAILABLE:
            return None
        try:
            return Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            logger.debug(f"bytes_to_pillow failed: {e}")
            return None

    @staticmethod
    def pillow_to_bytes(img: 'Image.Image', format: str = 'PNG') -> Optional[bytes]:
        """Pillow图像转字节"""
        if not PILLOW_AVAILABLE:
            return None
        try:
            buf = io.BytesIO()
            img.save(buf, format=format)
            return buf.getvalue()
        except Exception as e:
            logger.debug(f"pillow_to_bytes failed: {e}")
            return None

    @staticmethod
    def enhance_for_ocr(image_bytes: bytes) -> bytes:
        """增强图像以提高OCR准确率"""
        img_bytes = image_bytes

        if PILLOW_AVAILABLE:
            try:
                img = ImageProcessorTool.bytes_to_pillow(image_bytes)
                if img:
                    # 转为灰度
                    if img.mode != 'L':
                        img = img.convert('L')

                    # 增强对比度
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(2.0)

                    # 增强锐度
                    enhancer = ImageEnhance.Sharpness(img)
                    img = enhancer.enhance(1.5)

                    img_bytes = ImageProcessorTool.pillow_to_bytes(img) or image_bytes
            except Exception as e:
                logger.debug(f"Pillow enhance failed: {e}")

        if OPENCV_AVAILABLE and img_bytes:
            try:
                img = ImageProcessorTool.bytes_to_cv2(img_bytes)
                if img is not None:
                    # 转为灰度
                    if len(img.shape) == 3:
                        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    else:
                        gray = img

                    # 二值化
                    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                    # 去噪
                    kernel = np.ones((2, 2), np.uint8)
                    denoised = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

                    img_bytes = ImageProcessorTool.cv2_to_bytes(denoised) or img_bytes
            except Exception as e:
                logger.debug(f"OpenCV enhance failed: {e}")

        return img_bytes or image_bytes


class SliderGapFinder:
    """滑块缺口查找器"""

    @staticmethod
    def find_gap_multi_method(
        bg_bytes: bytes,
        slider_bytes: bytes = None,
        methods: List[str] = None
    ) -> SliderGapResult:
        """
        多种方法查找缺口

        Args:
            bg_bytes: 背景图
            slider_bytes: 滑块图（可选）
            methods: 使用的方法列表

        Returns:
            SliderGapResult
        """
        if methods is None:
            methods = ['edge_detection', 'template_match', 'color_diff', 'contour']

        results: List[SliderGapResult] = []

        for method in methods:
            try:
                if method == 'edge_detection' and OPENCV_AVAILABLE:
                    result = SliderGapFinder._find_by_edge_detection(bg_bytes)
                    if result and result.confidence > 0.5:
                        results.append(result)

                elif method == 'template_match' and OPENCV_AVAILABLE and slider_bytes:
                    result = SliderGapFinder._find_by_template_match(bg_bytes, slider_bytes)
                    if result and result.confidence > 0.3:
                        results.append(result)

                elif method == 'color_diff' and OPENCV_AVAILABLE:
                    result = SliderGapFinder._find_by_color_diff(bg_bytes)
                    if result and result.confidence > 0.4:
                        results.append(result)

                elif method == 'contour' and OPENCV_AVAILABLE:
                    result = SliderGapFinder._find_by_contour(bg_bytes)
                    if result and result.confidence > 0.4:
                        results.append(result)
            except Exception as e:
                logger.debug(f"Method {method} failed: {e}")

        if not results:
            return SliderGapResult(method='all_failed')

        # 选择置信度最高的结果
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results[0]

    @staticmethod
    def _find_by_edge_detection(image_bytes: bytes) -> Optional[SliderGapResult]:
        """通过边缘检测找缺口"""
        img = ImageProcessorTool.bytes_to_cv2(image_bytes)
        if img is None:
            return None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        # 边缘检测
        edges = cv2.Canny(gray, 50, 150)

        # 查找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_gap = None
        max_score = 0

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            # 筛选滑块缺口特征
            aspect_ratio = w / h if h > 0 else 0
            area = w * h

            # 滑块缺口通常宽高比在0.8-2.5之间
            if 0.8 <= aspect_ratio <= 2.5 and 500 <= area <= 50000:
                score = min(1.0, area / 10000)

                if score > max_score:
                    max_score = score
                    best_gap = SliderGapResult(
                        x=x, y=y, width=w, height=h,
                        confidence=score, method='edge_detection'
                    )

        return best_gap

    @staticmethod
    def _find_by_template_match(bg_bytes: bytes, slider_bytes: bytes) -> Optional[SliderGapResult]:
        """通过模板匹配找缺口"""
        bg = ImageProcessorTool.bytes_to_cv2(bg_bytes)
        slider = ImageProcessorTool.bytes_to_cv2(slider_bytes)

        if bg is None or slider is None:
            return None

        bg_gray = cv2.cvtColor(bg, cv2.COLOR_BGR2GRAY) if len(bg.shape) == 3 else bg
        slider_gray = cv2.cvtColor(slider, cv2.COLOR_BGR2GRAY) if len(slider.shape) == 3 else slider

        # 模板匹配
        result = cv2.matchTemplate(bg_gray, slider_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > 0.3:
            return SliderGapResult(
                x=max_loc[0], y=max_loc[1],
                width=slider_gray.shape[1], height=slider_gray.shape[0],
                confidence=max_val, method='template_match'
            )

        return None

    @staticmethod
    def _find_by_color_diff(image_bytes: bytes) -> Optional[SliderGapResult]:
        """通过颜色差异找缺口"""
        img = ImageProcessorTool.bytes_to_cv2(image_bytes)
        if img is None:
            return None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        # 模糊处理
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # 差分
        diff = cv2.absdiff(gray, blurred)

        # 阈值
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

        # 形态学操作
        kernel = np.ones((5, 5), np.uint8)
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h

            if 500 <= area <= 50000 and 0.8 <= w/h <= 2.5:
                return SliderGapResult(
                    x=x, y=y, width=w, height=h,
                    confidence=min(1.0, area / 8000),
                    method='color_diff'
                )

        return None

    @staticmethod
    def _find_by_contour(image_bytes: bytes) -> Optional[SliderGapResult]:
        """通过轮廓找缺口"""
        img = ImageProcessorTool.bytes_to_cv2(image_bytes)
        if img is None:
            return None

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        # 自适应阈值
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            # 近似多边形
            approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)

            # 滑块缺口通常是四边形或接近四边形
            if 4 <= len(approx) <= 8:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h

                if 500 <= area <= 50000:
                    return SliderGapResult(
                        x=x, y=y, width=w, height=h,
                        confidence=min(1.0, area / 10000),
                        method='contour'
                    )

        return None


class OCRTool:
    """OCR工具"""

    _easyocr_reader = None

    @classmethod
    def _get_easyocr_reader(cls, lang_list: List[str] = None):
        """获取EasyOCR阅读器"""
        if not EASYOCR_AVAILABLE:
            return None

        if lang_list is None:
            lang_list = ['en', 'ch_sim']

        if cls._easyocr_reader is None:
            try:
                cls._easyocr_reader = easyocr.Reader(lang_list, gpu=False)
            except Exception as e:
                logger.debug(f"EasyOCR init failed: {e}")

        return cls._easyocr_reader

    @classmethod
    def recognize_text(
        cls,
        image_bytes: bytes,
        lang_list: List[str] = None,
        enhance: bool = True
    ) -> TextRecognitionResult:
        """
        识别文本

        Args:
            image_bytes: 图像字节
            lang_list: 语言列表
            enhance: 是否增强图像

        Returns:
            TextRecognitionResult
        """
        result = TextRecognitionResult()

        processed_bytes = image_bytes
        if enhance:
            processed_bytes = ImageProcessorTool.enhance_for_ocr(image_bytes)

        # 尝试EasyOCR
        if EASYOCR_AVAILABLE:
            try:
                reader = cls._get_easyocr_reader(lang_list)
                if reader:
                    ocr_results = reader.readtext(processed_bytes)
                    if ocr_results:
                        full_text = ''.join([r[1] for r in ocr_results])
                        confidence = sum(r[2] for r in ocr_results) / len(ocr_results) if ocr_results else 0

                        result.text = full_text
                        result.confidence = confidence
                        result.method = 'easyocr'
                        result.candidates = [(r[1], r[2]) for r in ocr_results]

                        return result
            except Exception as e:
                logger.debug(f"EasyOCR failed: {e}")

        # 尝试其他方法...
        result.text = ""
        result.confidence = 0.0
        result.method = 'none'
        return result

    @staticmethod
    def clean_captcha_text(text: str) -> str:
        """清理验证码文本"""
        # 只保留字母数字
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', text)
        return cleaned


class HumanTrajectoryGenerator:
    """拟人化轨迹生成器"""

    @staticmethod
    def generate_trajectory(
        start_x: float, start_y: float,
        end_x: float, end_y: float,
        steps: int = None,
        randomness: float = 0.5
    ) -> List[Tuple[float, float, float]]:
        """
        生成拟人化移动轨迹

        Args:
            start_x: 起始X
            start_y: 起始Y
            end_x: 结束X
            end_y: 结束Y
            steps: 步数
            randomness: 随机程度 0-1

        Returns:
            [(x, y, delay_ms), ...]
        """
        if steps is None:
            distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
            steps = max(30, min(100, int(distance / 3)))

        trajectory = []

        for i in range(steps):
            t = i / (steps - 1)

            # 使用 ease-in-out 缓动函数
            if t < 0.2:
                progress = t * t * 2.5
            elif t < 0.8:
                progress = 0.5 + (t - 0.2) * 1.25
            else:
                progress = 1 - (1 - t) * (1 - t) * 2.5

            # 计算基础位置
            x = start_x + (end_x - start_x) * progress
            y = start_y + (end_y - start_y) * progress

            # 添加随机波动
            if randomness > 0:
                wave_amount = randomness * 10
                x += random.uniform(-wave_amount, wave_amount)
                y += random.uniform(-wave_amount / 2, wave_amount / 2)

            # 计算延迟（前面快后面慢）
            if t < 0.3:
                delay = random.uniform(5, 15)
            elif t < 0.8:
                delay = random.uniform(10, 25)
            else:
                delay = random.uniform(15, 40)

            trajectory.append((x, y, delay))

        return trajectory

    @staticmethod
    def generate_slide_trajectory(
        start_x: float, start_y: float,
        distance: float,
        extra_back: float = 0.1
    ) -> List[Tuple[float, float, float]]:
        """
        生成滑块拖拽轨迹

        Args:
            start_x: 起始X
            start_y: 起始Y
            distance: 移动距离
            extra_back: 往回拉的比例

        Returns:
            [(x, y, delay_ms), ...]
        """
        trajectory = []

        end_x = start_x + distance

        # 主要移动阶段
        main_trajectory = HumanTrajectoryGenerator.generate_trajectory(
            start_x, start_y, end_x, start_y,
            steps=random.randint(40, 70),
            randomness=0.6
        )
        trajectory.extend(main_trajectory)

        # 往回微调（模拟人手对准）
        if extra_back > 0:
            back_distance = distance * extra_back * random.uniform(0.5, 1.0)
            back_trajectory = HumanTrajectoryGenerator.generate_trajectory(
                end_x, start_y, end_x - back_distance, start_y,
                steps=random.randint(5, 15),
                randomness=0.3
            )
            trajectory.extend(back_trajectory)

        return trajectory


class CaptchaPatternMatcher:
    """验证码模式匹配器"""

    # 常见验证码模式
    PATTERNS = {
        'aliyun_nc': [
            r'nc-', r'nc_', r'aliyun.*captcha', r'nocaptcha'
        ],
        'geetest': [
            r'geetest', r'gt_', r'popup-captcha'
        ],
        'recaptcha_v2': [
            r'recaptcha/api2', r'g-recaptcha'
        ],
        'recaptcha_v3': [
            r'recaptcha/api3', r'grecaptcha.execute'
        ],
        'hcaptcha': [
            r'hcaptcha', r'h-captcha'
        ],
        'turnstile': [
            r'turnstile', r'challenges.cloudflare'
        ],
    }

    @classmethod
    def detect_captcha_type(cls, html: str, url: str = '') -> Tuple[str, float]:
        """
        检测验证码类型

        Args:
            html: 页面HTML
            url: 页面URL

        Returns:
            (type_name, confidence)
        """
        text = html.lower() + ' ' + url.lower()

        best_match = 'unknown'
        best_confidence = 0.0

        for captcha_type, patterns in cls.PATTERNS.items():
            match_count = sum(1 for p in patterns if re.search(p, text))
            if match_count > 0:
                confidence = min(1.0, match_count / 2)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = captcha_type

        return best_match, best_confidence


# 便捷函数
def process_slider_captcha(
    bg_image: bytes,
    slider_image: bytes = None
) -> SliderGapResult:
    """处理滑块验证码"""
    return SliderGapFinder.find_gap_multi_method(bg_image, slider_image)


def recognize_captcha_text(
    image_bytes: bytes,
    enhance: bool = True
) -> TextRecognitionResult:
    """识别验证码文本"""
    return OCRTool.recognize_text(image_bytes, enhance=enhance)


def generate_human_slide(
    start_x: float, start_y: float,
    distance: float
) -> List[Tuple[float, float, float]]:
    """生成拟人化滑块轨迹"""
    return HumanTrajectoryGenerator.generate_slide_trajectory(start_x, start_y, distance)
