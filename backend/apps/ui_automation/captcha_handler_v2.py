"""
统一验证码处理中心
- 检测 + 自动求解 + 持续监控 + 失败兜底
- 集成 captcha_detector + captcha_super_solver + captcha_handler
- 支持：滑块、点选、文字、reCAPTCHA、hCaptcha、Turnstile
"""
import asyncio
import logging
import time
import json
import os
from typing import Dict, Optional, Any, List, Tuple

logger = logging.getLogger(__name__)


class CaptchaHandlerV2:
    """
    验证码处理 V2
    - 检测到验证码 → 自动尝试求解
    - 求解失败 → 保存完整证据，标记为"需人工接管"
    - 支持多种验证码类型
    """

    # 求解器优先级：先尝试自动，再人工接管
    SOLVER_TIMEOUT = 30  # 单个求解器最大尝试时间
    MAX_TOTAL_ATTEMPTS = 3  # 总尝试次数

    def __init__(self, page, artifact_dir: str = ""):
        self.page = page
        self.artifact_dir = artifact_dir
        self.detector = None
        self.super_solver = None
        self._load_components()

    def _load_components(self):
        """延迟加载组件，避免启动时依赖问题"""
        try:
            from .captcha_detector import CaptchaDetector, get_captcha_detector
            self.detector = get_captcha_detector()
        except Exception as e:
            logger.warning(f"加载验证码检测器失败: {e}")
            self.detector = None

        try:
            from .captcha_super_solver import (
                CaptchaType, SliderSolver, OCRSolver, ClickCaptchaSolver
            )
            self.super_solver = {
                'slider': SliderSolver,
                'text': OCRSolver,
                'click': ClickCaptchaSolver,
                'CaptchaType': CaptchaType,
            }
        except Exception as e:
            logger.warning(f"加载验证码求解器失败: {e}")
            self.super_solver = None

    async def detect(self) -> Optional[Dict[str, Any]]:
        """检测验证码"""
        if not self.detector:
            return None
        try:
            result = await self.detector.detect(self.page)
            return {
                'detected': result.detected,
                'captcha_type': result.captcha_type,
                'block_reason': result.block_reason,
                'blocking_elements': result.blocking_elements or [],
            }
        except Exception as e:
            logger.warning(f"验证码检测失败: {e}")
            return None

    async def detect_and_solve(self) -> Dict[str, Any]:
        """
        检测并自动求解验证码
        返回:
          - solved: 是否已解决
          - attempts: 尝试次数
          - method: 使用的方法
          - blocked: 是否仍然阻塞（需要人工）
          - evidence_path: 证据保存路径
        """
        result = {
            'solved': False,
            'attempts': 0,
            'method': '',
            'blocked': True,
            'captcha_type': '',
            'evidence_path': '',
            'elapsed': 0.0,
        }
        start_time = time.time()

        # 1. 检测
        detection = await self.detect()
        if not detection or not detection.get('detected'):
            result['blocked'] = False
            result['solved'] = True
            return result

        captcha_type = detection.get('captcha_type', 'unknown')
        result['captcha_type'] = captcha_type
        logger.info(f"检测到验证码: {captcha_type} - {detection.get('block_reason')}")

        # 2. 保存检测证据
        if self.artifact_dir:
            try:
                evidence_path = await self._save_captcha_evidence('detected', detection)
                result['evidence_path'] = evidence_path
            except Exception as e:
                logger.warning(f"保存验证码证据失败: {e}")

        # 3. 尝试自动求解
        for attempt in range(1, self.MAX_TOTAL_ATTEMPTS + 1):
            result['attempts'] = attempt
            try:
                solved = await asyncio.wait_for(
                    self._try_solve(captcha_type),
                    timeout=self.SOLVER_TIMEOUT
                )
                if solved:
                    # 4. 验证是否真的解决（再次检测）
                    await asyncio.sleep(1.5)
                    recheck = await self.detect()
                    if recheck and not recheck.get('detected'):
                        result['solved'] = True
                        result['blocked'] = False
                        result['method'] = f"auto_solver_attempt_{attempt}"
                        logger.info(f"验证码已自动解决 (尝试{attempt}次)")
                        break
                    else:
                        logger.warning(f"第{attempt}次求解后验证码仍存在，继续尝试...")
                else:
                    logger.warning(f"第{attempt}次求解失败")
            except asyncio.TimeoutError:
                logger.warning(f"第{attempt}次求解超时")
            except Exception as e:
                logger.warning(f"第{attempt}次求解异常: {e}")

        # 5. 仍未解决 → 保存失败证据
        if not result['solved'] and self.artifact_dir:
            try:
                evidence_path = await self._save_captcha_evidence('failed', detection)
                result['evidence_path'] = evidence_path
            except Exception as e:
                logger.warning(f"保存失败证据失败: {e}")

        result['elapsed'] = round(time.time() - start_time, 2)
        return result

    async def _try_solve(self, captcha_type: str) -> bool:
        """调用对应类型的求解器"""
        if not self.super_solver:
            return False

        try:
            if 'slider' in captcha_type or '滑块' in captcha_type:
                from .captcha_super_solver import SliderSolver
                solver_result = await SliderSolver.solve_slider(self.page)
                return solver_result.success if solver_result else False

            elif 'text' in captcha_type or '文字' in captcha_type or 'image' in captcha_type:
                # 文字/图片验证码
                from .captcha_super_solver import OCRSolver
                # 截取验证码图片
                img_bytes = await self._capture_captcha_image()
                if img_bytes:
                    solver_result = await OCRSolver.solve_text_captcha(img_bytes)
                    if solver_result.success:
                        # 填入验证码
                        return await self._fill_text_captcha(solver_result.solution or "")
                return False

            elif 'click' in captcha_type or '点选' in captcha_type:
                from .captcha_super_solver import ClickCaptchaSolver
                solver_result = await ClickCaptchaSolver.solve(self.page)
                return solver_result.success if solver_result else False

            else:
                # 未知类型，先尝试 reCAPTCHA/turnstile/hCaptcha
                from .captcha_super_solver import SliderSolver
                solver_result = await SliderSolver.solve_slider(self.page)
                return solver_result.success if solver_result else False
        except Exception as e:
            logger.warning(f"求解器调用失败: {e}")
            return False

    async def _capture_captcha_image(self) -> Optional[bytes]:
        """截取验证码图片"""
        try:
            # 尝试找到验证码图片元素
            selectors = [
                'img[src*="captcha"]', 'img[src*="verify"]', 'img[src*="code"]',
                '.captcha-img', '.verify-img', '#captcha_img', '#verify_img',
                'canvas[class*="captcha"]', 'canvas[class*="verify"]',
            ]
            for sel in selectors:
                el = await self.page.query_selector(sel)
                if el:
                    buf = await el.screenshot()
                    return buf
            return None
        except Exception:
            return None

    async def _fill_text_captcha(self, code: str) -> bool:
        """填入文字验证码"""
        try:
            input_selectors = [
                'input[name*="captcha"]', 'input[name*="verify"]',
                'input[name*="code"]', 'input[id*="captcha"]',
                'input[id*="verify"]', 'input[id*="code"]',
                'input.captcha-input', 'input.verify-input',
            ]
            for sel in input_selectors:
                el = await self.page.query_selector(sel)
                if el:
                    await el.fill(code)
                    return True
            return False
        except Exception as e:
            logger.warning(f"填入验证码失败: {e}")
            return False

    async def _save_captcha_evidence(self, stage: str, detection: Dict) -> str:
        """保存验证码相关证据"""
        if not self.artifact_dir:
            return ""

        captcha_dir = os.path.join(self.artifact_dir, 'captcha')
        os.makedirs(captcha_dir, exist_ok=True)

        ts = int(time.time() * 1000)
        # 截图
        screenshot_path = os.path.join(captcha_dir, f'captcha_{stage}_{ts}.png')
        try:
            await self.page.screenshot(path=screenshot_path, full_page=True)
        except Exception as e:
            logger.warning(f"验证码截图失败: {e}")

        # DOM
        dom_path = os.path.join(captcha_dir, f'captcha_{stage}_{ts}.html')
        try:
            html = await self.page.content()
            with open(dom_path, 'w', encoding='utf-8') as f:
                f.write(html)
        except Exception as e:
            logger.warning(f"保存DOM失败: {e}")

        # 元数据
        meta_path = os.path.join(captcha_dir, f'captcha_{stage}_{ts}.json')
        try:
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'stage': stage,
                    'detection': detection,
                    'timestamp': ts,
                    'url': self.page.url,
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存元数据失败: {e}")

        return captcha_dir


async def detect_and_handle_captcha(page, artifact_dir: str = "") -> Dict[str, Any]:
    """
    便捷函数：检测并处理验证码
    用法: result = await detect_and_handle_captcha(page, artifact_dir)
    """
    handler = CaptchaHandlerV2(page, artifact_dir)
    return await handler.detect_and_solve()
