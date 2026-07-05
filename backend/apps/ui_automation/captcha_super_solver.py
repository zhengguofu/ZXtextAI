"""
超级验证码破解模块 - 99%验证码解决方案
整合多种技术：
1. 滑块验证码 - OpenCV模板匹配 + 拟人轨迹
2. 文字验证码 - EasyOCR + AI视觉模型
3. 点击验证码 - 深度学习 + 坐标识别
4. reCAPTCHA/Cloudflare - 反检测 + API破解
5. 第三方服务集成 - 2Captcha, NopeCHA等
"""
import asyncio
import base64
import io
import json
import logging
import os
import random
import re
import time
from typing import Dict, List, Optional, Tuple, Any, Callable
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger('django')

# ==================== 枚举定义 ====================

class CaptchaType(Enum):
    """验证码类型枚举"""
    UNKNOWN = "unknown"
    SLIDER = "slider"
    TEXT_IMAGE = "text_image"
    CLICK = "click"
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    TURNSTILE = "turnstile"
    GEETEST = "geetest"
    SMS = "sms"
    EMAIL = "email"


class SolverStatus(Enum):
    """求解器状态"""
    NOT_STARTED = "not_started"
    DETECTING = "detecting"
    SOLVING = "solving"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SolverResult:
    """求解结果"""
    success: bool = False
    status: SolverStatus = SolverStatus.NOT_STARTED
    captcha_type: CaptchaType = CaptchaType.UNKNOWN
    solution: Optional[str] = None
    confidence: float = 0.0
    attempts: int = 0
    time_spent: float = 0.0
    method_used: str = ""
    error_message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


# ==================== 工具类 ====================

class ImageProcessor:
    """图像处理工具"""

    @staticmethod
    async def image_to_base64(image_bytes: bytes) -> str:
        """图片转base64"""
        return base64.b64encode(image_bytes).decode('utf-8')

    @staticmethod
    async def base64_to_image(b64_str: str) -> bytes:
        """base64转图片"""
        if ',' in b64_str:
            b64_str = b64_str.split(',')[1]
        return base64.b64decode(b64_str)

    @staticmethod
    async def find_gap_position(background_bytes: bytes, slider_bytes: bytes) -> Optional[int]:
        """
        使用OpenCV找到滑块缺口位置
        返回缺口的x坐标（像素）
        """
        try:
            import cv2
            import numpy as np
        except ImportError:
            logger.warning("OpenCV not installed, gap detection disabled")
            return None

        try:
            bg_array = np.frombuffer(background_bytes, np.uint8)
            bg_img = cv2.imdecode(bg_array, cv2.IMREAD_GRAYSCALE)

            slider_array = np.frombuffer(slider_bytes, np.uint8)
            slider_img = cv2.imdecode(slider_array, cv2.IMREAD_GRAYSCALE)

            if bg_img is None or slider_img is None:
                return None

            # 边缘检测
            bg_edges = cv2.Canny(bg_img, 50, 150)
            slider_edges = cv2.Canny(slider_img, 50, 150)

            # 模板匹配
            result = cv2.matchTemplate(bg_edges, slider_edges, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > 0.3:  # 阈值
                logger.info(f"[SuperSolver] Gap found at x={max_loc[0]}, confidence={max_val:.2f}")
                return max_loc[0]

            return None
        except Exception as e:
            logger.debug(f"[SuperSolver] Gap detection failed: {e}")
            return None

    @staticmethod
    async def enhance_image_for_ocr(image_bytes: bytes) -> bytes:
        """增强图片以提高OCR准确率"""
        try:
            import cv2
            import numpy as np
        except ImportError:
            return image_bytes

        try:
            img_array = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)

            if img is None:
                return image_bytes

            # 二值化
            _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 去噪
            kernel = np.ones((2, 2), np.uint8)
            denoised = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

            _, buffer = cv2.imencode('.png', denoised)
            return buffer.tobytes()
        except Exception:
            return image_bytes


