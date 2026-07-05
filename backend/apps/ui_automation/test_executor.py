"""
测试执行器（全异步）
负责整合所有测试能力，执行完整的测试流程：
- 浏览器管理（启动/上下文/页面/清理）
- 全程录屏（Playwright 官方 record_video_dir）
- trace 录制（context.tracing）
- 步骤执行（StepExecutor）
- 验证码/风控检测（CaptchaDetector）
- 失败证据收集
- 报告生成（HTML + JSON）
"""
import os
import time
import json
import logging
import asyncio
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable

from .step_executor import StepExecutor, StepResult
from .artifact_manager import ArtifactManager, create_new_run
from .captcha_detector import CaptchaDetector, get_captcha_detector
from .captcha_handler_v2 import CaptchaHandlerV2, detect_and_handle_captcha

logger = logging.getLogger(__name__)


class TestExecutionResult:
    """测试执行结果"""

    def __init__(self):
        self.execution_id: str = ""
        self.start_time: float = 0
        self.end_time: float = 0
        self.duration: float = 0
        self.case_name: str = ""
        self.status: str = "pending"  # pending, running, passed, failed, blocked
        self.total_steps: int = 0
        self.passed_steps: int = 0
        self.failed_steps: int = 0
        self.blocked_steps: int = 0
        self.video_path: str = ""
        self.report_path: str = ""
        self.trace_path: str = ""
        self.har_path: str = ""
        self.artifact_dir: str = ""
        self.steps: List[StepResult] = []
        self.error: Optional[str] = None
        self.captcha_blocked: bool = False
        self.block_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'execution_id': self.execution_id,
            'start_time': datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else "",
            'end_time': datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else "",
            'duration': round(self.duration, 3),
            'case_name': self.case_name,
            'status': self.status,
            'total_steps': self.total_steps,
            'passed_steps': self.passed_steps,
            'failed_steps': self.failed_steps,
            'blocked_steps': self.blocked_steps,
            'pass_rate': round(self.passed_steps / self.total_steps * 100, 2) if self.total_steps > 0 else 0,
            'video_path': self.video_path,
            'report_path': self.report_path,
            'trace_path': self.trace_path,
            'har_path': self.har_path,
            'artifact_dir': self.artifact_dir,
            'steps': [step.to_dict() for step in self.steps],
            'error': self.error,
            'captcha_blocked': self.captcha_blocked,
            'block_reason': self.block_reason,
        }


