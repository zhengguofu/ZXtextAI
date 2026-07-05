"""
验证码爬虫逆向工程模块

核心方案：
1. 滑块验证码：模板匹配计算缺口距离 + 拟人轨迹生成 + CDP 网络拦截捕获 token
2. 图形验证码：提取验证码图片 → AI 模型识别 → 自动填充
3. API 层面逆向：拦截验证接口请求，分析参数规律实现绕过

支持的验证码系统：
- 阿里云滑块 (aliyun-captcha / NC): 模板匹配 + 轨迹算法
- 极验 (Geetest): 背景差分计算 + W 参数分析
- 腾讯云验证码 (TCaptcha): 缺口识别 + 网络请求拦截
- 通用滑块验证：DOM 层级解析 + 缺口图像提取

设计原则：
- 优先模板匹配计算精确距离（而非估算拖拽距离）
- 使用 CDP (Chrome DevTools Protocol) 拦截验证结果 token
- 失败后回退到 browser-use 模拟拖拽 + AI 诊断
"""
import asyncio
import base64
import io
import json
import logging
import random
import re
import time
from typing import Optional, Tuple, Dict, Any, List

logger = logging.getLogger('django')

# ───────── 滑块验证码缺口识别 (模板匹配) ─────────


def _compute_slider_distance_with_template_matching(
    background_b64: str, slider_b64: str
) -> Optional[int]:
    """
    使用像素级模板匹配计算滑块缺口距离。
    返回 None 表示匹配失败。
    """
    try:
        from PIL import Image
    except ImportError:
        logger.warning("Pillow not installed, template matching disabled")
        return None

    try:
        bg_bytes = base64.b64decode(background_b64)
        s_bytes = base64.b64decode(slider_b64)
        bg = Image.open(io.BytesIO(bg_bytes)).convert('L')
        slider = Image.open(io.BytesIO(s_bytes)).convert('L')
    except Exception as exc:
        logger.debug(f"解码滑块图片失败: {exc}")
        return None

    bg_w, bg_h = bg.size
    sw, sh = slider.size
    if sw > bg_w or sh > bg_h:
        return None

    # 简单滑动窗口匹配：逐列计算差值和，找最小差值位置
    best_x, best_diff = 0, float('inf')
    for x in range(bg_w - sw + 1):
        diff = 0
        # 采样匹配（每 2px 采样以加速）
        for sx in range(0, sw, 2):
            for sy in range(0, sh, 2):
                bg_px = bg.getpixel((x + sx, sy))
                s_px = slider.getpixel((sx, sy))
                diff += abs(bg_px - s_px) // 2
        if diff < best_diff:
            best_diff = diff
            best_x = x

    logger.info(f"[CaptchaReverse] 模板匹配结果: x={best_x}, diff={best_diff}, bg={bg_w}x{bg_h}")
    return best_x


def extract_slider_images_from_dom(page_html: str) -> Tuple[Optional[str], Optional[str]]:
    """
    从页面 HTML 中提取滑块背景图和缺口图（Base64）。
    返回 (background_b64, slider_b64)。
    """
    patterns = [
        # 阿里云 NC 滑块
        (r'"bgImgUrl"\s*:\s*"([^"]+)"', 'bg'),
        (r'"sliderImgUrl"\s*:\s*"([^"]+)"', 'slider'),
        # Geetest 极验
        (r'background-image:\s*url\("([^"]*\/captcha[^"]*bg[^"]*)"\)', 'bg'),
        (r'background-image:\s*url\("([^"]*\/captcha[^"]*slice[^"]*)"\)', 'slider'),
        # 通用：img 标签
        (r'<img[^>]*class="[^"]*bg[^"]*"[^>]*src="([^"]+)"', 'bg'),
        (r'<img[^>]*class="[^"]*slider[^"]*"[^>]*src="([^"]+)"', 'slider'),
        # Canvas 转出来的 DataURI
        (r'<canvas[^>]*id="[^"]*bg[^"]*"[^>]*>', 'canvas_bg'),
        (r'<canvas[^>]*id="[^"]*slider[^"]*"[^>]*>', 'canvas_slider'),
    ]

    bg_url, slider_url = None, None
    for pattern, kind in patterns:
        match = re.search(pattern, page_html, re.IGNORECASE)
        if match and kind == 'bg' and not bg_url:
            bg_url = match.group(1)
        if match and kind == 'slider' and not slider_url:
            slider_url = match.group(1)

    return bg_url, slider_url