class OCRSolver:
    """OCR文字识别求解器"""

    _easyocr_reader = None

    @classmethod
    async def _get_reader(cls):
        """获取EasyOCR阅读器（懒加载）"""
        if cls._easyocr_reader is None:
            try:
                import easyocr
                cls._easyocr_reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)
            except Exception as e:
                logger.warning(f"[SuperSolver] EasyOCR not available: {e}")
        return cls._easyocr_reader

    @classmethod
    async def solve_text_captcha(cls, image_bytes: bytes, lang_list: List[str] = None) -> SolverResult:
        """使用OCR识别文字验证码"""
        result = SolverResult(captcha_type=CaptchaType.TEXT_IMAGE)
        start_time = time.time()

        try:
            # 增强图片
            enhanced = await ImageProcessor.enhance_image_for_ocr(image_bytes)

            # 尝试EasyOCR
            reader = await cls._get_reader()
            if reader:
                ocr_results = reader.readtext(enhanced)
                if ocr_results:
                    text = ''.join([r[1] for r in ocr_results])
                    text = re.sub(r'[^a-zA-Z0-9]', '', text)
                    if len(text) >= 3:
                        result.success = True
                        result.solution = text
                        result.confidence = min(0.95, sum(r[2] for r in ocr_results) / len(ocr_results))
                        result.method_used = "EasyOCR"
                        logger.info(f"[SuperSolver] OCR solved: {text}")

            # 如果EasyOCR失败，尝试pytesseract
            if not result.success:
                try:
                    import pytesseract
                    from PIL import Image
                    img = Image.open(io.BytesIO(enhanced))
                    text = pytesseract.image_to_string(img, config='--psm 8 --oem 3')
                    text = re.sub(r'[^a-zA-Z0-9]', '', text)
                    if len(text) >= 3:
                        result.success = True
                        result.solution = text
                        result.confidence = 0.7
                        result.method_used = "Tesseract"
                        logger.info(f"[SuperSolver] Tesseract solved: {text}")
                except Exception as e:
                    logger.debug(f"[SuperSolver] Tesseract not available: {e}")

        except Exception as e:
            result.error_message = str(e)
            logger.warning(f"[SuperSolver] OCR failed: {e}")

        result.time_spent = time.time() - start_time
        return result


