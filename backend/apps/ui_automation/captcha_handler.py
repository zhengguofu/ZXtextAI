"""
Captcha detection and automated solving for UI automation.

支持多级自动化验证码处理（含 iframe 穿透）：
1. 滑块验证码：iframe 穿透 + 模板匹配 + CDP 网络拦截 + 拟人轨迹（最多5次尝试）
2. 图形验证码：OCR 识别 + AI 视觉模型
3. Cookie/同意弹窗：自动关闭
4. 第三方验证码（reCAPTCHA/Cloudflare）：检测 + 诊断报告

分层求解策略（从上到下依次尝试）：
  Layer 1: 爬虫逆向（captcha_reverse）→ 模板匹配/CDP拦截
  Layer 2: Frame 穿透 → 在 iframe 内搜索滑块元素
  Layer 3: DOM 全局搜索（所有 frames）
  Layer 4: 拟人轨迹拖拽（5次加速曲线尝试）
  Layer 5: AI 诊断 + 人工接管提示
"""
import asyncio
import base64
import logging
import random
import re
from typing import Optional, Tuple, List

logger = logging.getLogger('django')

# ──────── 验证码关键词检测 ────────

CAPTCHA_KEYWORDS = [
    '验证码', 'captcha', 'verify', 'verification', '人机验证', '安全验证',
    '图形验证', '图片验证码', '滑块验证', '拖动滑块', '向右滑动', 'slide to verify',
    'drag the slider', 'slider captcha', 'geetest', 'aliyun-captcha', 'nc_iconfont',
    'recaptcha', 'hcaptcha', 'turnstile', 'cloudflare', '短信验证码', '手机验证码',
    '请输入验证码', '请输入短信', '获取验证码', '发送验证码', '请完成验证',
]

OVERLAY_KEYWORDS = [
    '同意', '接受', 'allow', 'accept', 'ok', '确定', '知道了', '关闭', 'close',
    '取消', 'dismiss', 'cookie', '隐私', 'privacy', 'gdpr', '继续访问', '不再提示',
]

LOGIN_FAILURE_SIGNALS = [
    '登录失败', 'login failed', '用户名或密码错误', '账号或密码错误',
    'invalid credentials', 'incorrect password', '账号不存在', 'user not found',
    '账号已锁定', 'account locked', '密码错误', 'wrong password', '验证失败',
    'auth failed', '请稍后再试', 'try again later', '验证码错误',
]

SLIDER_MAX_ATTEMPTS = 5  # 提升到5次，给iframe场景更多机会
SPEED_FAST = True  # 快速模式：减少延迟，加速自动化

# ──────── iframe 相关 — 验证码常见 iframe URL 模式 ────────

CAPTCHA_IFRAME_PATTERNS = [
    'nc_login', 'newlogin', 'checkcode', 'captcha', 'verify',
    'sec.m.taobao.com', 'cf.aliyun.com', 'geetest', 'nocaptcha',
    'auth_code', 'login_ifr', 'sso.taobao.com',
]


def _normalise_text(page_html: str) -> str:
    return re.sub(r'\s+', ' ', page_html or '').lower()


def _u(value: str) -> str:
    return value.encode('ascii').decode('unicode_escape')


def detect_captcha(page_html: str) -> Tuple[bool, str]:
    """检测页面是否包含验证码，返回 (has_captcha, captcha_type)。"""
    text = _normalise_text(page_html)
    if not text:
        return False, ''

    third_party_signals = ['recaptcha', 'hcaptcha', 'turnstile', 'cloudflare']
    slider_signals = [
        _u('\\u6ed1\\u5757'), _u('\\u62d6\\u52a8'), _u('\\u5411\\u53f3\\u6ed1\\u52a8'),
        _u('\\u62d6\\u52a8\\u6ed1\\u5757'), _u('\\u6ed1\\u5757\\u9a8c\\u8bc1'),
        'slide', 'slider', 'drag the slider', 'slide to verify', 'geetest', 'nc_iconfont', 'aliyun-captcha'
    ]
    click_signals = [
        _u('\\u6309\\u987a\\u5e8f\\u70b9\\u51fb'), _u('\\u8bf7\\u9009\\u62e9\\u56fe\\u4e2d'),
        _u('\\u70b9\\u9009'), 'click captcha'
    ]
    sms_signals = [
        _u('\\u77ed\\u4fe1\\u9a8c\\u8bc1\\u7801'), _u('\\u624b\\u673a\\u9a8c\\u8bc1\\u7801'),
        _u('\\u77ed\\u4fe1\\u9a8c\\u8bc1'), _u('\\u624b\\u673a\\u9a8c\\u8bc1'),
        _u('\\u52a8\\u6001\\u7801'), 'sms code', 'phone verification'
    ]
    text_signals = [
        _u('\\u56fe\\u5f62\\u9a8c\\u8bc1\\u7801'), _u('\\u56fe\\u7247\\u9a8c\\u8bc1\\u7801'),
        _u('\\u8bf7\\u8f93\\u5165\\u9a8c\\u8bc1\\u7801'), 'captcha image'
    ]
    general_signals = [
        _u('\\u9a8c\\u8bc1\\u7801'), _u('\\u4eba\\u673a\\u9a8c\\u8bc1'),
        _u('\\u5b89\\u5168\\u9a8c\\u8bc1'), _u('\\u8bf7\\u5b8c\\u6210\\u9a8c\\u8bc1'),
        'captcha', 'verification'
    ]

    if any(k in text for k in third_party_signals):
        return True, 'third_party_captcha'
    if any(k in text for k in slider_signals):
        return True, 'slider_captcha'
    if any(k in text for k in click_signals):
        return True, 'click_captcha'
    if any(k in text for k in text_signals):
        return True, 'text_captcha'
    if any(k in text for k in sms_signals):
        return True, 'sms_verify'
    if any(k in text for k in general_signals):
        return True, 'general_captcha'
    if any(k.lower() in text for k in CAPTCHA_KEYWORDS):
        return True, 'general_captcha'
    return False, ''


