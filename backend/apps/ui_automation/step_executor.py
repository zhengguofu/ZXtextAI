"""
统一步骤执行器（全异步版本）
负责包装所有测试动作，统一处理截图、日志、异常捕获和证据收集

注意：本执行器基于 Playwright 异步 API（async_api），所有页面操作均为 async/await。
所有关键测试动作都通过 execute_step() 统一包装，确保：
- 每个步骤执行前/后自动截图（真实写入磁盘）
- 步骤描述、开始/结束时间、耗时、URL、标题完整记录
- 异常时收集完整失败证据（截图、DOM、控制台日志）
- 步骤结果写入结构化日志，供报告生成使用
"""
import os
import time
import json
import logging
import traceback as tb_module
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable, Awaitable

logger = logging.getLogger(__name__)


class StepResult:
    """步骤执行结果"""

    def __init__(self):
        self.step_id: str = ""
        self.step_name: str = ""
        self.step_desc: str = ""
        self.start_time: float = 0
        self.end_time: float = 0
        self.duration: float = 0
        self.success: bool = False
        self.error: Optional[str] = None
        self.current_url: str = ""
        self.page_title: str = ""
        self.before_screenshot_path: str = ""
        self.after_screenshot_path: str = ""
        self.screenshot_b64: str = ""
        self.status: str = "pending"  # pending, running, passed, failed, blocked
        self.action_type: str = ""
        self.element_info: str = ""
        self.har_path: str = ""
        self.trace_path: str = ""
        self.dom_path: str = ""
        self.console_log_path: str = ""
        self.video_path: str = ""
        self.is_blocked: bool = False
        self.block_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'step_id': self.step_id,
            'step_name': self.step_name,
            'step_desc': self.step_desc,
            'start_time': datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else "",
            'end_time': datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else "",
            'duration': round(self.duration, 3),
            'success': self.success,
            'error': self.error,
            'current_url': self.current_url,
            'page_title': self.page_title,
            'before_screenshot_path': self.before_screenshot_path,
            'after_screenshot_path': self.after_screenshot_path,
            'screenshot_b64': self.screenshot_b64,
            'status': self.status,
            'action_type': self.action_type,
            'element_info': self.element_info,
            'har_path': self.har_path,
            'trace_path': self.trace_path,
            'dom_path': self.dom_path,
            'console_log_path': self.console_log_path,
            'video_path': self.video_path,
            'is_blocked': self.is_blocked,
            'block_reason': self.block_reason,
        }