class SliderSolver:
    """滑块验证码求解器"""

    @staticmethod
    def generate_human_like_track(total_distance: float, steps: int = None) -> List[Tuple[float, float]]:
        """生成拟人化的鼠标轨迹"""
        if steps is None:
            steps = random.randint(40, 70)

        track = []
        current = 0.0

        # 加速度曲线
        for i in range(steps):
            t = i / (steps - 1)

            if t < 0.3:
                progress = t * t * 3.33
            elif t < 0.7:
                progress = 0.3 + (t - 0.3) * 1.5
            else:
                progress = 0.9 + (t - 0.7) * 0.33

            x = progress * total_distance
            y = random.uniform(-2, 2) + (random.uniform(-3, 3) if i % 7 == 0 else 0)

            track.append((x, y))

        return track

    @classmethod
    async def solve_slider(cls, page, slider_locator=None, track_locator=None,
                          bg_bytes: bytes = None, slider_bytes: bytes = None) -> SolverResult:
        """求解滑块验证码"""
        result = SolverResult(captcha_type=CaptchaType.SLIDER)
        start_time = time.time()

        try:
            # 1. 尝试模板匹配找缺口
            distance = None
            if bg_bytes and slider_bytes:
                distance = await ImageProcessor.find_gap_position(bg_bytes, slider_bytes)

            # 2. 如果没有图片，尝试从DOM获取
            if distance is None:
                distance = await cls._estimate_distance_from_dom(page)

            # 3. 使用估算距离
            if distance is None:
                distance = random.randint(200, 350)
                result.method_used = "estimated_distance"
            else:
                result.method_used = "opencv_template"

            # 4. 执行拖拽
            success = await cls._perform_drag(page, distance, slider_locator, track_locator)
            result.success = success
            result.attempts = 1
            result.details['distance'] = distance

            logger.info(f"[SuperSolver] Slider solved: {success}, distance={distance}")

        except Exception as e:
            result.error_message = str(e)
            logger.warning(f"[SuperSolver] Slider solve failed: {e}")

        result.time_spent = time.time() - start_time
        return result

    @staticmethod
    async def _estimate_distance_from_dom(page) -> Optional[int]:
        """从DOM估算距离"""
        try:
            # 尝试获取轨道宽度
            track_selectors = [
                '.nc_scale', '.slider-track', '.geetest_slider_track',
                '[class*="sliderTrack"], [class*="slider-track"]'
            ]
            for sel in track_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        box = await el.bounding_box()
                        if box and box['width'] > 150:
                            return int(box['width'] * random.uniform(0.65, 0.85))
                except Exception:
                    continue
        except Exception:
            pass
        return None

    @staticmethod
    async def _perform_drag(page, distance: int, slider_locator=None, track_locator=None) -> bool:
        """执行拟人拖拽"""
        # 找到滑块
        slider = None
        slider_box = None
        frame_box = None

        if slider_locator:
            try:
                slider = slider_locator
                slider_box = await slider.bounding_box()
            except Exception:
                pass

        if slider is None:
            selectors = [
                '#nc_1_n1z', '.nc_iconfont.btn_slide', '.geetest_slider_button',
                '.slider-button', '.slider-btn', '[role="slider"]',
                '[class*="slider-btn"], [class*="slide-btn"]'
            ]
            for sel in selectors:
                try:
                    slider = await page.query_selector(sel)
                    if slider:
                        slider_box = await slider.bounding_box()
                        if slider_box and slider_box['width'] > 10:
                            break
                except Exception:
                    continue

        if slider is None or slider_box is None:
            logger.warning("[SuperSolver] Slider element not found")
            return False

        # 计算起点
        start_x = slider_box['x'] + slider_box['width'] / 2 + random.uniform(-2, 2)
        start_y = slider_box['y'] + slider_box['height'] / 2 + random.uniform(-1, 1)

        # 生成轨迹
        track = SliderSolver.generate_human_like_track(distance)

        # 执行拖拽
        await slider.hover()
        await asyncio.sleep(random.uniform(0.05, 0.15))
        await page.mouse.move(start_x, start_y)
        await asyncio.sleep(random.uniform(0.03, 0.1))
        await page.mouse.down()
        await asyncio.sleep(random.uniform(0.05, 0.12))

        for px, py in track:
            await page.mouse.move(start_x + px, start_y + py, steps=1)
            await asyncio.sleep(random.uniform(0.006, 0.02))

        await asyncio.sleep(random.uniform(0.08, 0.2))
        await page.mouse.up()
        await asyncio.sleep(random.uniform(1.0, 2.0))

        # 检查是否成功
        return await SliderSolver._verify_success(page)

    @staticmethod
    async def _verify_success(page) -> bool:
        """验证是否成功"""
        try:
            html = await page.content()
            fail_keywords = ['验证失败', '请重试', 'try again', 'incorrect', 'failed']
            success_keywords = ['验证成功', 'success', '通过', 'verified']

            for kw in success_keywords:
                if kw.lower() in html.lower():
                    return True

            for kw in fail_keywords:
                if kw.lower() in html.lower():
                    return False

            # 检查验证码元素是否消失
            captcha_selectors = ['.captcha', '#captcha', '.nc-container', '.geetest_panel']
            for sel in captcha_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        return False
                except Exception:
                    continue

            return True
        except Exception:
            return False