def detect_login_page(page_html: str) -> bool:
    text = _normalise_text(page_html)
    signals = ['password', '密码', '登录', 'login', 'sign in', '用户名', 'username', 'account']
    return sum(1 for signal in signals if signal.lower() in text) >= 2


def detect_overlay_or_popup(page_html: str) -> bool:
    text = _normalise_text(page_html)
    overlay_signals = ['modal', 'dialog', 'popup', 'overlay', '弹窗', '遮罩', '提示', '通知']
    has_overlay = any(signal in text for signal in overlay_signals)
    has_consent = any(signal.lower() in text for signal in OVERLAY_KEYWORDS)
    return has_overlay and has_consent


def detect_login_failure(page_html: str) -> Tuple[bool, str]:
    text = _normalise_text(page_html)
    for signal in LOGIN_FAILURE_SIGNALS:
        if signal.lower() in text:
            return True, signal
    return False, ''


def captcha_block_reason(captcha_type: str) -> str:
    reasons = {
        'text_captcha': '检测到图片/图形验证码，自动化已尝试OCR识别',
        'third_party_captcha': '检测到第三方人机验证（reCAPTCHA等），自动化无法绕过，建议人工处理',
        'slider_captcha': '检测到滑块验证码，自动化已尝试多次拟人拖动',
        'click_captcha': '检测到点选/图片选择验证码，自动化已尝试AI识别',
        'sms_verify': '检测到短信/手机验证码，需要人工输入动态验证码',
        'general_captcha': '检测到验证码/安全验证，自动化正在尝试自动处理',
    }
    return reasons.get(captcha_type, reasons['general_captcha'])


def get_captcha_handling_prompt(captcha_type: str) -> str:
    reason = captcha_block_reason(captcha_type)
    if captcha_type == 'slider_captcha':
        return (
            f"\n\n🔐 CAPTCHA DETECTED（{reason}）."
            "\n  处理策略：自动化引擎正在尝试拖动滑块验证。请等待结果。"
            "\n  如果多次拖动后滑块仍然存在，再考虑调用 mark_task_skipped。"
        )
    elif captcha_type == 'text_captcha':
        return (
            f"\n\n🔐 CAPTCHA DETECTED（{reason}）."
            "\n  处理策略：自动化引擎将尝试OCR识别验证码图片。请等待结果。"
            "\n  如果OCR识别失败，再调用 handle_verification_barrier 获取诊断建议。"
        )
    elif captcha_type in ('third_party_captcha', 'click_captcha'):
        return (
            f"\n\n🔐 CAPTCHA DETECTED（{reason}）."
            "\n  处理策略：先尝试关闭弹窗遮挡，如仍无法通过则调用 handle_verification_barrier 获取诊断建议。"
        )
    elif captcha_type == 'sms_verify':
        return (
            f"\n\n🔐 CAPTCHA DETECTED（{reason}）."
            "\n  处理策略：短信验证码无法自动完成，调用 mark_task_skipped 标记当前任务。"
        )
    else:
        return (
            f"\n\n🔐 CAPTCHA DETECTED（{reason}）."
            "\n  处理策略：自动化引擎正在尝试处理。如果持续被阻塞，调用 handle_verification_barrier 获取诊断建议。"
            "\n  请不要立即跳过——先等待自动化引擎的处理结果。"
        )


# ──────── 拟人轨迹生成 ────────

def _generate_human_like_track(total_distance: float, steps: int = 50) -> list:
    """生成拟人鼠标轨迹（加速→匀速→减速→微抖动）。"""
    track = []
    current = 0.0
    y_base = 0.0

    for i in range(steps):
        t = i / (steps - 1)  # 0.0 ~ 1.0

        if t < 0.3:
            progress = _ease_in_quad(t / 0.3)
        elif t < 0.7:
            progress = 0.3 + (t - 0.3) / 0.4 * 0.6
        else:
            progress = 0.9 + _ease_out_quad((t - 0.7) / 0.3) * 0.1

        x = progress * total_distance
        y = y_base + random.uniform(-1.5, 1.5) + (random.uniform(-2, 2) if i % 7 == 0 else 0)

        track.append((x, y))
        current = x

    if abs(current - total_distance) > 0.5:
        track[-1] = (total_distance, track[-1][1])

    return track


def _ease_in_quad(t: float) -> float:
    return t * t


def _ease_out_quad(t: float) -> float:
    return 1 - (1 - t) * (1 - t)


# ──────── iframe 穿透核心 ────────