class TestExecutor:
    """
    测试执行器（异步）
    整合浏览器管理、步骤执行、录屏、trace、HAR、验证码检测、证据收集、报告生成
    """

    def __init__(self, case_name: str = "", execution_id: Optional[str] = None):
        self.case_name = case_name
        self.execution_id = execution_id or self._generate_execution_id()
        self.artifact_manager: Optional[ArtifactManager] = None
        self.step_executor: Optional[StepExecutor] = None
        self.captcha_detector: CaptchaDetector = get_captcha_detector()
        self.result: TestExecutionResult = TestExecutionResult()
        self.result.execution_id = self.execution_id
        self.result.case_name = case_name

        # Playwright相关
        self._playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._user_data_dir = None
        self._video_enabled = True
        self._trace_enabled = True
        self._har_enabled = True
        self._har_path = ""

    def _generate_execution_id(self) -> str:
        """生成执行ID"""
        timestamp = int(time.time())
        import uuid
        uuid_short = str(uuid.uuid4())[:8]
        return f"{timestamp}_{uuid_short}"

    def enable_video(self, enabled: bool = True):
        self._video_enabled = enabled

    def enable_trace(self, enabled: bool = True):
        self._trace_enabled = enabled

    def enable_har(self, enabled: bool = True):
        self._har_enabled = enabled

    async def setup(self, browser_type: str = "chromium", headless: bool = False) -> bool:
        """
        初始化测试环境

        Args:
            browser_type: chromium, firefox, webkit
            headless: 是否无头模式

        Returns:
            是否成功
        """
        try:
            # 创建产物目录
            self.artifact_manager = create_new_run(self.execution_id)
            self.result.artifact_dir = self.artifact_manager.get_run_dir()
            logger.info(f"测试产物目录: {self.result.artifact_dir}")

            video_dir = os.path.join(self.result.artifact_dir, 'video')
            os.makedirs(video_dir, exist_ok=True)

            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()

            # 浏览器启动参数（规避 Windows 受限沙箱写 Recent/JumpList 等敏感目录）
            launch_args = [
                '--disable-gpu',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-features=Translate',
                '--no-first-run',
                '--no-default-browser-check',
            ]
            browser_launch_options = {
                'headless': headless,
                'args': launch_args,
            }

            if browser_type == 'chromium':
                self.browser = await self._playwright.chromium.launch(**browser_launch_options)
            elif browser_type == 'firefox':
                self.browser = await self._playwright.firefox.launch(headless=headless)
            elif browser_type == 'webkit':
                self.browser = await self._playwright.webkit.launch(headless=headless)
            else:
                raise ValueError(f"不支持的浏览器类型: {browser_type}")

            # 创建上下文（含录屏配置）
            context_options: Dict[str, Any] = {
                'viewport': {'width': 1440, 'height': 900},
                'ignore_https_errors': True,
            }
            if self._video_enabled:
                context_options['record_video_dir'] = video_dir
                context_options['record_video_size'] = {'width': 1440, 'height': 900}

            # HAR 录制（需在 new_context 时配置 record_har_path）
            if self._har_enabled:
                self._har_path = os.path.join(self.result.artifact_dir, 'har', f"network_{self.execution_id}.har")
                os.makedirs(os.path.dirname(self._har_path), exist_ok=True)
                context_options['record_har_path'] = self._har_path
                context_options['record_har_mode'] = 'full'

            self.context = await self.browser.new_context(**context_options)

            # 创建页面
            self.page = await self.context.new_page()
            self.page.set_default_timeout(30000)

            # 初始化步骤执行器
            self.step_executor = StepExecutor(
                page=self.page,
                output_dir=self.result.artifact_dir,
                case_name=self.case_name,
                execution_id=self.execution_id,
            )
            if self._har_enabled:
                self.step_executor.enable_har()
            if self._trace_enabled:
                self.step_executor.enable_trace()

            logger.info("测试环境初始化完成")
            return True

        except Exception as e:
            logger.error(f"测试环境初始化失败: {e}", exc_info=True)
            self.result.error = str(e)
            self.result.status = "failed"
            return False

    async def execute(self, test_func: Callable) -> TestExecutionResult:
        """
        执行测试用例

        Args:
            test_func: 异步测试函数，接收 StepExecutor 作为唯一参数

        Returns:
            TestExecutionResult
        """
        self.result.start_time = time.time()
        self.result.status = "running"

        try:
            # 启动 trace
            if self._trace_enabled and self.context:
                try:
                    await self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
                except Exception as e:
                    logger.warning(f"启动trace失败: {e}")

            # 执行测试函数
            await test_func(self.step_executor)

            # 收集步骤结果
            summary = self.step_executor.get_summary()
            self.result.total_steps = summary['total_steps']
            self.result.passed_steps = summary['passed']
            self.result.failed_steps = summary['failed']
            self.result.blocked_steps = summary['blocked']
            self.result.steps = self.step_executor.steps

            # 验证码检测（执行完后检查最终页面）
            try:
                await self.check_captcha()
            except Exception as e:
                logger.warning(f"验证码检测失败: {e}")

            # 判断整体状态
            if self.result.captcha_blocked:
                self.result.status = "blocked"
            elif self.result.failed_steps > 0:
                self.result.status = "failed"
            elif self.result.blocked_steps > 0:
                self.result.status = "blocked"
            else:
                self.result.status = "passed"

        except Exception as e:
            logger.error(f"测试执行异常: {e}", exc_info=True)
            self.result.error = str(e)
            self.result.status = "failed"

            # 收集失败证据
            if self.step_executor:
                try:
                    await self.step_executor.capture_full_page_screenshot("test_failed")
                    await self.step_executor.save_dom("test_failed")
                    self.step_executor.save_console_logs("test_failed")
                except Exception as ev_err:
                    logger.warning(f"收集失败证据失败: {ev_err}")
                # 同步最新步骤数据
                summary = self.step_executor.get_summary()
                self.result.total_steps = summary['total_steps']
                self.result.passed_steps = summary['passed']
                self.result.failed_steps = summary['failed']
                self.result.steps = self.step_executor.steps

        finally:
            # 停止 trace
            if self._trace_enabled and self.context:
                trace_path = os.path.join(self.result.artifact_dir, 'trace', f"trace_{self.execution_id}.zip")
                os.makedirs(os.path.dirname(trace_path), exist_ok=True)
                try:
                    await self.context.tracing.stop(path=trace_path)
                    self.result.trace_path = trace_path
                    logger.info(f"Trace已保存: {trace_path}")
                except Exception as e:
                    logger.warning(f"保存trace失败: {e}")

            # 导出步骤数据
            if self.step_executor:
                self.step_executor.export_steps_json()

            # 记录结束时间
            self.result.end_time = time.time()
            self.result.duration = self.result.end_time - self.result.start_time

        return self.result

    async def _generate_report(self) -> str:
        """生成测试报告"""
        try:
            from .reports import TestReportGenerator
            # 关联 step_executor 供报告生成讲解文字使用
            self.result.step_executor = self.step_executor
            report_generator = TestReportGenerator(self.result)
            return await report_generator.generate()
        except Exception as e:
            logger.error(f"生成报告失败: {e}", exc_info=True)
            return ""

    async def cleanup(self) -> None:
        """
        清理测试环境
        注意：视频文件只有在 page/context 关闭后才会最终落盘，
        因此必须在关闭前先拿到 video 对象，再在关闭后读取路径。
        """
        video_obj = None
        try:
            if self.page and self._video_enabled:
                try:
                    video_obj = self.page.video
                except Exception:
                    video_obj = None

            if self.page:
                await self.page.close()

            # 关闭 context 会触发 HAR 落盘
            if self.context:
                await self.context.close()

            # 关闭后获取视频真实路径
            if video_obj is not None:
                try:
                    self.result.video_path = await video_obj.path()
                    logger.info(f"视频已保存: {self.result.video_path}")
                except Exception as e:
                    logger.warning(f"获取视频路径失败: {e}")

            # HAR 路径
            if self._har_enabled and self._har_path and os.path.exists(self._har_path):
                self.result.har_path = self._har_path
                logger.info(f"HAR已保存: {self._har_path}")

            if self.browser:
                await self.browser.close()

            if self._playwright:
                await self._playwright.stop()

            logger.info("测试环境已清理")
        except Exception as e:
            logger.warning(f"清理测试环境失败: {e}")

    async def run(self, test_func: Callable, browser_type: str = "chromium", headless: bool = False) -> TestExecutionResult:
        """
        完整执行测试流程：setup -> execute -> cleanup -> 生成报告
        """
        if not await self.setup(browser_type, headless):
            # setup 失败也尽量生成报告
            self.result.report_path = await self._generate_report()
            return self.result

        try:
            await self.execute(test_func)
        finally:
            # 先清理（拿到视频/HAR路径），再生成报告
            await self.cleanup()
            self.result.report_path = await self._generate_report()
            logger.info(f"测试执行完成 - 状态: {self.result.status}, 耗时: {self.result.duration:.2f}s")

        return self.result

    async def check_captcha(self) -> bool:
        """
        检查并尝试自动解决验证码/风控阻塞
        使用 captcha_handler_v2 的 detect_and_solve 能力
        """
        if not self.page:
            return False

        try:
            artifact_dir = self.result.artifact_dir if hasattr(self.result, 'artifact_dir') else ''
            handler = CaptchaHandlerV2(self.page, artifact_dir)
            result = await handler.detect_and_solve()

            if result.get('solved'):
                # 已自动解决
                self.result.captcha_blocked = False
                self.result.block_reason = ''
                logger.info(f"验证码已自动解决 (尝试{result.get('attempts', 0)}次, 耗时{result.get('elapsed', 0)}s)")
                return False

            if result.get('blocked'):
                # 仍然阻塞，标记需要人工
                self.result.captcha_blocked = True
                self.result.block_reason = f"检测到{result.get('captcha_type', 'unknown')}验证码，自动求解失败（已尝试{result.get('attempts', 0)}次）"
                self.result.evidence = self.result.evidence or {}
                self.result.evidence['captcha'] = result.get('evidence_path', '')
                logger.error(f"验证码/风控阻塞: {self.result.block_reason}")
                return True

            return False
        except Exception as e:
            logger.warning(f"验证码检测处理失败: {e}")
            # 退回到简单检测
            try:
                result = await self.captcha_detector.detect(self.page)
                if result.detected:
                    self.result.captcha_blocked = True
                    self.result.block_reason = result.block_reason
                    return True
            except Exception:
                pass
            return False