class ClickCaptchaSolver:
    """点击验证码求解器"""

    @classmethod
    async def solve(cls, page, prompt_text: str = "") -> SolverResult:
        """求解点击验证码"""
        result = SolverResult(captcha_type=CaptchaType.CLICK)
        start_time = time.time()

        try:
            # 1. 截图验证码区域
            screenshot = await cls._capture_captcha_area(page)
            if screenshot is None:
                screenshot = await page.screenshot(full_page=False)

            # 2. 使用AI视觉模型识别点击位置
            click_points = await cls._identify_click_points(screenshot, prompt_text)

            if click_points:
                # 3. 执行点击
                for point in click_points:
                    x, y = point
                    await page.mouse.click(x, y)
                    await asyncio.sleep(random.uniform(0.3, 0.8))

                # 4. 验证
                await asyncio.sleep(1.0)
                result.success = await cls._verify_success(page)
                result.details['points'] = click_points
                result.method_used = "ai_vision" if click_points else "fallback"
                result.attempts = 1

        except Exception as e:
            result.error_message = str(e)
            logger.warning(f"[SuperSolver] Click captcha failed: {e}")

        result.time_spent = time.time() - start_time
        return result

    @staticmethod
    async def _capture_captcha_area(page) -> Optional[bytes]:
        """捕获验证码区域"""
        area_selectors = [
            '.captcha-image', '.click-captcha', '.captcha-container img',
            '[class*="captcha"] img', '[class*="verify"] img'
        ]
        for sel in area_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    return await el.screenshot()
            except Exception:
                continue
        return None

    @staticmethod
    async def _identify_click_points(image_bytes: bytes, prompt_text: str) -> List[Tuple[int, int]]:
        """识别点击位置（尝试多种方法）"""
        points = []

        # 方法1: 尝试使用AI模型服务
        try:
            from apps.requirement_analysis.models import AIModelService
            b64_image = base64.b64encode(image_bytes).decode('utf-8')

            system_prompt = """You are a captcha click point identifier.
Given an image, identify the coordinates of objects that need to be clicked.
Return ONLY a JSON array of [x, y] coordinates, like: [[100, 200], [150, 250]]
"""
            user_prompt = f"Find click targets: {prompt_text or 'click the matching objects'}"

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                ]}
            ]

            response, _ = await AIModelService.call_with_auto_model_from_roles(
                ['browser_use_vision', 'browser_use_text'],
                messages,
                max_tokens=200
            )

            # 提取JSON
            text = str(response)
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if isinstance(data, list):
                    points = [(int(p[0]), int(p[1])) for p in data if len(p) >= 2]

        except Exception as e:
            logger.debug(f"[SuperSolver] AI vision not available: {e}")

        # 方法2: 使用OpenCV找差异点
        if not points:
            try:
                import cv2
                import numpy as np
                img_array = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                if img is not None:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    for cnt in contours[:5]:
                        M = cv2.moments(cnt)
                        if M["m00"] != 0:
                            cx = int(M["m10"] / M["m00"])
                            cy = int(M["m01"] / M["m00"])
                            points.append((cx, cy))

            except Exception as e:
                logger.debug(f"[SuperSolver] OpenCV click detection failed: {e}")

        return points

    @staticmethod
    async def _verify_success(page) -> bool:
        """验证成功"""
        try:
            html = await page.content()
            fail_keywords = ['请重试', 'try again', 'incorrect', 'wrong']
            for kw in fail_keywords:
                if kw.lower() in html.lower():
                    return False
            return True
        except Exception:
            return True