async def _get_all_captcha_frames(page) -> List[dict]:
    """
    扫描页面所有 frame，找到包含验证码内容的 frame。
    返回 [{frame, frame_box, url, name}, ...]。
    主页面也作为一个条目返回（始终排在最后）。
    """
    frames_found = []

    try:
        all_frames = page.frames
    except Exception:
        all_frames = []

    for frame in all_frames:
        try:
            url = frame.url
            # 检查 frame URL 是否匹配已知验证码模式
            is_captcha_frame = any(p in url.lower() for p in CAPTCHA_IFRAME_PATTERNS)
            if not is_captcha_frame:
                continue

            # 获取 iframe 在主页面上的 bounding box（用于坐标偏移）
            frame_box = None
            try:
                frame_element = frame.frame_element()
                frame_box = await frame_element.bounding_box()
                if not frame_box and frame_element:
                    try:
                        box = await frame_element.bounding_box(timeout=1000)
                        frame_box = box
                    except Exception:
                        pass
            except Exception:
                pass

            frames_found.append({
                'frame': frame,
                'frame_box': frame_box,
                'url': url,
                'name': frame.name,
            })
            logger.info(f"[Captcha] 发现验证码 iframe: {url[:80]} box={frame_box}")

        except Exception:
            continue

    # 也搜索主页面的 frameLocator（跨域 iframe 也能匹配）
    for pattern in CAPTCHA_IFRAME_PATTERNS:
        try:
            fl = page.frame_locator(f'iframe[src*="{pattern}"]')
            # 尝试定位一下看是否存在
            try:
                await fl.locator('body').first.wait_for(state='attached', timeout=500)
                # 从 page.frames 找到对应的 frame
                for f in page.frames:
                    if pattern in f.url.lower():
                        if not any(x['frame'] is f for x in frames_found):
                            frame_element = f.frame_element() if hasattr(f, 'frame_element') else None
                            fb = None
                            if frame_element:
                                try:
                                    fb = await frame_element.bounding_box(timeout=1000)
                                except Exception:
                                    pass
                            frames_found.append({
                                'frame': f,
                                'frame_box': fb,
                                'url': f.url,
                                'name': f.name,
                            })
                            logger.info(f"[Captcha] frameLocator 发现验证码 iframe: {f.url[:80]}")
            except Exception:
                pass
        except Exception:
            continue

    # 主页面作为兜底
    frames_found.append({
        'frame': page,
        'frame_box': None,
        'url': getattr(page, 'url', ''),
        'name': 'main',
    })

    return frames_found


# ──────── 滑块元素查找（支持 frame 穿透） ────────

SLIDER_SELECTORS = [
    # 阿里云 NC 滑块
    '#nc_1_n1z', '.nc_iconfont.btn_slide', '.nc_wrapper .btn_slide',
    '[id*=nc_1]', '#nc_1__scale_text', '.btn_slide',
    # 极验 Geetest
    '.geetest_slider_button', '.geetest_slider_track .geetest_slider_button',
    '.geetest_btn', '.geetest_slider_btn',
    # 通用滑块
    '.slider-button', '.slider-btn', '.slider > div',
    '[class*=slider-btn]', '[class*=slide-btn]', '[class*=slideButton]',
    '[class*=slider] [role=slider]',
    '[aria-label*=滑块]', '[aria-label*=slider]', '[role=slider]',
    'span[class*=slider]', 'div[class*=slider]',
]

TRACK_SELECTORS = [
    '.nc_scale', '.slider-track', '.slider-rail', '.geetest_slider_track',
    '[class*=sliderTrack]', '[class*=slider-track]', '[class*=slideTrack]',
    '.slider-container', '.slide-container', '.nc-lang-cnt',
]


async def _find_slider_in_context(ctx) -> Tuple[object, Optional[dict]]:
    """
    在给定 context（page 或 frame）中搜索滑块元素。
    ctx 可以是 Page 或 Frame。
    返回 (locator, box) 或 (None, None)。
    """
    for selector in SLIDER_SELECTORS:
        try:
            locator = ctx.locator(selector).first
            count = await locator.count()
            if count == 0:
                continue
            box = await locator.bounding_box()
            if box and box['width'] > 10 and box['height'] > 10:
                return locator, box
        except Exception:
            continue
    return None, None


async def _find_track_in_context(ctx) -> Optional[float]:
    """在给定 context 中搜索滑块轨道，返回宽度。"""
    for selector in TRACK_SELECTORS:
        try:
            loc = ctx.locator(selector).first
            if await loc.count() > 0:
                box = await loc.bounding_box()
                if box:
                    return box['width']
        except Exception:
            continue
    return None


async def _find_slider_element_global(page) -> Tuple[object, Optional[dict], Optional[dict]]:
    """
    全局搜索滑块元素（穿透所有 frames）。
    返回 (locator, slider_box, frame_box)。
    - locator: Playwright Locator（可能位于 frame 中）
    - slider_box: 滑块在自身 context 中的 bounding box
    - frame_box: frame 在主页面中的 bounding box（用于坐标偏移），主页面则为 None
    """
    captcha_frames = await _get_all_captcha_frames(page)

    for ctx_info in captcha_frames:
        ctx = ctx_info['frame']
        locator, box = await _find_slider_in_context(ctx)
        if locator is not None:
            src = '主页面' if ctx_info['name'] == 'main' else f'iframe({ctx_info["name"] or ctx_info["url"][:40]})'
            logger.info(f"[Captcha] 在 {src} 中找到滑块元素: {box}")
            return locator, box, ctx_info['frame_box']

    return None, None, None