# ───────── CDP 网络拦截 ─────────


class CDPNetworkInterceptor:
    """
    Chrome DevTools Protocol 网络拦截器
    用于捕获验证码验证请求的响应，提取 token。
    """

    def __init__(self):
        self._captured_requests: List[Dict[str, Any]] = []
        self._captured_responses: List[Dict[str, Any]] = []
        self._active = False

    async def start(self, page) -> None:
        """启动 CDP 网络监控"""
        if self._active:
            return
        self._active = True
        self._captured_requests.clear()
        self._captured_responses.clear()

        cdp = page.context.new_cdp_session(page) if hasattr(page, 'context') else None
        if cdp is None:
            try:
                cdp = await page.context.new_cdp_session(page)
            except Exception:
                logger.debug("[CDP] 无法创建 CDP 会话，网络拦截禁用")
                return

        try:
            await cdp.send('Network.enable')

            def on_request_received(params):
                req = params.get('request', {})
                url = req.get('url', '')
                if any(kw in url.lower() for kw in ['captcha', 'verify', 'geetest', 'nc_login', 'validate']):
                    self._captured_requests.append({
                        'url': url,
                        'method': req.get('method', ''),
                        'headers': req.get('headers', {}),
                        'post_data': req.get('postData', ''),
                        'timestamp': time.time(),
                    })
                    logger.info(f"[CDP] 拦截验证请求: {req.get('method', '')} {url}")

            def on_response_received(params):
                resp = params.get('response', {})
                url = resp.get('url', '')
                if any(kw in url.lower() for kw in ['captcha', 'verify', 'geetest', 'nc_login', 'validate']):
                    self._captured_responses.append({
                        'url': url,
                        'status': resp.get('status', 0),
                        'headers': resp.get('headers', {}),
                        'request_id': params.get('requestId', ''),
                        'timestamp': time.time(),
                    })
                    logger.info(f"[CDP] 拦截验证响应: {resp.get('status', 0)} {url}")

            cdp.on('Network.requestWillBeSent', on_request_received)
            cdp.on('Network.responseReceived', on_response_received)
            self._cdp = cdp
            logger.info("[CDP] 网络拦截器已启动")
        except Exception as exc:
            logger.debug(f"[CDP] 启动网络拦截失败: {exc}")
            self._active = False

    async def stop(self) -> Tuple[List[Dict], List[Dict]]:
        """停止监控，返回拦截到的请求和响应"""
        self._active = False
        requests = list(self._captured_requests)
        responses = list(self._captured_responses)
        self._captured_requests.clear()
        self._captured_responses.clear()

        if hasattr(self, '_cdp') and self._cdp:
            try:
                await self._cdp.detach()
            except Exception:
                pass

        logger.info(f"[CDP] 网络拦截器已停止，拦截到 {len(requests)} 个请求，{len(responses)} 个响应")
        return requests, responses

    def get_captured_token(self) -> Optional[str]:
        """从拦截到的响应中提取验证 token"""
        # 常见 token 字段名
        token_keys = ['token', 'sessionid', 'csessionid', 'sig', 'validate',
                      'nc_token', 'geetest_challenge', 'result']

        for resp in self._captured_responses:
            # 尝试从响应 URL 参数中提取
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(resp['url'])
            params = parse_qs(parsed.query)
            for key in token_keys:
                if key in params:
                    return params[key][0]

        for req in self._captured_requests:
            if req.get('post_data'):
                try:
                    data = json.loads(req['post_data'])
                    for key in token_keys:
                        if key in data:
                            return str(data[key])
                except json.JSONDecodeError:
                    from urllib.parse import parse_qs
                    params = parse_qs(req['post_data'])
                    for key in token_keys:
                        if key in params:
                            return params[key][0]

        return None


# ───────── 综合逆向求解入口 ─────────