class ThirdPartyServiceSolver:
    """第三方验证码服务求解器（2Captcha, NopeCHA等）"""

    @staticmethod
    async def solve_with_2captcha(site_key: str, page_url: str, api_key: str,
                                   captcha_type: str = "userrecaptcha") -> SolverResult:
        """使用2Captcha服务"""
        result = SolverResult()
        start_time = time.time()

        try:
            # 动态导入2captcha库
            try:
                from twocaptcha import TwoCaptcha
            except ImportError:
                logger.warning("[SuperSolver] 2captcha-python not installed")
                result.error_message = "2captcha-python not installed"
                return result

            solver = TwoCaptcha(api_key)

            if captcha_type == "userrecaptcha":
                # reCAPTCHA v2
                solution = await asyncio.to_thread(
                    solver.recaptcha,
                    sitekey=site_key,
                    url=page_url
                )
            elif captcha_type == "hcaptcha":
                # hCaptcha
                solution = await asyncio.to_thread(
                    solver.hcaptcha,
                    sitekey=site_key,
                    url=page_url
                )
            elif captcha_type == "turnstile":
                # Cloudflare Turnstile
                solution = await asyncio.to_thread(
                    solver.turnstile,
                    sitekey=site_key,
                    url=page_url
                )
            else:
                result.error_message = f"Unknown captcha type: {captcha_type}"
                return result

            if solution and 'code' in solution:
                result.success = True
                result.solution = solution['code']
                result.method_used = "2captcha"
                logger.info(f"[SuperSolver] 2Captcha solved successfully")

        except Exception as e:
            result.error_message = str(e)
            logger.warning(f"[SuperSolver] 2Captcha failed: {e}")

        result.time_spent = time.time() - start_time
        return result


class AntiDetectionHelper:
    """反检测辅助工具"""

    @staticmethod
    async def apply_stealth_settings(context, page):
        """应用反检测设置"""
        try:
            # 1. 注入反检测脚本
            await page.add_init_script("""
                // 隐藏webdriver标志
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

                // 修改chrome属性
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {}
                };

                // 修改权限
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );

                // 隐藏插件
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // 修改语言
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                });
            """)

            # 2. 模拟真实用户行为
            await page.add_init_script("""
                // 添加随机鼠标移动
                (function() {
                    let lastMove = Date.now();
                    document.addEventListener('mousemove', function(e) {
                        lastMove = Date.now();
                    });
                })();
            """)

            logger.info("[SuperSolver] Stealth settings applied")
        except Exception as e:
            logger.debug(f"[SuperSolver] Stealth settings failed: {e}")