async def _find_track_width_global(page, slider_box) -> float:
    """全局搜索轨道宽度。"""
    captcha_frames = await _get_all_captcha_frames(page)

    for ctx_info in captcha_frames:
        ctx = ctx_info['frame']
        width = await _find_track_in_context(ctx)
        if width:
            return width

    # Fallback：根据滑块框估算
    return max(280, min(400, slider_box['width'] * 8))


# ──────── 执行一次拖拽（支持 iframe 坐标偏移） ────────

async def _perform_slider_drag(
    page,
    slider_locator,
    slider_box: dict,
    track_width: float,
    frame_box: Optional[dict] = None,
    attempt: int = 1,
) -> bool:
    """
    执行一次拟人滑块拖拽。
    如果 frame_box 非空，坐标会自动偏移到主页面坐标系。
    """
    # 计算滑块起点（相对于主页面）
    offset_x = frame_box['x'] if frame_box else 0.0
    offset_y = frame_box['y'] if frame_box else 0.0

    start_x = offset_x + slider_box['x'] + slider_box['width'] / 2
    start_y = offset_y + slider_box['y'] + slider_box['height'] / 2

    # 拖拽距离：先尝试匹配缺口，最后一次尝试全距离
    base_distance = track_width - slider_box['width']
    if attempt == 1:
        target_distance = base_distance - random.uniform(2, 8)
    elif attempt <= 3:
        target_distance = base_distance - random.uniform(0, 6)
    elif attempt == 4:
        target_distance = base_distance + random.uniform(-2, 5)
    else:
        target_distance = base_distance + random.uniform(2, 8)

    target_distance = max(track_width * 0.65, min(track_width * 1.02, target_distance))

    # 生成拟人轨迹
    steps_count = random.randint(45, 65)
    track = _generate_human_like_track(target_distance, steps_count)

    # 微量随机偏移
    start_x += random.uniform(-2, 2)
    start_y += random.uniform(-1, 1)

    # 执行拖拽（速度优化）
    try:
        await slider_locator.hover()
    except Exception:
        pass

    hover_delay = random.uniform(0.02, 0.08) if SPEED_FAST else random.uniform(0.05, 0.15)
    await asyncio.sleep(hover_delay)
    await page.mouse.move(start_x, start_y)

    move_delay = random.uniform(0.01, 0.05) if SPEED_FAST else random.uniform(0.03, 0.1)
    await asyncio.sleep(move_delay)

    await page.mouse.down()

    down_delay = random.uniform(0.02, 0.06) if SPEED_FAST else random.uniform(0.05, 0.12)
    await asyncio.sleep(down_delay)

    track_delay_range = (0.003, 0.012) if SPEED_FAST else (0.006, 0.022)
    for px, py in track:
        await page.mouse.move(start_x + px, start_y + py, steps=1)
        await asyncio.sleep(random.uniform(*track_delay_range))

    up_delay = random.uniform(0.04, 0.1) if SPEED_FAST else random.uniform(0.08, 0.2)
    await asyncio.sleep(up_delay)
    await page.mouse.up()

    verify_delay = random.uniform(0.8, 1.5) if SPEED_FAST else random.uniform(1.5, 2.5)
    await asyncio.sleep(verify_delay)

    # 检查结果（先检查主页面，再检查 frame）
    page_html = await page.content()
    has_captcha, captcha_type = detect_captcha(page_html)
    success = not has_captcha or captcha_type != 'slider_captcha'

    if success:
        logger.info(f'[Captcha] 滑块验证 PASSED on attempt #{attempt} (offset={frame_box is not None})')
    else:
        logger.info(f'[Captcha] 滑块验证 attempt #{attempt} failed, captcha still present')

    return success


# ──────── 主入口：多策略滑块求解 ────────