class StepExecutor:
    """
    统一步骤执行器（异步）

    所有测试动作都通过此执行器执行，统一处理：
    - 生成step_id
    - 记录step_name和step_desc
    - 记录开始/结束时间
    - 执行前/后截图
    - 捕获异常
    - 异常时保存额外证据
    - 写日志
    - 收集步骤结果数据
    """

    def __init__(self, page, output_dir: str, case_name: str = "", execution_id: str = ""):
        """
        Args:
            page: Playwright 异步 Page 对象
            output_dir: 输出目录根路径
            case_name: 测试用例名称
            execution_id: 执行ID
        """
        self.page = page
        self.output_dir = output_dir
        self.case_name = case_name
        self.execution_id = execution_id
        self.step_index = 0
        self.steps: List[StepResult] = []
        self.console_logs: List[Dict] = []
        self._trace_enabled = False
        self._har_enabled = False

        # 创建目录结构
        self._create_output_directories()

        # 监听控制台日志
        self._setup_console_listener()

    def _create_output_directories(self):
        """创建输出目录结构"""
        dirs = [
            os.path.join(self.output_dir, 'screenshots'),
            os.path.join(self.output_dir, 'video'),
            os.path.join(self.output_dir, 'trace'),
            os.path.join(self.output_dir, 'har'),
            os.path.join(self.output_dir, 'dom'),
            os.path.join(self.output_dir, 'logs'),
            os.path.join(self.output_dir, 'console'),
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)

    def _setup_console_listener(self):
        """设置控制台日志监听器（异步 Page 的 on 仍是同步注册回调）"""
        try:
            def on_console_message(msg):
                try:
                    location = None
                    if msg.location:
                        location = {
                            'url': msg.location.get('url', '') if isinstance(msg.location, dict) else getattr(msg.location, 'url', ''),
                            'line': msg.location.get('lineNumber', 0) if isinstance(msg.location, dict) else getattr(msg.location, 'line', 0),
                            'column': msg.location.get('columnNumber', 0) if isinstance(msg.location, dict) else getattr(msg.location, 'column', 0),
                        }
                    self.console_logs.append({
                        'timestamp': datetime.now().isoformat(),
                        'type': msg.type,
                        'text': msg.text,
                        'location': location,
                    })
                except Exception:
                    pass

            if hasattr(self.page, 'on'):
                self.page.on('console', on_console_message)
        except Exception as e:
            logger.warning(f"设置控制台监听器失败: {e}")

    def set_page(self, page):
        """更新当前页面对象（切换tab时使用），并重新绑定控制台监听"""
        self.page = page
        self._setup_console_listener()

    def enable_trace(self, enabled: bool = True):
        """启用trace收集（实际由TestExecutor在context级别处理）"""
        self._trace_enabled = enabled

    def enable_har(self, enabled: bool = True):
        """启用HAR收集（实际由TestExecutor在context级别处理）"""
        self._har_enabled = enabled

    async def execute_step(self, step_name: str, action_coro_func: Callable[[], Awaitable[Any]], **kwargs) -> StepResult:
        """
        执行一个测试步骤（异步）

        Args:
            step_name: 步骤名称
            action_coro_func: 无参的异步动作函数（返回协程）
            **kwargs: 支持:
                - step_desc: 步骤描述
                - action_type: 操作类型
                - element_info: 元素信息
                - skip_before_screenshot: 是否跳过执行前截图
                - skip_after_screenshot: 是否跳过执行后截图

        Returns:
            StepResult: 步骤执行结果
        """
        self.step_index += 1

        # 创建步骤结果对象
        result = StepResult()
        result.step_id = f"step_{self.execution_id}_{self.step_index}" if self.execution_id else f"step_{self.step_index}"
        result.step_name = step_name
        result.step_desc = kwargs.get('step_desc', '')
        result.action_type = kwargs.get('action_type', '')
        result.element_info = kwargs.get('element_info', '')
        result.status = "running"

        # 记录开始时间
        result.start_time = time.time()

        try:
            # 获取当前页面信息
            result.current_url = getattr(self.page, 'url', '')
            try:
                result.page_title = await self.page.title()
            except Exception:
                result.page_title = ''

            # 执行前截图（除非跳过）
            if not kwargs.get('skip_before_screenshot', False):
                result.before_screenshot_path = await self._capture_screenshot(f"step_{self.step_index}_before")

            # 执行动作
            logger.info(f"[Step {self.step_index}] 执行: {step_name} | 描述: {result.step_desc}")

            # 执行异步动作函数
            await action_coro_func()

            # 执行后截图（除非跳过）
            if not kwargs.get('skip_after_screenshot', False):
                result.after_screenshot_path = await self._capture_screenshot(f"step_{self.step_index}_after")

            # 更新执行后URL/标题
            result.current_url = getattr(self.page, 'url', result.current_url)

            # 标记成功
            result.success = True
            result.status = "passed"
            logger.info(f"[Step {self.step_index}] [OK] 成功")

            return result

        except Exception as e:
            # 捕获异常
            result.success = False
            result.status = "failed"
            result.error = str(e) + "\n\n" + tb_module.format_exc()

            # 失败时收集完整证据
            await self._collect_failure_evidence(result, f"step_{self.step_index}_failed")

            logger.error(f"[Step {self.step_index}] [FAIL] 失败: {e}")

            return result
        finally:
            # 记录结束时间和耗时
            result.end_time = time.time()
            result.duration = result.end_time - result.start_time

            # 添加到步骤列表
            self.steps.append(result)

            # 记录日志
            self._log_step(result)

    async def _collect_failure_evidence(self, result: StepResult, filename_prefix: str):
        """收集失败证据链"""
        try:
            # 失败截图（视口 + 全页）
            result.after_screenshot_path = await self._capture_screenshot(f"{filename_prefix}_viewport", full_page=False)
            await self._capture_screenshot(f"{filename_prefix}_fullpage", full_page=True)
            result.dom_path = await self.save_dom(f"{filename_prefix}")
            result.console_log_path = self.save_console_logs(f"{filename_prefix}")
        except Exception as e:
            logger.warning(f"收集失败证据时出错: {e}")

    async def _capture_screenshot(self, filename_prefix: str, full_page: bool = False) -> str:
        """
        捕获页面截图（异步）

        Returns:
            截图文件路径，失败返回空字符串
        """
        try:
            timestamp = int(time.time() * 1000)
            filename = f"{filename_prefix}_{timestamp}.png"
            screenshot_path = os.path.join(self.output_dir, 'screenshots', filename)

            # 直接保存到磁盘（path 参数让 Playwright 自己写文件，最稳）
            await self.page.screenshot(path=screenshot_path, full_page=full_page, timeout=15000)

            logger.debug(f"截图已保存: {screenshot_path}")
            return screenshot_path

        except Exception as e:
            logger.warning(f"截图失败 ({filename_prefix}): {e}")
            return ""

    async def capture_full_page_screenshot(self, filename_prefix: str = "fullpage") -> str:
        """捕获全页截图"""
        return await self._capture_screenshot(filename_prefix, full_page=True)

    async def save_dom(self, filename_prefix: str = "dom") -> str:
        """保存当前页面DOM（异步）"""
        try:
            timestamp = int(time.time() * 1000)
            filename = f"{filename_prefix}_{timestamp}.html"
            dom_path = os.path.join(self.output_dir, 'dom', filename)

            html_content = await self.page.content()

            with open(dom_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.debug(f"DOM已保存: {dom_path}")
            return dom_path

        except Exception as e:
            logger.warning(f"保存DOM失败: {e}")
            return ""

    def save_console_logs(self, filename_prefix: str = "console") -> str:
        """保存控制台日志（同步，仅写文件）"""
        try:
            timestamp = int(time.time() * 1000)
            filename = f"{filename_prefix}_{timestamp}.log"
            log_path = os.path.join(self.output_dir, 'console', filename)

            with open(log_path, 'w', encoding='utf-8') as f:
                for log_entry in self.console_logs:
                    f.write(f"[{log_entry['timestamp']}] [{log_entry['type']}] {log_entry['text']}\n")
                    if log_entry.get('location'):
                        loc = log_entry['location']
                        f.write(f"              @ {loc.get('url')}:{loc.get('line')}:{loc.get('column')}\n")

            logger.debug(f"控制台日志已保存: {log_path}")
            return log_path

        except Exception as e:
            logger.warning(f"保存控制台日志失败: {e}")
            return ""

    def _log_step(self, result: StepResult):
        """记录步骤日志到文件"""
        log_entry = {
            'step_id': result.step_id,
            'step_name': result.step_name,
            'step_desc': result.step_desc,
            'action_type': result.action_type,
            'element_info': result.element_info,
            'start_time': datetime.fromtimestamp(result.start_time).isoformat(),
            'end_time': datetime.fromtimestamp(result.end_time).isoformat(),
            'duration': round(result.duration, 3),
            'success': result.success,
            'status': result.status,
            'error': result.error,
            'current_url': result.current_url,
            'page_title': result.page_title,
            'before_screenshot': result.before_screenshot_path,
            'after_screenshot': result.after_screenshot_path,
            'dom_path': result.dom_path,
            'console_log_path': result.console_log_path,
        }

        try:
            log_name = f"steps_{self.execution_id}.log" if self.execution_id else "steps.log"
            log_file = os.path.join(self.output_dir, 'logs', log_name)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.warning(f"写入步骤日志失败: {e}")

    def generate_step_narrative(self, step: StepResult) -> str:
        """
        生成步骤的"讲解文字"（Narrative）
        让用户像看测试教程一样，清楚每一步在做什么、看到了什么、得到了什么
        """
        try:
            parts = []

            action = step.action_type or '执行'
            target = step.element_info or ''
            desc = step.step_desc or ''

            # 1. 步骤目标说明
            narrative_intro = {
                'navigate': f'🌐 **打开页面**：导航到目标URL',
                'click': f'👆 **点击操作**：在页面上点击 `{target or "目标元素"}`',
                'fill': f'⌨️ **输入操作**：在 `{target or "输入框"}` 中填写内容',
                'waitFor': f'⏳ **等待元素**：等待 `{target or "目标元素"}` 出现',
                'wait': f'⏱️ **等待**：暂停 {step.duration:.2f} 秒',
                'submit': f'📤 **提交操作**：执行表单提交',
                'verify': f'✅ **验证操作**：检查页面状态是否符合预期',
                'select': f'📋 **选择操作**：在 `{target or "下拉框"}` 中选择选项',
                'hover': f'🖱️ **悬停操作**：鼠标悬停在 `{target or "目标元素"}`',
            }.get(action, f'▶️ **执行操作**：{action} {target}')

            parts.append(narrative_intro)
            if desc and desc != narrative_intro and len(desc) > 3:
                parts.append(f'📝 **步骤说明**：{desc}')

            # 2. 页面状态
            page_state_parts = []
            if step.page_title:
                page_state_parts.append(f'页面标题为「{step.page_title}」')
            if step.current_url:
                url_short = step.current_url[:80] + '...' if len(step.current_url) > 80 else step.current_url
                page_state_parts.append(f'当前URL `{url_short}`')
            if page_state_parts:
                parts.append('🔍 **页面观察**：' + '，'.join(page_state_parts) + '。')

            # 3. 执行结果
            if step.status == 'passed':
                parts.append('✅ **执行结果**：操作按预期完成，页面响应正常。')
            elif step.status == 'failed':
                error_msg = (step.error or '').split('\n')[0][:200]
                parts.append(f'❌ **执行结果**：操作执行失败。错误信息：`{error_msg}`')
            elif step.status == 'blocked':
                parts.append(f'⚠️ **执行结果**：操作被阻塞。原因：{step.block_reason or "未明确"}')
            elif step.status == 'running':
                parts.append('⏳ **执行中**：正在执行此步骤...')

            # 4. 截图说明
            if step.before_screenshot_path:
                parts.append(f'📷 **执行前截图**：已保存（`{os.path.basename(step.before_screenshot_path)}`），展示操作前的页面状态')
            if step.after_screenshot_path:
                parts.append(f'📷 **执行后截图**：已保存（`{os.path.basename(step.after_screenshot_path)}`），展示操作后的页面变化')

            # 5. 耗时
            if step.duration > 0:
                parts.append(f'⏱️ **耗时**：{step.duration:.3f}秒')

            return '\n\n'.join(parts)
        except Exception as e:
            logger.warning(f"生成步骤讲解文字失败: {e}")
            return step.step_desc or step.step_name or ''

    def get_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        total = len(self.steps)
        passed = sum(1 for s in self.steps if s.status == 'passed')
        failed = sum(1 for s in self.steps if s.status == 'failed')
        blocked = sum(1 for s in self.steps if s.is_blocked)

        return {
            'total_steps': total,
            'passed': passed,
            'failed': failed,
            'blocked': blocked,
            'pass_rate': round(passed / total * 100, 2) if total > 0 else 0,
            'total_duration': sum(s.duration for s in self.steps),
            'case_name': self.case_name,
            'execution_id': self.execution_id,
        }

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典（用于报告生成）"""
        return {
            'summary': self.get_summary(),
            'steps': [step.to_dict() for step in self.steps],
            'output_dir': self.output_dir,
            'case_name': self.case_name,
            'execution_id': self.execution_id,
        }

    def export_steps_json(self) -> str:
        """导出步骤数据为JSON文件"""
        try:
            filename = f"steps_{self.execution_id}.json" if self.execution_id else "steps.json"
            output_path = os.path.join(self.output_dir, 'logs', filename)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

            logger.info(f"步骤数据已导出: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"导出步骤数据失败: {e}")
            return ""

    # ========== 常用步骤包装方法（全部异步） ==========

    async def click(self, locator, step_desc: str = "", element_name: str = "") -> StepResult:
        """点击元素"""
        return await self.execute_step(
            "点击元素",
            lambda: locator.click(),
            step_desc=step_desc or f"点击元素: {element_name}",
            action_type="click",
            element_info=element_name,
        )

    async def fill(self, locator, text: str, step_desc: str = "", element_name: str = "") -> StepResult:
        """输入文本"""
        return await self.execute_step(
            "输入文本",
            lambda: locator.fill(text),
            step_desc=step_desc or f"在 {element_name} 输入: {text[:30]}",
            action_type="fill",
            element_info=element_name,
        )

    async def goto(self, url: str, step_desc: str = "") -> StepResult:
        """导航到URL"""
        result = await self.execute_step(
            "导航到页面",
            lambda: self.page.goto(url, wait_until='domcontentloaded', timeout=30000),
            step_desc=step_desc or f"访问: {url}",
            action_type="navigate",
            skip_before_screenshot=True,
        )

        # 导航后自动检查验证码
        if result.success:
            try:
                from .captcha_handler_v2 import CaptchaHandlerV2
                handler = CaptchaHandlerV2(self.page, self.output_dir)
                captcha_result = await handler.detect_and_solve()
                if captcha_result.get('solved') and captcha_result.get('captcha_type'):
                    logger.info(f"导航后自动解决验证码: {captcha_result.get('captcha_type')}")
                    result.step_desc = (result.step_desc or '') + f" [验证码已自动解决]"
            except Exception as e:
                logger.debug(f"导航后验证码检查跳过: {e}")

        return result

    async def auto_solve_captcha(self) -> Dict[str, Any]:
        """
        主动检查并尝试自动解决当前页面的验证码
        返回处理结果 dict
        """
        try:
            from .captcha_handler_v2 import CaptchaHandlerV2
            handler = CaptchaHandlerV2(self.page, self.output_dir)
            return await handler.detect_and_solve()
        except Exception as e:
            logger.error(f"自动验证码处理失败: {e}")
            return {'solved': False, 'error': str(e)}

    async def wait_for_selector(self, selector: str, step_desc: str = "", timeout: int = 15000) -> StepResult:
        """等待元素出现"""
        return await self.execute_step(
            "等待元素",
            lambda: self.page.wait_for_selector(selector, timeout=timeout),
            step_desc=step_desc or f"等待元素: {selector}",
            action_type="waitFor",
            element_info=selector,
        )

    async def wait_for_timeout(self, milliseconds: int, step_desc: str = "") -> StepResult:
        """固定等待"""
        return await self.execute_step(
            "固定等待",
            lambda: self.page.wait_for_timeout(milliseconds),
            step_desc=step_desc or f"等待 {milliseconds}ms",
            action_type="wait",
            skip_before_screenshot=True,
        )

    async def get_text(self, locator, step_desc: str = "", element_name: str = "") -> Tuple[StepResult, Optional[str]]:
        """获取文本"""
        holder = {'text': None}

        async def action():
            holder['text'] = await locator.inner_text()

        result = await self.execute_step(
            "获取文本",
            action,
            step_desc=step_desc or f"获取 {element_name} 文本",
            action_type="getText",
            element_info=element_name,
        )
        return result, holder['text']

    async def assert_text_contains(self, locator, expected_text: str, step_desc: str = "") -> StepResult:
        """断言文本包含"""
        async def action():
            actual_text = await locator.inner_text()
            if expected_text not in actual_text:
                raise AssertionError(f"文本断言失败: 期望包含 '{expected_text}'，实际为 '{actual_text}'")

        return await self.execute_step(
            "断言文本包含",
            action,
            step_desc=step_desc or f"断言文本包含: '{expected_text}'",
            action_type="assert",
            element_info=f"期望: {expected_text}",
        )

    async def assert_element_visible(self, locator, step_desc: str = "", element_name: str = "") -> StepResult:
        """断言元素可见"""
        async def action():
            if not await locator.is_visible():
                raise AssertionError(f"元素不可见: {element_name}")

        return await self.execute_step(
            "断言元素可见",
            action,
            step_desc=step_desc or f"断言元素可见: {element_name}",
            action_type="assert",
            element_info=element_name,
        )

    async def select_option(self, locator, value: str, step_desc: str = "", element_name: str = "") -> StepResult:
        """选择下拉框选项"""
        return await self.execute_step(
            "选择下拉框",
            lambda: locator.select_option(value=value),
            step_desc=step_desc or f"选择 {element_name}: {value}",
            action_type="select",
            element_info=element_name,
        )

    async def hover(self, locator, step_desc: str = "", element_name: str = "") -> StepResult:
        """悬停"""
        return await self.execute_step(
            "悬停",
            lambda: locator.hover(),
            step_desc=step_desc or f"悬停在 {element_name}",
            action_type="hover",
            element_info=element_name,
        )

    async def scroll_to(self, locator, step_desc: str = "", element_name: str = "") -> StepResult:
        """滚动到元素"""
        return await self.execute_step(
            "滚动到元素",
            lambda: locator.scroll_into_view_if_needed(),
            step_desc=step_desc or f"滚动到 {element_name}",
            action_type="scroll",
            element_info=element_name,
        )

    async def switch_tab(self, index: int = -1, step_desc: str = "") -> StepResult:
        """切换标签页"""
        return await self.execute_step(
            "切换标签页",
            lambda: self._switch_tab_impl(index),
            step_desc=step_desc or f"切换到标签页 {index}",
            action_type="switchTab",
        )

    async def _switch_tab_impl(self, index: int):
        """切换标签页实现"""
        pages = self.page.context.pages
        target_page = pages[-1] if index == -1 else pages[index]
        await target_page.bring_to_front()
        self.set_page(target_page)
        return True

    async def clear(self, locator, step_desc: str = "", element_name: str = "") -> StepResult:
        """清空输入框"""
        return await self.execute_step(
            "清空输入框",
            lambda: locator.clear(),
            step_desc=step_desc or f"清空 {element_name}",
            action_type="clear",
            element_info=element_name,
        )

    async def type(self, locator, text: str, step_desc: str = "", element_name: str = "") -> StepResult:
        """逐字符输入"""
        return await self.execute_step(
            "逐字符输入",
            lambda: locator.type(text),
            step_desc=step_desc or f"在 {element_name} 逐字符输入: {text[:30]}",
            action_type="type",
            element_info=element_name,
        )

    async def press(self, key: str, step_desc: str = "") -> StepResult:
        """按键"""
        return await self.execute_step(
            "按键",
            lambda: self.page.keyboard.press(key),
            step_desc=step_desc or f"按下: {key}",
            action_type="press",
            element_info=key,
        )

    async def check(self, locator, step_desc: str = "", element_name: str = "") -> StepResult:
        """勾选复选框"""
        return await self.execute_step(
            "勾选复选框",
            lambda: locator.check(),
            step_desc=step_desc or f"勾选 {element_name}",
            action_type="check",
            element_info=element_name,
        )

    async def uncheck(self, locator, step_desc: str = "", element_name: str = "") -> StepResult:
        """取消勾选复选框"""
        return await self.execute_step(
            "取消勾选",
            lambda: locator.uncheck(),
            step_desc=step_desc or f"取消勾选 {element_name}",
            action_type="uncheck",
            element_info=element_name,
        )

    async def set_input_files(self, locator, files, step_desc: str = "", element_name: str = "") -> StepResult:
        """上传文件"""
        return await self.execute_step(
            "上传文件",
            lambda: locator.set_input_files(files),
            step_desc=step_desc or f"上传文件到 {element_name}",
            action_type="upload",
            element_info=element_name,
        )

    async def evaluate(self, expression: str, step_desc: str = "") -> Tuple[StepResult, Any]:
        """执行JavaScript"""
        holder = {'value': None}

        async def action():
            holder['value'] = await self.page.evaluate(expression)

        result = await self.execute_step(
            "执行JavaScript",
            action,
            step_desc=step_desc or f"执行JS: {expression[:50]}",
            action_type="evaluate",
            element_info=expression[:100],
        )
        return result, holder['value']

    async def go_back(self, step_desc: str = "") -> StepResult:
        """返回上一页"""
        return await self.execute_step(
            "返回上一页",
            lambda: self.page.go_back(),
            step_desc=step_desc or "返回上一页",
            action_type="goBack",
        )

    async def go_forward(self, step_desc: str = "") -> StepResult:
        """前进到下一页"""
        return await self.execute_step(
            "前进到下一页",
            lambda: self.page.go_forward(),
            step_desc=step_desc or "前进到下一页",
            action_type="goForward",
        )

    async def reload(self, step_desc: str = "") -> StepResult:
        """刷新页面"""
        return await self.execute_step(
            "刷新页面",
            lambda: self.page.reload(),
            step_desc=step_desc or "刷新页面",
            action_type="reload",
        )

    async def wait_for_load_state(self, state: str = "domcontentloaded", step_desc: str = "") -> StepResult:
        """等待页面加载状态"""
        return await self.execute_step(
            "等待加载状态",
            lambda: self.page.wait_for_load_state(state),
            step_desc=step_desc or f"等待加载状态: {state}",
            action_type="waitForLoad",
            skip_before_screenshot=True,
        )

    async def assert_url_contains(self, expected: str, step_desc: str = "") -> StepResult:
        """断言URL包含"""
        async def action():
            if expected not in self.page.url:
                raise AssertionError(f"URL断言失败: 期望包含 '{expected}'，实际为 '{self.page.url}'")

        return await self.execute_step(
            "断言URL包含",
            action,
            step_desc=step_desc or f"断言URL包含: {expected}",
            action_type="assert",
            element_info=f"期望URL包含: {expected}",
        )

    async def assert_title_contains(self, expected: str, step_desc: str = "") -> StepResult:
        """断言标题包含"""
        async def action():
            title = await self.page.title()
            if expected not in title:
                raise AssertionError(f"标题断言失败: 期望包含 '{expected}'，实际为 '{title}'")

        return await self.execute_step(
            "断言标题包含",
            action,
            step_desc=step_desc or f"断言标题包含: {expected}",
            action_type="assert",
            element_info=f"期望标题包含: {expected}",
        )

    async def assert_element_count(self, selector: str, expected_count: int, step_desc: str = "") -> StepResult:
        """断言元素数量"""
        async def action():
            count = await self.page.locator(selector).count()
            if count != expected_count:
                raise AssertionError(f"元素数量断言失败: 期望 {expected_count}，实际 {count}")

        return await self.execute_step(
            "断言元素数量",
            action,
            step_desc=step_desc or f"断言元素数量为 {expected_count}",
            action_type="assert",
            element_info=f"选择器: {selector}, 期望数量: {expected_count}",
        )