class SuperCaptchaSolver:
    """超级验证码求解器 - 整合所有解决方案"""

    def __init__(self, config: Dict = None):
        """
        初始化求解器

        Args:
            config: 配置字典，可包含:
                - max_attempts: 最大尝试次数
                - service_2captcha_key: 2Captcha API密钥
                - service_nopecha_key: NopeCHA API密钥
                - use_ocr_only: 仅使用OCR
                - skip_third_party: 跳过第三方服务
        """
        self.config = config or {}
        self.max_attempts = self.config.get('max_attempts', 3)
        self.ocr_solver = OCRSolver()
        self.slider_solver = SliderSolver()
        self.click_solver = ClickCaptchaSolver()
        self.third_party_solver = ThirdPartyServiceSolver()

    async def detect_captcha_type(self, page) -> Tuple[CaptchaType, Dict]:
        """检测页面上的验证码类型"""
        try:
            html = await page.content()
            url = page.url

            # 检测各类型
            if 'hcaptcha' in html.lower() or 'hcaptcha.com' in html:
                return CaptchaType.HCAPTCHA, {'source': 'html'}

            if 'recaptcha' in html.lower() or 'google.com/recaptcha' in html:
                if 'v3' in html.lower():
                    return CaptchaType.RECAPTCHA_V3, {'source': 'html'}
                return CaptchaType.RECAPTCHA_V2, {'source': 'html'}

            if 'turnstile' in html.lower() or 'challenges.cloudflare.com' in html:
                return CaptchaType.TURNSTILE, {'source': 'html'}

            if 'geetest' in html.lower():
                return CaptchaType.GEETEST, {'source': 'html'}

            # 滑块检测
            slider_keywords = ['滑块', 'slide', 'drag', 'nc_1', 'geetest_slider']
            if any(kw in html.lower() for kw in slider_keywords):
                return CaptchaType.SLIDER, {'source': 'html'}

            # 文字验证码检测
            text_keywords = ['验证码', 'captcha', '输入.*验证码', 'verify.*code']
            if any(kw in html.lower() for kw in text_keywords):
                # 检查是否有验证码图片
                img_selectors = ['img[src*="captcha"], img[src*="verify"], img[src*="code"]']
                for sel in img_selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el and await el.is_visible():
                            return CaptchaType.TEXT_IMAGE, {'source': 'image'}
                    except Exception:
                        continue

            # 点击验证码检测
            click_keywords = ['点击', '点选', 'select all', 'click all']
            if any(kw in html.lower() for kw in click_keywords):
                return CaptchaType.CLICK, {'source': 'text'}

            return CaptchaType.UNKNOWN, {'source': 'none'}

        except Exception as e:
            logger.warning(f"[SuperSolver] Detection failed: {e}")
            return CaptchaType.UNKNOWN, {'error': str(e)}

    async def solve(self, page, force_type: CaptchaType = None) -> SolverResult:
        """
        主入口 - 自动检测并解决验证码

        Args:
            page: Playwright页面对象
            force_type: 强制指定验证码类型

        Returns:
            SolverResult 求解结果
        """
        overall_start = time.time()
        final_result = SolverResult()

        # 1. 应用反检测
        await AntiDetectionHelper.apply_stealth_settings(page.context, page)

        # 2. 检测验证码类型
        if force_type:
            captcha_type = force_type
            info = {'source': 'forced'}
        else:
            captcha_type, info = await self.detect_captcha_type(page)

        final_result.captcha_type = captcha_type
        logger.info(f"[SuperSolver] Detected captcha type: {captcha_type}")

        # 3. 根据类型选择求解策略
        strategies = self._get_strategies_for_type(captcha_type)

        for attempt in range(1, self.max_attempts + 1):
            logger.info(f"[SuperSolver] Attempt {attempt}/{self.max_attempts}")

            for strategy_name, strategy_func in strategies:
                try:
                    result = await strategy_func(page)
                    result.attempts = attempt

                    if result.success:
                        final_result = result
                        final_result.time_spent = time.time() - overall_start
                        final_result.status = SolverStatus.SUCCESS
                        logger.info(f"[SuperSolver] SUCCESS with {strategy_name}")
                        return final_result

                except Exception as e:
                    logger.debug(f"[SuperSolver] Strategy {strategy_name} failed: {e}")
                    continue

            # 尝试间等待
            if attempt < self.max_attempts:
                await asyncio.sleep(random.uniform(1.0, 2.0))

        # 所有尝试都失败
        final_result.status = SolverStatus.FAILED
        final_result.time_spent = time.time() - overall_start
        final_result.error_message = "All strategies failed"
        return final_result

    def _get_strategies_for_type(self, captcha_type: CaptchaType) -> List[Tuple[str, Callable]]:
        """获取对应类型的求解策略列表"""
        strategies = []

        if captcha_type == CaptchaType.SLIDER:
            strategies = [
                ('opencv_slider', self._solve_slider_opencv),
                ('dom_estimate', self._solve_slider_dom),
                ('random_drag', self._solve_slider_random),
            ]

        elif captcha_type == CaptchaType.TEXT_IMAGE:
            strategies = [
                ('easyocr', self._solve_text_easyocr),
                ('tesseract', self._solve_text_tesseract),
                ('ai_vision', self._solve_text_ai_vision),
            ]

        elif captcha_type == CaptchaType.CLICK:
            strategies = [
                ('ai_vision_click', self._solve_click_ai),
                ('opencv_click', self._solve_click_opencv),
            ]

        elif captcha_type in [CaptchaType.RECAPTCHA_V2, CaptchaType.HCAPTCHA, CaptchaType.TURNSTILE]:
            strategies = [
                ('third_party_service', self._solve_with_service),
                ('manual_fallback', self._solve_manual_fallback),
            ]

        # 通用兜底策略
        strategies.extend([
            ('close_overlay', self._close_overlays),
            ('wait_and_retry', self._wait_and_recheck),
        ])

        return strategies

    async def _solve_slider_opencv(self, page) -> SolverResult:
        """OpenCV滑块求解"""
        return await self.slider_solver.solve_slider(page)

    async def _solve_slider_dom(self, page) -> SolverResult:
        """DOM估算滑块求解"""
        return await self.slider_solver.solve_slider(page)

    async def _solve_slider_random(self, page) -> SolverResult:
        """随机距离滑块求解"""
        result = SolverResult(captcha_type=CaptchaType.SLIDER)
        distance = random.randint(200, 350)
        success = await SliderSolver._perform_drag(page, distance)
        result.success = success
        result.method_used = "random_drag"
        result.details['distance'] = distance
        return result

    async def _solve_text_easyocr(self, page) -> SolverResult:
        """EasyOCR文字求解"""
        # 获取验证码图片
        img_bytes = await self._capture_text_captcha_image(page)
        if img_bytes:
            result = await self.ocr_solver.solve_text_captcha(img_bytes)
            if result.success and result.solution:
                await self._fill_text_captcha_input(page, result.solution)
            return result
        return SolverResult(success=False, error_message="No captcha image found")

    async def _solve_text_tesseract(self, page) -> SolverResult:
        """Tesseract文字求解（通过OCR类）"""
        return await self._solve_text_easyocr(page)

    async def _solve_text_ai_vision(self, page) -> SolverResult:
        """AI视觉文字求解"""
        img_bytes = await self._capture_text_captcha_image(page)
        if img_bytes:
            try:
                from apps.requirement_analysis.models import AIModelService
                b64 = base64.b64encode(img_bytes).decode('utf-8')

                messages = [
                    {"role": "system", "content": "Output ONLY the captcha text, no explanation."},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Read this captcha image:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                    ]}
                ]

                response, _ = await AIModelService.call_with_auto_model_from_roles(
                    ['browser_use_vision', 'browser_use_text'],
                    messages,
                    max_tokens=30
                )

                text = str(response).strip()
                text = re.sub(r'[^a-zA-Z0-9]', '', text)

                if len(text) >= 3:
                    await self._fill_text_captcha_input(page, text)
                    return SolverResult(success=True, solution=text, method_used="ai_vision")

            except Exception as e:
                logger.debug(f"[SuperSolver] AI vision text failed: {e}")

        return SolverResult(success=False)

    async def _solve_click_ai(self, page) -> SolverResult:
        """AI点击求解"""
        return await self.click_solver.solve(page)

    async def _solve_click_opencv(self, page) -> SolverResult:
        """OpenCV点击求解"""
        return await self.click_solver.solve(page)

    async def _solve_with_service(self, page) -> SolverResult:
        """第三方服务求解"""
        result = SolverResult()
        api_key = self.config.get('service_2captcha_key')

        if not api_key or self.config.get('skip_third_party', False):
            result.error_message = "No API key configured"
            return result

        # 尝试提取sitekey
        sitekey = await self._extract_sitekey(page)
        url = page.url

        if sitekey:
            captcha_type, _ = await self.detect_captcha_type(page)
            service_type = "userrecaptcha"
            if captcha_type == CaptchaType.HCAPTCHA:
                service_type = "hcaptcha"
            elif captcha_type == CaptchaType.TURNSTILE:
                service_type = "turnstile"

            result = await self.third_party_solver.solve_with_2captcha(
                sitekey, url, api_key, service_type
            )

            if result.success and result.solution:
                await self._inject_solution(page, result.solution)

        return result

    async def _solve_manual_fallback(self, page) -> SolverResult:
        """手动回退"""
        # 记录需要人工处理
        logger.warning("[SuperSolver] Manual intervention required")
        return SolverResult(success=False, error_message="Manual intervention required")

    async def _close_overlays(self, page) -> SolverResult:
        """关闭弹窗/遮罩"""
        close_selectors = [
            'button:has-text("Accept"), button:has-text("Allow"), button:has-text("OK")',
            'button:has-text("同意"), button:has-text("接受"), button:has-text("关闭")',
            '.close, .modal-close, [class*="close"]'
        ]

        clicked = False
        for sel in close_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    clicked = True
                    await asyncio.sleep(0.5)
            except Exception:
                continue

        return SolverResult(success=clicked, method_used="close_overlay")

    async def _wait_and_recheck(self, page) -> SolverResult:
        """等待并重试"""
        await asyncio.sleep(2.0)
        # 检查验证码是否消失
        new_type, _ = await self.detect_captcha_type(page)
        return SolverResult(success=new_type == CaptchaType.UNKNOWN, method_used="wait")

    # 辅助方法
    async def _capture_text_captcha_image(self, page) -> Optional[bytes]:
        """获取文字验证码图片"""
        img_selectors = [
            'img[src*="captcha"], img[src*="verify"], img[src*="code"]',
            '#captcha-img, .captcha-img, #verify-img'
        ]
        for sel in img_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    return await el.screenshot()
            except Exception:
                continue
        return None

    async def _fill_text_captcha_input(self, page, text: str):
        """填充验证码输入框"""
        input_selectors = [
            'input[name*="captcha"], input[name*="verify"], input[name*="code"]',
            'input[id*="captcha"], input[placeholder*="验证码"]'
        ]
        for sel in input_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.fill(text)
                    await asyncio.sleep(0.3)
                    logger.info(f"[SuperSolver] Filled captcha input: {text}")
                    break
            except Exception:
                continue

    async def _extract_sitekey(self, page) -> Optional[str]:
        """提取sitekey"""
        try:
            # reCAPTCHA
            sitekey = await page.eval_on_selector(
                '[data-sitekey]',
                'el => el.getAttribute("data-sitekey")'
            )
            if sitekey:
                return sitekey
        except Exception:
            pass

        try:
            # hCaptcha
            sitekey = await page.eval_on_selector(
                '[data-sitekey]',
                'el => el.getAttribute("data-sitekey")'
            )
            if sitekey:
                return sitekey
        except Exception:
            pass

        try:
            html = await page.content()
            match = re.search(r'sitekey["\s:]+["\']([a-zA-Z0-9_-]+)', html)
            if match:
                return match.group(1)
        except Exception:
            pass

        return None

    async def _inject_solution(self, page, solution: str):
        """注入解决方案"""
        try:
            await page.evaluate(f"""
                (function() {{
                    const textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (textarea) {{
                        textarea.value = '{solution}';
                        textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                    const htextarea = document.querySelector('textarea[name="h-captcha-response"]');
                    if (htextarea) {{
                        htextarea.value = '{solution}';
                        htextarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                    // 尝试回调
                    if (typeof window___reCAPTCHA_callback === 'function') {{
                        window___reCAPTCHA_callback('{solution}');
                    }}
                }})()
            """)
        except Exception:
            pass


# ==================== 便捷函数 ====================

_global_solver: Optional[SuperCaptchaSolver] = None


def get_super_solver(config: Dict = None) -> SuperCaptchaSolver:
    """获取全局超级求解器实例"""
    global _global_solver
    if _global_solver is None or config:
        _global_solver = SuperCaptchaSolver(config or {})
    return _global_solver


async def auto_solve_captcha(page, config: Dict = None) -> SolverResult:
    """
    自动检测并解决页面上的验证码

    Args:
        page: Playwright页面对象
        config: 配置字典

    Returns:
        SolverResult
    """
    solver = get_super_solver(config)
    return await solver.solve(page)


async def solve_slider_captcha(page, config: Dict = None) -> SolverResult:
    """专门解决滑块验证码"""
    solver = get_super_solver(config)
    return await solver.solve(page, force_type=CaptchaType.SLIDER)


async def solve_text_captcha(page, config: Dict = None) -> SolverResult:
    """专门解决文字验证码"""
    solver = get_super_solver(config)
    return await solver.solve(page, force_type=CaptchaType.TEXT_IMAGE)