async def try_solve_slider_captcha(page, max_attempts: int = SLIDER_MAX_ATTEMPTS) -> Tuple[bool, int]:
    """
    多策略滑块验证码自动求解（iframe 穿透 + 逆向工程 + 拟人轨迹）。

    执行流程：
    1. 爬虫逆向工程（captcha_reverse）—— 模板匹配 / CDP 拦截
    2. Frame 穿透搜索滑块元素
    3. 按轨道宽度执行拟人拖拽（最多 max_attempts 次）
    4. 每次拖拽前重新定位滑块（因为 DOM 可能刷新）
    5. 尝试等待验证通过（notify 钩子、AJAX 回调）

    Returns (success, attempts_used)。
    """
    if page is None:
        return False, 0

    # ===== Layer 1: 爬虫逆向工程 =====
    try:
        from .captcha_reverse import try_solve_slider_captcha_with_reverse
        page_html = await page.content()
        reverse_success, detail = await try_solve_slider_captcha_with_reverse(page, page_html)
        if reverse_success:
            logger.info(f'[Captcha] 逆向工程求解成功: {detail}')
            return True, 1
        logger.info(f'[Captcha] 逆向工程未成功 ({detail})，进入 Layer 2')
    except Exception as rev_exc:
        logger.debug(f'[Captcha] 逆向工程不可用: {rev_exc}')

    # ===== Layer 2: Frame 穿透全局搜索 =====
    slider_locator, slider_box, frame_box = await _find_slider_element_global(page)
    if slider_locator is None:
        logger.warning('[Captcha] 全局搜索未找到滑块元素（包括 iframe），探测失败')
        return False, 0

    track_width = await _find_track_width_global(page, slider_box)
    frame_tag = 'iframe' if frame_box else 'main'
    logger.info(
        f'[Captcha] 滑块已定位: frame={frame_tag}, '
        f'box={slider_box["width"]:.0f}x{slider_box["height"]:.0f}, '
        f'track≈{track_width:.0f}px, max_attempts={max_attempts}'
    )

    # ===== Layer 3: 多次拟人拖拽 =====
    for attempt in range(1, max_attempts + 1):
        try:
            # 每次重新定位滑块（DOM 可能刷新或 frame 变化）
            slider_locator, slider_box, frame_box = await _find_slider_element_global(page)
            if slider_locator is None:
                logger.warning(f'[Captcha] attempt #{attempt}: 滑块消失（DOM 刷新？），终止')
                break

            success = await _perform_slider_drag(
                page, slider_locator, slider_box, track_width,
                frame_box=frame_box, attempt=attempt
            )
            if success:
                return True, attempt

            if attempt < max_attempts:
                delay = random.uniform(0.5, 1.5) if SPEED_FAST else random.uniform(1.0, 2.5)
                logger.info(f'[Captcha] attempt #{attempt} 失败，{delay:.1f}s 后重试...')
                await asyncio.sleep(delay)
                await _try_refresh_captcha_if_possible(page)

                # 每次等待后尝试点击滑块使其重新加载
                try:
                    await page.mouse.click(
                        frame_box['x'] + slider_box['x'] + 10 if frame_box else slider_box['x'] + 10,
                        frame_box['y'] + slider_box['y'] + slider_box['height'] / 2 if frame_box else slider_box['y'] + slider_box['height'] / 2,
                    )
                    await asyncio.sleep(0.3)
                except Exception:
                    pass

        except Exception as exc:
            logger.debug(f'[Captcha] attempt #{attempt} 异常: {exc}')
            if attempt < max_attempts:
                await asyncio.sleep(0.5)

    return False, max_attempts


# ──────── 辅助函数 ────────

async def _try_refresh_captcha_if_possible(page) -> bool:
    """尝试点击验证码刷新按钮。"""
    refresh_selectors = [
        '.nc_refresh', '.captcha-refresh', '.verification-refresh',
        '[class*=refresh]', '[aria-label*=刷新]', 'a[class*=refresh]',
        'span[class*=refresh]', '.reload-btn',
    ]
    for selector in refresh_selectors:
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0 and await locator.is_visible(timeout=500):
                await locator.click(timeout=1000)
                await asyncio.sleep(0.8)
                return True
        except Exception:
            continue

    # 也尝试在 iframe 中找刷新按钮
    try:
        frames_info = await _get_all_captcha_frames(page)
        for fi in frames_info:
            if fi['name'] == 'main':
                continue
            for selector in refresh_selectors:
                try:
                    loc = fi['frame'].locator(selector).first
                    if await loc.count() > 0:
                        await loc.click(timeout=1000)
                        await asyncio.sleep(0.8)
                        return True
                except Exception:
                    continue
    except Exception:
        pass

    return False


# ──────── 文字/图形验证码 OCR ────────

async def try_solve_text_captcha(page) -> Optional[str]:
    if page is None:
        return None

    try:
        img_selectors = [
            'img[src*=captcha]', 'img[src*=verify]', 'img[src*=code]',
            'img[id*=captcha]', 'img[class*=captcha]', 'img[class*=verify]',
            '#captcha-img', '.captcha-img', '.verify-img', '.code-img',
            'img[src*=验证码]', 'img[src*=checkcode]',
        ]

        # 扩展：搜索更多验证码图片类型
        img_selectors.extend([
            'img[src*=rand]', 'img[src*=auth]', 'img[src*=imgcode]',
            'img[src*=get_code]', 'img[onclick*=captcha]', 'img[onclick*=code]',
            '.auth-code-img img', '.captcha img', '.verify-img img',
        ])

        captcha_img = None
        for selector in img_selectors:
            try:
                loc = page.locator(selector).first
                if await loc.count() > 0 and await loc.is_visible(timeout=500):
                    captcha_img = loc
                    break
            except Exception:
                continue

        # 如果没找到img，尝试截图整个验证码容器
        if captcha_img is None:
            container_selectors = [
                '.captcha', '#captcha', '.verification', '.auth-code',
                '[class*=captcha]', '[class*=verify]', '[class*=auth-code]',
                '[class*=checkcode]',
            ]
            for cont_sel in container_selectors:
                try:
                    cont = page.locator(cont_sel).first
                    if await cont.count() > 0 and await cont.is_visible(timeout=500):
                        captcha_img = cont
                        break
                except Exception:
                    continue

        if captcha_img is None:
            logger.debug('No captcha image element found for OCR')
            return None

        screenshot_bytes = await captcha_img.screenshot(type='png')
        if not screenshot_bytes:
            return None

        screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        captcha_text = await _ocr_captcha_with_ai(screenshot_b64)

        # 如果AI OCR失败，尝试备用OCR（纯数字模式）
        if not captcha_text:
            captcha_text = await _ocr_captcha_digits_only(screenshot_b64)

        if captcha_text:
            input_selectors = [
                'input[name*=captcha]', 'input[name*=verify]', 'input[name*=code]',
                'input[id*=captcha]', 'input[class*=captcha]',
                'input[placeholder*=验证码]', 'input[placeholder*=captcha]',
                'input[name*=auth]', 'input[id*=auth_code]',
                'input[type=text][maxlength="4"]', 'input[type=text][maxlength="6"]',
            ]
            for input_sel in input_selectors:
                try:
                    input_loc = page.locator(input_sel).first
                    if await input_loc.count() > 0 and await input_loc.is_visible(timeout=500):
                        await input_loc.fill(captcha_text)
                        # 尝试自动提交（按回车或点击确认按钮）
                        await input_loc.press('Enter')
                        logger.info(f'Filled captcha input with: {captcha_text}')
                        return captcha_text
                except Exception:
                    continue
            logger.warning(f'Captcha text recognized ({captcha_text}) but no input field found')

        return captcha_text
    except Exception as exc:
        logger.warning(f'Text captcha OCR attempt failed: {exc}')
        return None