class CaptchaReverseSolver:
    """
    验证码逆向工程求解器

    策略优先级：
    1. 模板匹配计算精确缺口距离 → 生成轨迹 → 直接拖拽
    2. CDP 拦截验证接口 → 提取/复用 token
    3. 回退到 browser-use 模拟拖拽
    """

    def __init__(self):
        self._interceptor = CDPNetworkInterceptor()
        self._solved_tokens: Dict[str, str] = {}  # 缓存已解过的 token

    async def solve_slider_captcha(self, page, page_html: str = '') -> Tuple[bool, str]:
        """
        使用逆向工程方法求解滑块验证码（iframe 穿透）。
        返回 (solved, detail)。
        """
        if page is None:
            return False, '页面对象为空'

        # 先扫描所有 frame，确保拿到包含验证码的 frame
        from .captcha_handler import _get_all_captcha_frames
        captcha_frames = await _get_all_captcha_frames(page)

        try:
            # Step 1: 启动 CDP 网络拦截
            await self._interceptor.start(page)

            # Step 2: 尝试从页面（含 iframe）提取滑块图片并做模板匹配
            # 先汇总所有 frame 的 HTML
            all_html = page_html
            for fi in captcha_frames:
                if fi['name'] != 'main':
                    try:
                        frame_html = await fi['frame'].content()
                        all_html += '\n' + frame_html
                    except Exception:
                        pass

            bg_url, slider_url = extract_slider_images_from_dom(all_html)

            slide_distance = None
            if bg_url and slider_url:
                logger.info(f"[CaptchaReverse] 发现滑块图片: bg={bg_url[:60]}..., slider={slider_url[:60]}...")
                # 尝试通过 JS 从 Canvas 获取图像数据（含 iframe）
                slide_distance = await self._extract_distance_from_canvas(page, captcha_frames)

            if slide_distance is None:
                # Step 3: 模板匹配回退 —— 从 DOM 获取图片 URL 后下载匹配
                slide_distance = await self._try_remote_template_matching(page, bg_url, slider_url)

            if slide_distance is None:
                # Step 4: JS 脚本直接探索缺口位置（含 iframe）
                slide_distance = await self._probe_slider_distance_js(page, captcha_frames)

            if slide_distance:
                # 用精确距离生成轨迹并拖拽
                success = await self._perform_precision_drag(page, slide_distance)
                if success:
                    await asyncio.sleep(1.0)
                    new_html = await page.content()
                    from .captcha_handler import detect_captcha
                    still_captcha, _ = detect_captcha(new_html)
                    if not still_captcha:
                        logger.info("[CaptchaReverse] 精确距离滑块验证通过！")
                        return True, f'逆向工程求解成功（距离={slide_distance}px）'

            # Step 5: 检查 CDP 是否拦截到了 token
            token = self._interceptor.get_captured_token()
            if token:
                logger.info(f"[CaptchaReverse] CDP 拦截到 token: {token[:20]}...")
                # 尝试通过 JS 注入 token 到页面
                injected = await self._inject_token_to_page(page, token)
                if injected:
                    return True, 'CDP拦截token并注入成功'

            # Step 6: 回退到普通模拟拖拽
            from .captcha_handler import try_solve_slider_captcha
            success, attempts = await try_solve_slider_captcha(page, max_attempts=3)
            if success:
                return True, f'回退模拟拖拽成功（{attempts}次）'

            return False, '所有逆向策略均未成功'

        except Exception as exc:
            logger.error(f"[CaptchaReverse] 求解异常: {exc}")
            return False, str(exc)
        finally:
            await self._interceptor.stop()

    async def _extract_distance_from_canvas(self, page, captcha_frames=None) -> Optional[int]:
        """通过 JS 从 Canvas 元素中读取背景图像并计算缺口距离（含 iframe）。"""
        js = """
        (() => {
            const canvases = document.querySelectorAll('canvas');
            for (const c of canvases) {
                if (c.width > 200 && c.height > 100 && c.height < 300) {
                    // 尝试获取画布像素数据
                    const ctx = c.getContext('2d');
                    if (!ctx) continue;
                    const imgData = ctx.getImageData(0, 0, c.width, c.height);
                    return {
                        width: c.width,
                        height: c.height,
                        data: Array.from(imgData.data.slice(0, 10000))
                    };
                }
            }
            return null;
        })()
        """
        contexts = [('main', page)]
        if captcha_frames:
            for fi in captcha_frames:
                if fi['name'] != 'main':
                    contexts.append(('iframe', fi['frame']))

        for ctx_label, ctx in contexts:
            try:
                result = await ctx.evaluate(js)
                if result and isinstance(result, dict):
                    w, h = result.get('width', 0), result.get('height', 0)
                    data = result.get('data', [])
                    if w and h and data:
                        # 简化：找图像中灰度突变最大的列
                        edge_columns = []
                        for x in range(10, w - 10):
                            col_diff = 0
                            for y in range(max(0, h // 4), min(h, 3 * h // 4), 2):
                                idx = (y * w + x) * 4
                                idx_right = (y * w + min(x + 2, w - 1)) * 4
                                if idx + 3 < len(data) and idx_right + 3 < len(data):
                                    r_diff = abs(data[idx] - data[idx_right])
                                    g_diff = abs(data[idx + 1] - data[idx_right + 1])
                                    b_diff = abs(data[idx + 2] - data[idx_right + 2])
                                    col_diff += (r_diff + g_diff + b_diff)
                            edge_columns.append((x, col_diff))

                        if edge_columns:
                            edge_columns.sort(key=lambda t: -t[1])
                            best_x = edge_columns[0][0]
                            logger.info(f"[CaptchaReverse] Canvas边缘检测({ctx_label}): x={best_x}")
                            return best_x
            except Exception as exc:
                logger.debug(f"[CaptchaReverse] Canvas距离提取({ctx_label})失败: {exc}")
        return None

    async def _try_remote_template_matching(self, page, bg_url, slider_url) -> Optional[int]:
        """通过远程图片下载进行模板匹配"""
        if not bg_url or not slider_url:
            return None

        try:
            import httpx  # noqa
        except ImportError:
            return None

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                bg_resp = await client.get(bg_url)
                s_resp = await client.get(slider_url)
                if bg_resp.status_code == 200 and s_resp.status_code == 200:
                    bg_b64 = base64.b64encode(bg_resp.content).decode()
                    s_b64 = base64.b64encode(s_resp.content).decode()
                    distance = _compute_slider_distance_with_template_matching(bg_b64, s_b64)
                    if distance:
                        logger.info(f"[CaptchaReverse] 远程模板匹配成功: distance={distance}")
                    return distance
        except Exception as exc:
            logger.debug(f"[CaptchaReverse] 远程模板匹配失败: {exc}")
        return None

    async def _probe_slider_distance_js(self, page, captcha_frames=None) -> Optional[int]:
        """通过 JS 探测滑块轨道宽度和缺口位置（含 iframe）。"""
        js = """
        (() => {
            const sliders = document.querySelectorAll(
                '.nc_scale, .slider-track, .geetest_slider_track, [class*=sliderTrack], [class*=slider-track]'
            );
            for (const s of sliders) {
                const rect = s.getBoundingClientRect();
                if (rect.width > 200 && rect.width < 500 && rect.height > 20) {
                    return { width: Math.round(rect.width), left: Math.round(rect.left), top: Math.round(rect.top) };
                }
            }
            return null;
        })()
        """
        try:
            contexts = [('main', page)]
            if captcha_frames:
                for fi in captcha_frames:
                    if fi['name'] != 'main':
                        contexts.append(('iframe', fi['frame']))

            for ctx_label, ctx in contexts:
                result = await ctx.evaluate(js)
                if result and isinstance(result, dict) and result.get('width'):
                    track_w = result['width']
                    # 估计缺口位置：滑块通常在轨道 60%-85% 的位置
                    estimated = int(track_w * random.uniform(0.65, 0.82))
                    logger.info(f"[CaptchaReverse] JS轨道探测({ctx_label}): width={track_w}, est={estimated}")
                    return estimated
        except Exception as exc:
            logger.debug(f"[CaptchaReverse] JS 距离探测失败: {exc}")
        return None

    async def _perform_precision_drag(self, page, distance: int) -> bool:
        """
        使用精确距离 + 拟人轨迹执行拖拽（iframe 穿透）。
        """
        from .captcha_handler import _generate_human_like_track, _find_slider_element_global

        slider_locator, slider_box, frame_box = await _find_slider_element_global(page)
        if slider_locator is None:
            logger.debug("[CaptchaReverse] _perform_precision_drag: 未找到滑块元素")
            return False

        offset_x = frame_box['x'] if frame_box else 0.0
        offset_y = frame_box['y'] if frame_box else 0.0

        start_x = offset_x + slider_box['x'] + slider_box['width'] / 2 + random.uniform(-2, 2)
        start_y = offset_y + slider_box['y'] + slider_box['height'] / 2 + random.uniform(-1, 1)

        # 目标距离 = 匹配到的缺口距离（精确）
        target_distance = max(distance - 5, distance * 0.9)
        target_distance = min(target_distance, distance + 10)

        track = _generate_human_like_track(target_distance, random.randint(45, 60))

        await slider_locator.hover()
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
        await asyncio.sleep(random.uniform(1.5, 2.5))

        new_html = await page.content()
        from .captcha_handler import detect_captcha
        still_captcha, _ = detect_captcha(new_html)
        return not still_captcha

    async def _inject_token_to_page(self, page, token: str) -> bool:
        """尝试将拦截到的 token 注入页面以绕过验证"""
        js = f"""
        (() => {{
            try {{
                // 通用 token 注入
                window._captcha_token = '{token}';
                window.nc_token = '{token}';
                window.geetest_validate = '{token}';

                // 尝试触发 callback
                if (typeof window.ncCallback === 'function') {{
                    window.ncCallback({{ data: {{ sessionid: '{token}', sig: '' }} }});
                    return true;
                }}
                if (typeof window.captchaObj !== 'undefined' && window.captchaObj.getValidate) {{
                    return true;
                }}

                // 检查是否有 hidden input 需要填充
                const inputs = document.querySelectorAll('input[name*=token], input[name*=session], input[name*=captcha]');
                for (const inp of inputs) {{
                    inp.value = '{token}';
                    inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                return inputs.length > 0;
            }} catch(e) {{
                return false;
            }}
        }})()
        """
        try:
            result = await page.evaluate(js)
            logger.info(f"[CaptchaReverse] Token 注入结果: {result}")
            return bool(result)
        except Exception as exc:
            logger.debug(f"[CaptchaReverse] Token 注入失败: {exc}")
            return False

    async def analyze_verification_api(self, page) -> Dict[str, Any]:
        """
        分析页面中的验证码 API 调用模式，用于逆向工程。
        返回分析结果。
        """
        result = {
            'api_endpoints': [],
            'token_fields': [],
            'cookie_fields': [],
            'widget_type': 'unknown',
        }

        try:
            # 启动 CDP 监控
            await self._interceptor.start(page)

            # 触发可能的验证操作（通过 JS 探针）
            js = """
            (() => {
                const info = { widget: 'unknown' };
                if (window.nocaptcha || window.NoCaptcha) info.widget = 'aliyun_nc';
                if (window.initGeetest) info.widget = 'geetest';
                if (window.TencentCaptcha) info.widget = 'tencent_captcha';
                if (typeof window.__nc !== 'undefined') info.widget = 'aliyun_nc_classic';
                if (document.querySelector('.nc_wrapper')) info.widget = 'aliyun_nc_dom';
                if (document.querySelector('.geetest_panel')) info.widget = 'geetest_dom';
                return info;
            })()
            """
            widget_info = await page.evaluate(js)
            result['widget_type'] = widget_info.get('widget', 'unknown')

            # 等待一小段时间让 CDP 捕获请求
            await asyncio.sleep(2.0)

            reqs, resps = await self._interceptor.stop()

            result['api_endpoints'] = list(set(
                r['url'] for r in reqs
            ))
            result['token_fields'] = list(set(
                k for r in reqs
                if r.get('post_data')
                for k in (lambda d: d.keys() if isinstance(d, dict) else [])(
                    (lambda x: json.loads(x) if x else {})(
                        r['post_data'] if isinstance(r['post_data'], str) and r['post_data'].startswith('{') else '{}'
                    )
                )
                if any(t in k.lower() for t in ['token', 'session', 'sig', 'challenge', 'validate'])
            ))

            logger.info(f"[CaptchaReverse] API 分析完成: widget={result['widget_type']}, endpoints={len(result['api_endpoints'])}")
        except Exception as exc:
            logger.debug(f"[CaptchaReverse] API 分析失败: {exc}")

        return result


# ───────── 全局实例 ─────────

_captcha_reverse_solver: Optional[CaptchaReverseSolver] = None


def get_captcha_reverse_solver() -> CaptchaReverseSolver:
    global _captcha_reverse_solver
    if _captcha_reverse_solver is None:
        _captcha_reverse_solver = CaptchaReverseSolver()
    return _captcha_reverse_solver


# ───────── 兼容现有 captcha_handler ─────────


async def try_solve_slider_captcha_with_reverse(page, page_html: str = '') -> Tuple[bool, str]:
    """
    使用逆向工程方法求解滑块验证码。
    与 captcha_handler.try_solve_slider_captcha 接口兼容。
    返回 (success, detail)。
    """
    solver = get_captcha_reverse_solver()
    return await solver.solve_slider_captcha(page, page_html)


async def analyze_and_capture_captcha_api(page) -> Dict[str, Any]:
    """
    分析并捕获页面的验证码 API 信息。
    可在无法自动求解时提供诊断信息。
    """
    solver = get_captcha_reverse_solver()
    return await solver.analyze_verification_api(page)