# ========== 包装函数 ==========

async def run_test_async(
    case_name: str,
    test_func: Callable,
    browser_type: str = "chromium",
    headless: bool = False,
    execution_id: Optional[str] = None,
    resume_from_step: int = 0,
) -> TestExecutionResult:
    """
    异步执行测试

    Args:
        case_name: 测试用例名称
        test_func: 异步测试函数（接收 StepExecutor）。允许为 None（仅初始化环境，主要用于占位/续跑场景）
        browser_type: 浏览器类型
        headless: 是否无头模式
        execution_id: 执行ID（用于产物目录与续跑）
        resume_from_step: 续跑起始步骤索引（保留参数，供测试函数内部判断）

    Returns:
        TestExecutionResult
    """
    executor = TestExecutor(case_name=case_name, execution_id=execution_id)

    if test_func is None:
        # 没有可执行的测试函数时，返回一个明确的失败结果，避免 None 不可调用导致崩溃
        executor.result.status = "failed"
        executor.result.error = "未提供可执行的测试函数 test_func"
        executor.result.report_path = await executor._generate_report()
        return executor.result

    # 把 resume_from_step 注入到测试函数可访问的位置（通过 executor 属性）
    executor._resume_from_step = resume_from_step
    return await executor.run(test_func, browser_type, headless)


def run_test(
    case_name: str,
    test_func: Callable,
    browser_type: str = "chromium",
    headless: bool = False,
    execution_id: Optional[str] = None,
) -> TestExecutionResult:
    """
    同步执行测试（包装 async）。
    注意：不可在已有事件循环（如异步视图）中调用，应使用 run_test_async。
    """
    return asyncio.run(
        run_test_async(case_name, test_func, browser_type, headless, execution_id)
    )