async def _ocr_captcha_with_ai(screenshot_b64: str) -> Optional[str]:
    try:
        from apps.requirement_analysis.models import AIModelService

        messages = [
            {
                'role': 'system',
                'content': (
                    'You are a CAPTCHA OCR tool. Look at the image and output ONLY the '
                    'alphanumeric characters/digits you see. No spaces, no punctuation, '
                    'no explanation. Output must be 4-6 characters only. '
                    'If you cannot read the text clearly, output "NONE".'
                )
            },
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'Read the CAPTCHA text from this image. Output ONLY the characters:'},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{screenshot_b64}'}},
                ]
            },
        ]

        response, config = await AIModelService.call_with_auto_model_from_roles(
            ['browser_use_vision', 'browser_use_text', 'ai_tester'],
            messages,
            max_tokens=20,
        )

        result = _extract_response_text(response)
        if result and result.upper() != 'NONE' and len(result) >= 3:
            logger.info(f'AI OCR recognized captcha: {result}')
            return result.strip()

        logger.debug(f'AI OCR could not recognize captcha: {result}')
        return None
    except Exception as exc:
        logger.warning(f'AI OCR captcha failed: {exc}')
        return None


async def _ocr_captcha_digits_only(screenshot_b64: str) -> Optional[str]:
    """备用OCR：纯数字模式，用于数字验证码（如4位/6位数字）。"""
    try:
        from apps.requirement_analysis.models import AIModelService

        messages = [
            {
                'role': 'system',
                'content': (
                    'You are a digit-only OCR tool. The image contains ONLY digits/numbers. '
                    'Output ONLY the digits seen in the image (e.g., "3847" or "629104"). '
                    'No spaces, no letters, no explanation. '
                    'If you cannot read clearly, output "NONE".'
                )
            },
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'Extract ONLY digits from this image (4-6 digits):'},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{screenshot_b64}'}},
                ]
            },
        ]

        response, config = await AIModelService.call_with_auto_model_from_roles(
            ['browser_use_vision', 'browser_use_text', 'ai_tester'],
            messages,
            max_tokens=10,
        )

        result = _extract_response_text(response)
        if result:
            # 只保留数字
            digits_only = ''.join(c for c in result if c.isdigit())
            if digits_only and len(digits_only) >= 3:
                logger.info(f'Digit-only OCR recognized: {digits_only}')
                return digits_only

        logger.debug(f'Digit-only OCR could not recognize: {result}')
        return None
    except Exception as exc:
        logger.warning(f'Digit-only OCR failed: {exc}')
        return None


def _extract_response_text(response) -> Optional[str]:
    if isinstance(response, dict):
        choices = response.get('choices') or []
        if choices:
            message = choices[0].get('message') or {}
            content = message.get('content')
            if content:
                return str(content).strip()
        if response.get('content'):
            return str(response['content']).strip()
    if isinstance(response, str):
        return response.strip()
    return None


# ──────── 点选验证码处理 ────────

async def try_solve_click_captcha(page) -> Tuple[bool, str]:
    """
    处理点选验证码（图片选择/点击验证）。
    策略：
    1. 截图验证码区域
    2. 使用 AI 视觉模型识别需要点击的目标
    3. 按顺序点击目标点
    """
    if page is None:
        return False, 'page is None'

    try:
        # 查找验证码提示文字和图片区域
        prompt_selectors = [
            'text=请依次点击', 'text=请点击', 'text=点击图中的',
            'text=请选择', '.click-captcha-prompt', '.captcha-title',
            '.verification-title', '[class*=click-captcha]',
        ]
        captcha_area_selectors = [
            '.click-captcha-image', '.captcha-img-area', '.verification-image',
            'img[class*=captcha]', 'img[class*=verify]',
            '.captcha-container img', '.verification-container img',
        ]

        # 先找提示文字
        prompt_text = ''
        for sel in prompt_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    prompt_text = await loc.text_content()
                    break
            except Exception:
                continue

        # 截取整个验证码区域
        captcha_screenshot = None
        for sel in captcha_area_selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible(timeout=500):
                    captcha_screenshot = await loc.screenshot(type='png')
                    break
            except Exception:
                continue

        if captcha_screenshot is None:
            # Fallback: 截取整个页面
            captcha_screenshot = await page.screenshot(type='png', full_page=False)

        if not captcha_screenshot:
            return False, '无法获取验证码截图'

        screenshot_b64 = base64.b64encode(captcha_screenshot).decode('utf-8')

        # 使用 AI 视觉模型识别点击目标
        click_targets = await _identify_click_targets(screenshot_b64, prompt_text)

        if not click_targets:
            return False, 'AI 未识别到点击目标'

        # 按顺序点击目标
        for target in click_targets:
            try:
                x = target.get('x', target.get('center_x', 0))
                y = target.get('y', target.get('center_y', 0))
                if x > 0 and y > 0:
                    await page.mouse.click(x, y)
                    await asyncio.sleep(0.3 if SPEED_FAST else 0.8)
            except Exception as click_err:
                logger.debug(f'Click captcha target click failed: {click_err}')

        # 检查是否通过
        await asyncio.sleep(0.5 if SPEED_FAST else 1.5)
        page_html = await page.content()
        has_captcha, captcha_type = detect_captcha(page_html)
        if not has_captcha:
            return True, f'点选验证通过（点击{len(click_targets)}个目标）'

        return False, f'点选验证未通过，已点击{len(click_targets)}个目标'

    except Exception as exc:
        logger.warning(f'Click captcha handling failed: {exc}')
        return False, str(exc)


async def _identify_click_targets(screenshot_b64: str, prompt_text: str) -> list:
    """使用 AI 视觉模型识别点选验证码中需要点击的目标坐标。"""
    try:
        from apps.requirement_analysis.models import AIModelService

        system_prompt = (
            "You are a click-captcha solver. Given a captcha image and text instruction, "
            "identify the objects that need to be clicked IN ORDER. "
            "Return ONLY a JSON array of {x, y} coordinates of the center of each target object. "
            "The coordinates should be in pixels relative to the image. "
            'Format: [{"x": 150, "y": 200}, {"x": 300, "y": 250}]'
        )

        user_text = "Find and return click coordinates for: " + (prompt_text or "the objects shown in order")
        messages = [
            {'role': 'system', 'content': system_prompt},
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': user_text},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{screenshot_b64}'}},
                ]
            },
        ]

        response, config = await AIModelService.call_with_auto_model_from_roles(
            ['browser_use_vision', 'browser_use_text', 'ai_tester'],
            messages,
            max_tokens=300,
        )

        result_text = _extract_response_text(response)
        if not result_text:
            return []

        # 从回复中提取 JSON
        import re as _re
        json_match = _re.search(r'\[.*?\]', result_text, _re.DOTALL)
        if json_match:
            targets = json.loads(json_match.group())
            if isinstance(targets, list):
                logger.info(f'AI identified {len(targets)} click targets for captcha')
                return targets

        return []

    except Exception as exc:
        logger.warning(f'AI click target identification failed: {exc}')
        return []


# ──────── CaptchaHandler 封装类 ────────

class CaptchaHandler:
    """验证码处理工具类（供自动化执行器使用）。"""

    @staticmethod
    def should_pause_execution(page_html: str) -> Tuple[bool, str]:
        has_captcha, captcha_type = detect_captcha(page_html)
        if not has_captcha:
            return False, ''
        if captcha_type in {'third_party_captcha', 'sms_verify'}:
            return True, captcha_block_reason(captcha_type)
        return False, ''

    @staticmethod
    async def try_solve_slider_captcha(page) -> bool:
        success, attempts = await try_solve_slider_captcha(page, max_attempts=SLIDER_MAX_ATTEMPTS)
        if success:
            logger.info(f'Slider verification passed after {attempts} attempt(s)')
        else:
            logger.info(f'Slider verification failed after {attempts} attempts')
        return success

    @staticmethod
    async def try_solve_text_captcha(page) -> bool:
        result = await try_solve_text_captcha(page)
        return result is not None

    @staticmethod
    async def try_solve_click_captcha(page) -> Tuple[bool, str]:
        return await try_solve_click_captcha(page)

    @staticmethod
    async def auto_handle_captcha(page, captcha_type: str) -> Tuple[bool, str]:
        """主入口：自动处理各类验证码（快速模式）。"""
        if captcha_type == 'slider_captcha':
            success, attempts = await try_solve_slider_captcha(page, max_attempts=SLIDER_MAX_ATTEMPTS)
            if success:
                return True, f'滑块验证自动通过（第{attempts}次尝试）'
            else:
                try:
                    frames_info = await _get_all_captcha_frames(page)
                    has_iframe = any(fi['name'] != 'main' for fi in frames_info)
                    if has_iframe:
                        return False, f'滑块验证失败（已尝试{attempts}次，验证码在iframe内），请检查frame穿透'
                except Exception:
                    pass
                return False, f'滑块验证失败（已尝试{attempts}次），需要人工接管'

        elif captcha_type == 'text_captcha':
            result = await try_solve_text_captcha(page)
            if result:
                return True, f'图形验证码OCR识别成功: {result}'
            else:
                return False, '图形验证码OCR识别失败，可能需要人工输入'

        elif captcha_type == 'click_captcha':
            success, detail = await try_solve_click_captcha(page)
            if success:
                return True, detail
            return False, f'点选验证码处理失败: {detail}'

        elif captcha_type in ('general_captcha',):
            slider_success, _ = await try_solve_slider_captcha(page, max_attempts=2)
            if slider_success:
                return True, '通用验证码经滑块方式自动通过'
            text_result = await try_solve_text_captcha(page)
            if text_result:
                return True, f'通用验证码经OCR识别通过: {text_result}'
            click_success, click_detail = await try_solve_click_captcha(page)
            if click_success:
                return True, f'通用验证码经点选方式通过: {click_detail}'
            return False, '通用验证码自动处理失败，请检查是否为第三方验证'

        elif captcha_type in ('click_captcha',):
            return False, '点选验证码暂不支持自动解决，需要人工完成'

        elif captcha_type == 'sms_verify':
            return False, '短信验证码无法自动完成，需要人工输入'

        elif captcha_type == 'third_party_captcha':
            return False, '第三方人机验证（reCAPTCHA/Cloudflare等）无法自动绕过'

        return False, f'未知验证码类型: {captcha_type}'

    @staticmethod
    async def dismiss_common_overlays(page) -> bool:
        selectors = [
            'button:has-text("Accept")', 'button:has-text("Allow")', 'button:has-text("OK")',
            'button:has-text("I agree")', 'button:has-text("Continue")',
            '.cookie button', '.privacy button', '[class*=modal] button', '[class*=dialog] button',
        ]
        text_buttons = [
            ''.join(chr(x) for x in [0x540c, 0x610f]),
            ''.join(chr(x) for x in [0x5141, 0x8bb8]),
            ''.join(chr(x) for x in [0x63a5, 0x53d7]),
            ''.join(chr(x) for x in [0x786e, 0x5b9a]),
            ''.join(chr(x) for x in [0x77e5, 0x9053, 0x4e86]),
        ]
        selectors.extend([f'button:has-text("{label}")' for label in text_buttons])
        for selector in selectors:
            try:
                locator = page.locator(selector).first()
                if await locator.count() == 0:
                    continue
                if not await locator.is_visible(timeout=800):
                    continue
                await locator.click(timeout=1500)
                await asyncio.sleep(0.5)
                return True
            except Exception as exc:
                logger.debug('Overlay dismiss attempt failed for %s: %s', selector, exc)
        return False

    @staticmethod
    def try_solve_slider_captcha_sync(page) -> bool:
        """同步版 Playwright 滑块求解（iframe 穿透）。"""
        slider_selectors = [
            '#nc_1_n1z', '.nc_iconfont.btn_slide', '.nc_wrapper .btn_slide',
            '.geetest_slider_button', '.geetest_btn',
            '.slider-button', '.slider-btn', '[class*=slider-btn]', '[class*=slide-btn]',
            '[aria-label*=滑块]', '[aria-label*=slider]', '[role=slider]',
        ]

        # 先尝试主页面
        for attempt in range(1, SLIDER_MAX_ATTEMPTS + 1):
            # 在每个 frame 中搜索
            for selector in slider_selectors:
                # 主页
                try:
                    locator = page.locator(selector).first
                    if locator.count() > 0:
                        box = locator.bounding_box()
                        if box:
                            return _do_sync_drag(page, locator, box, None, attempt)
                except Exception:
                    pass

                # 所有子 frame
                for frame in page.frames:
                    if frame is page:
                        continue
                    try:
                        locator = frame.locator(selector).first
                        if locator.count() > 0:
                            box = locator.bounding_box()
                            if box:
                                # 计算 frame 偏移
                                try:
                                    fe = frame.frame_element()
                                    fb = fe.bounding_box() if fe else None
                                except Exception:
                                    fb = None
                                return _do_sync_drag(page, locator, box, fb, attempt)
                    except Exception:
                        continue

            if attempt < SLIDER_MAX_ATTEMPTS:
                page.wait_for_timeout(1000)

        return False

    @staticmethod
    def get_timeout_config(fast_mode: bool = True) -> dict:
        if fast_mode:
            return {
                'page_load_timeout': 20,
                'action_timeout': 30,
                'llm_timeout': 60,
                'step_timeout': 90,
                'total_timeout': 1200,
                'max_retries': 1,
                'retry_delay': 1,
            }
        return {
            'page_load_timeout': 30,
            'action_timeout': 60,
            'llm_timeout': 90,
            'step_timeout': 120,
            'total_timeout': 1800,
            'max_retries': 2,
            'retry_delay': 2,
        }


def _do_sync_drag(page, locator, box, frame_box, attempt: int) -> bool:
    """同步拖拽辅助函数。"""
    offset_x = frame_box['x'] if frame_box else 0.0
    offset_y = frame_box['y'] if frame_box else 0.0

    start_x = offset_x + box['x'] + box['width'] / 2 + random.uniform(-1, 1)
    start_y = offset_y + box['y'] + box['height'] / 2 + random.uniform(-1, 1)
    distance = max(240, min(380, box['width'] * 7))

    track = _generate_human_like_track(distance, random.randint(40, 60))
    locator.hover()
    page.wait_for_timeout(50)
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    for px, py in track:
        page.mouse.move(start_x + px, start_y + py, steps=1)
        page.wait_for_timeout(random.randint(8, 25))
    page.wait_for_timeout(random.randint(80, 200))
    page.mouse.up()
    page.wait_for_timeout(random.randint(1500, 2500))

    has_captcha, captcha_type = detect_captcha(page.content())
    if not has_captcha or captcha_type != 'slider_captcha':
        logger.info(f'Slider captcha solved on sync attempt #{attempt}')
        return True
    return False
