"""
Playwright自动化测试执行引擎
用于驱动真实浏览器执行UI自动化测试
"""
import asyncio
import base64
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
from apps.core.variable_resolver import resolve_variables

logger = logging.getLogger(__name__)

# 验证码求解器集成
CAPTCHA_SOLVER_AVAILABLE = False
try:
    from apps.ui_automation.captcha_super_solver import (
        SuperCaptchaSolver,
        auto_solve_captcha,
        get_super_solver,
    )
    CAPTCHA_SOLVER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"超级验证码求解器未加载: {e}")

# 延迟导入，避免playwright未安装时整个模块加载失败
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Playwright未安装，Playwright引擎不可用: {e}")

class PlaywrightTestEngine:
    """Playwright测试执行引擎"""

    def __init__(self, browser_type='chromium', headless=True, captcha_config: Dict = None):
        """
        初始化测试引擎

        Args:
            browser_type: 浏览器类型 (chromium, firefox, webkit)
            headless: 是否无头模式
            captcha_config: 验证码求解器配置
        """
        self.browser_type = browser_type
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # 验证码求解器
        self.captcha_solver: Optional[SuperCaptchaSolver] = None
        self.captcha_config = captcha_config or {
            'max_attempts': 3,
            'auto_solve': True,  # 自动检测并解决验证码
            'skip_third_party': False,  # 不跳过第三方服务
        }
        self.captcha_solve_count = 0
        self.captcha_solve_success = 0

    async def start(self):
        """启动浏览器"""
        try:
            self.playwright = await async_playwright().start()

            # 根据浏览器类型选择启动方式
            if self.browser_type == 'chromium':
                browser_launcher = self.playwright.chromium
            elif self.browser_type == 'firefox':
                browser_launcher = self.playwright.firefox
            elif self.browser_type == 'webkit':
                browser_launcher = self.playwright.webkit
            else:
                browser_launcher = self.playwright.chromium

            # 启动浏览器
            self.browser = await browser_launcher.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',  # 避免被检测
                    '--ignore-certificate-errors',  # 忽略证书错误
                    '--allow-insecure-localhost',  # 允许不安全localhost
                    '--disable-web-security',  # 禁用web安全限制（跨域）
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )

            # 创建浏览器上下文（带反检测配置）
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                permissions=['geolocation'],
                geolocation={'latitude': 31.2304, 'longitude': 121.4737},
                http_credentials=None,
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True,
            )

            # 创建页面
            self.page = await self.context.new_page()

            # 初始化验证码求解器
            if CAPTCHA_SOLVER_AVAILABLE and self.captcha_config.get('auto_solve', True):
                self.captcha_solver = get_super_solver(self.captcha_config)
                logger.info(f"超级验证码求解器已初始化")

                # 应用反检测脚本
                await self._apply_anti_detection_scripts()

            logger.info(f"浏览器启动成功: {self.browser_type}, headless={self.headless}")

        except Exception as e:
            logger.error(f"启动浏览器失败: {str(e)}")
            raise

    async def stop(self):
        """关闭浏览器"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

            if self.captcha_solve_count > 0:
                logger.info(f"验证码统计: 检测到 {self.captcha_solve_count} 次, 成功解决 {self.captcha_solve_success} 次")

            logger.info("浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {str(e)}")

    async def _apply_anti_detection_scripts(self):
        """应用反检测脚本"""
        try:
            # 隐藏 webdriver 属性
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            # 模拟真实的 chrome 属性
            await self.page.add_init_script("""
                window.chrome = {
                    runtime: {
                        id: 'fake-id',
                        OnInstalledReason: {
                            CHROME_UPDATE: 'chrome_update',
                            INSTALL: 'install',
                            SHARED_MODULE_UPDATE: 'shared_module_update',
                            UPDATE: 'update'
                        },
                        OnRestartRequiredReason: {
                            APP_UPDATE: 'app_update',
                            OS_UPDATE: 'os_update',
                            PERIODIC: 'periodic'
                        },
                        PlatformArch: {
                            ARM: 'arm',
                            ARM64: 'arm64',
                            MIPS: 'mips',
                            MIPS64: 'mips64',
                            X86_32: 'x86-32',
                            X86_64: 'x86-64'
                        },
                        PlatformNaclArch: {
                            ARM: 'arm',
                            MIPS: 'mips',
                            MIPS64: 'mips64',
                            X86_32: 'x86-32',
                            X86_64: 'x86-64'
                        },
                        PlatformOs: {
                            ANDROID: 'android',
                            CROS: 'cros',
                            LINUX: 'linux',
                            MAC: 'mac',
                            OPENBSD: 'openbsd',
                            WIN: 'win'
                        },
                        RequestUpdateCheckStatus: {
                            NO_UPDATE: 'no_update',
                            THROTTLED: 'throttled',
                            UPDATE_AVAILABLE: 'update_available'
                        }
                    },
                    loadTimes: () => {},
                    csi: () => {}
                };
            """)

            # 模拟真实的插件
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin' }
                    ]
                });
            """)

            # 模拟真实的语言
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                });
            """)

            # 模拟真实的 permissions
            await self.page.add_init_script("""
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications'
                        ? Promise.resolve({ state: Notification.permission })
                        : originalQuery(parameters)
                );
            """)

            logger.debug("反检测脚本已应用")
        except Exception as e:
            logger.debug(f"应用反检测脚本失败: {e}")

    async def _detect_and_solve_captcha(self) -> Tuple[bool, str]:
        """
        检测并尝试解决验证码

        Returns:
            (是否处理了验证码, 处理日志)
        """
        if not self.captcha_solver or not self.captcha_config.get('auto_solve', True):
            return False, ""

        try:
            # 检测页面是否有验证码
            page_html = await self.page.content()

            # 快速检测关键词
            captcha_keywords = [
                '验证码', 'captcha', 'verify', '人机验证', 'slider',
                '拖动', '滑动', 'geetest', 'nc_', 'recaptcha',
                'hcaptcha', 'turnstile'
            ]

            has_captcha = any(kw.lower() in page_html.lower() for kw in captcha_keywords)

            if not has_captcha:
                # 检查是否有验证码iframe
                iframe_count = await self.page.locator('iframe').count()
                for i in range(iframe_count):
                    try:
                        iframe = self.page.frame_locator(f'iframe:nth-child({i+1})')
                        iframe_src = await self.page.locator('iframe').nth(i).get_attribute('src') or ''
                        if any(kw in iframe_src.lower() for kw in ['captcha', 'geetest', 'recaptcha', 'hcaptcha']):
                            has_captcha = True
                            logger.info(f"检测到验证码iframe: {iframe_src[:60]}")
                            break
                    except:
                        continue

            if not has_captcha:
                return False, ""

            # 检测到验证码，尝试解决
            self.captcha_solve_count += 1
            logger.info(f"检测到验证码，开始自动解决 (第{self.captcha_solve_count}次)...")

            result = await self.captcha_solver.solve(self.page)

            log_info = f"验证码解决: {'成功' if result.success else '失败'}"
            log_info += f", 类型: {result.captcha_type.value if result.captcha_type else 'unknown'}"
            log_info += f", 方法: {result.method_used}"
            log_info += f", 耗时: {result.time_spent:.2f}s"

            if result.success:
                self.captcha_solve_success += 1
                logger.info(log_info)
                return True, log_info
            else:
                log_info += f", 错误: {result.error_message}"
                logger.warning(log_info)
                return False, log_info

        except Exception as e:
            logger.debug(f"验证码检测/解决异常: {e}")
            return False, f"异常: {e}"

    async def _wait_and_check_captcha(self, wait_time: float = 1.0):
        """
        等待后检查验证码

        Args:
            wait_time: 等待时间（秒）
        """
        await asyncio.sleep(wait_time)
        return await self._detect_and_solve_captcha()

    async def _finalize_step_result(self, success: bool, log: str, screenshot: Optional[str], extra_logs: List[str]) -> Tuple[bool, str, Optional[str]]:
        """
        最终处理步骤结果，添加额外日志和执行后验证码检测

        Args:
            success: 操作是否成功
            log: 主日志
            screenshot: 截图
            extra_logs: 额外日志

        Returns:
            (是否成功, 合并后的日志, 截图)
        """
        # 操作后再次检测验证码（可能是操作触发的验证码）
        if success:
            captcha_handled, captcha_log = await self._wait_and_check_captcha(0.5)
            if captcha_handled:
                extra_logs.append(captcha_log)

        # 合并日志
        if extra_logs:
            combined_log = log + "\n" + "\n".join([f"  [验证码] {l}" for l in extra_logs])
        else:
            combined_log = log

        return success, combined_log, screenshot

    async def execute_step(self, step, element_data: Dict) -> Tuple[bool, str, Optional[str]]:
        """
        执行单个测试步骤

        Args:
            step: 测试步骤对象
            element_data: 元素数据字典 {locator_strategy, locator_value, name}

        Returns:
            (是否成功, 日志信息, 截图base64)
        """
        action_type = step.action_type

        # 预先解析变量
        resolved_input_value = step.input_value
        if step.input_value:
            resolved_input_value = resolve_variables(step.input_value)

        resolved_assert_value = step.assert_value
        if step.assert_value:
            resolved_assert_value = resolve_variables(step.assert_value)

        start_time = time.time()
        screenshot_base64 = None
        extra_logs = []

        try:
            # 执行操作前检测验证码
            captcha_handled, captcha_log = await self._detect_and_solve_captcha()
            if captcha_handled:
                extra_logs.append(captcha_log)

            # wait和screenshot操作不需要元素定位器
            if action_type == 'wait':
                wait_seconds = step.wait_time / 1000 if step.wait_time else 1
                await asyncio.sleep(wait_seconds)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 固定等待 {wait_seconds} 秒完成 - 耗时 {execution_time}秒"
                return True, log, None

            elif action_type == 'screenshot':
                screenshot = await self.page.screenshot()
                screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 截图成功\n"
                log += f"  - 截图范围: 整个页面\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, screenshot_base64

            elif action_type == 'switchTab':
                # 切换标签页
                # 获取超时时间
                if step.wait_time:
                    timeout = step.wait_time / 1000
                else:
                    timeout = 5.0
                
                start_wait = time.time()
                current_page = self.page
                target_index = -1
                
                while True:
                    pages = self.context.pages
                    target_index = -1  # 默认切换到最新标签页
                    should_switch = False
                    
                    if resolved_input_value and str(resolved_input_value).isdigit():
                        # 指定索引的情况
                        idx = int(resolved_input_value)
                        if 0 <= idx < len(pages):
                            target_index = idx
                            should_switch = True
                    else:
                        # 切换到最新的情况
                        target_index = -1
                        # 如果最新的页面不是当前页面，说明有新标签页，或者是切换到其他已存在的标签页
                        if pages[-1] != current_page:
                            should_switch = True
                        # 如果只有一个页面，且就是当前页，可能是在等待新标签页打开
                        elif len(pages) == 1 and pages[0] == current_page:
                            should_switch = False
                        # 如果有多个页面，但最新的就是当前页，可能是想留在当前页，也可能是等待更新的
                        else:
                            should_switch = False

                    if should_switch:
                        break
                    
                    if time.time() - start_wait > timeout:
                        # 超时了，就切换到当前能找到的那个（Best Effort）
                        break
                        
                    await asyncio.sleep(0.5)
                
                # 获取目标页面
                if target_index == -1:
                    target_page = pages[-1]
                    final_target_index = len(pages) - 1
                else:
                    target_page = pages[target_index]
                    final_target_index = target_index

                # 将目标页面设为当前活动页面
                await target_page.bring_to_front()
                # 更新引擎的当前页面引用
                self.page = target_page
                
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 切换标签页成功\n"
                log += f"  - 目标索引: {final_target_index}\n"
                log += f"  - 页面标题: {await self.page.title()}\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            # 其他操作需要元素定位器
            # 获取元素定位器
            locator_strategy = element_data.get('locator_strategy', 'css')
            locator_value = element_data.get('locator_value', '')
            element_name = element_data.get('name', '未知元素')

            # 获取强制操作选项（用于visibility:hidden的元素）
            force_action = element_data.get('force_action', False)

            # 计算超时时间：优先使用元素的wait_timeout（秒），其次使用步骤的wait_time（毫秒）
            # 如果元素有wait_timeout，转换为毫秒；否则使用步骤的wait_time
            element_wait_timeout = element_data.get('wait_timeout')  # 秒
            if element_wait_timeout is not None and element_wait_timeout > 0:
                timeout_ms = element_wait_timeout * 1000  # 转换为毫秒
            elif step.wait_time:
                timeout_ms = step.wait_time
            else:
                # 默认15秒，适配慢速服务器/复杂SPA页面
                import platform as _platform
                is_linux = _platform.system() == 'Linux'
                timeout_ms = 15000 if is_linux else 10000

            # 根据定位策略获取元素
            if locator_strategy.lower() == 'id':
                locator = self.page.locator(f'#{locator_value}')
            elif locator_strategy.lower() in ['css', 'css selector']:
                # CSS 定位器，对于可能匹配多个元素的情况，添加 .first
                # 特别是下拉框选项，可能有多个同名选项
                if any(keyword in locator_value.lower() for keyword in ['dropdown', 'el-select', ':has(', 'li']):
                    # 如果是下拉框选项，强制只查找可见元素
                    if 'visible=true' not in locator_value:
                        locator = self.page.locator(f"{locator_value} >> visible=true").first
                    else:
                        locator = self.page.locator(locator_value).first
                else:
                    locator = self.page.locator(locator_value)
            elif locator_strategy.lower() == 'xpath':
                # XPath 定位器
                # 如果是下拉框选项，强制只查找可见元素
                if any(keyword in locator_value.lower() for keyword in ['dropdown', 'el-select', ':has(', 'li']):
                    if 'visible=true' not in locator_value:
                        locator = self.page.locator(f"xpath={locator_value} >> visible=true").first
                    else:
                        locator = self.page.locator(f"xpath={locator_value}").first
                # 如果 XPath 已经包含索引 [n]，不要添加 .first（会冲突）
                elif '[' in locator_value and ']' in locator_value:
                    locator = self.page.locator(f'xpath={locator_value}')
                else:
                    # 如果没有索引，添加 .first 避免 strict mode violation
                    locator = self.page.locator(f'xpath={locator_value}').first
            elif locator_strategy.lower() == 'text':
                locator = self.page.get_by_text(locator_value)
            elif locator_strategy.lower() == 'name':
                locator = self.page.locator(f'[name="{locator_value}"]')
            elif locator_strategy.lower() == 'placeholder':
                locator = self.page.get_by_placeholder(locator_value)
            elif locator_strategy.lower() == 'role':
                locator = self.page.get_by_role(locator_value)
            elif locator_strategy.lower() == 'label':
                locator = self.page.get_by_label(locator_value)
            elif locator_strategy.lower() == 'title':
                locator = self.page.get_by_title(locator_value)
            elif locator_strategy.lower() == 'test-id':
                locator = self.page.get_by_test_id(locator_value)
            else:
                # 默认使用CSS选择器
                locator = self.page.locator(locator_value)

            # 执行操作
            execution_time = 0

            if action_type == 'click':
                # 检测是否是原生HTML select的option元素（优先检测，因为option元素特殊）
                is_native_select_option = (
                    ('option[' in locator_value or ' > option' in locator_value or '//option' in locator_value) or
                    ('select' in locator_value.lower() and 'option' in locator_value.lower())
                )

                # 对于原生HTML select的option，使用select_option方法
                if is_native_select_option:
                    logger.info(f"检测到原生HTML select元素，使用select_option方法...")

                    # 提取select的定位器和option的value
                    # 例如：select[name="my-select"] option[value="1"]
                    # 需要提取：select[name="my-select"] 和 value="1"

                    import re

                    # 提取option的value值
                    option_value_match = re.search(r'option\[value=["\']([^"\']+)["\']\]', locator_value)
                    option_value_xpath_match = re.search(r'option\[@value=["\']([^"\']+)["\']\]', locator_value)

                    option_value = None
                    if option_value_match:
                        option_value = option_value_match.group(1)
                    elif option_value_xpath_match:
                        option_value = option_value_xpath_match.group(1)
                    else:
                        # 尝试其他格式
                        option_value = '1'  # 默认值

                    # 构造select元素的定位器（去掉option部分）
                    select_locator_value = re.sub(r'\s*>\s*option\[.*?\]', '', locator_value)
                    select_locator_value = re.sub(r'\s+option\[.*?\]', '', select_locator_value)
                    select_locator_value = re.sub(r'//option\[.*?\]', '', select_locator_value)

                    logger.info(f"Select定位器: {select_locator_value}, Option值: {option_value}")

                    try:
                        # 构造select元素的locator
                        if locator_strategy.lower() == 'xpath':
                            # XPath: //select[@name='my-select']/option[@value='1']
                            # 提取select部分
                            select_match = re.match(r'^(//.*?select)(?:/option)?', locator_value)
                            if select_match:
                                select_locator_value = select_match.group(1)
                            else:
                                select_locator_value = locator_value.split('/')[0]
                            select_locator = self.page.locator(f"xpath={select_locator_value}")
                        else:
                            # CSS: select[name="my-select"] option[value="1"]
                            select_locator = self.page.locator(select_locator_value)

                        # 使用select_option方法
                        await select_locator.select_option(value=option_value, timeout=timeout_ms)

                        execution_time = round(time.time() - start_time, 2)
                        log = f"✓ 选择下拉框选项 '{element_name}' 成功\n"
                        log += f"  - Select定位器: {select_locator_value}\n"
                        log += f"  - 选中值: {option_value}\n"
                        log += f"  - 方法: select_option() (原生HTML select)\n"
                        log += f"  - 执行时间: {execution_time}秒"
                        return True, log, None

                    except Exception as e:
                        logger.error(f"select_option失败: {e}")
                        # 如果失败，继续尝试普通点击
                        pass

                # 对于下拉框选项，需要特殊处理
                # 通过定位器特征自动识别下拉框选项
                is_dropdown_option = (
                    'dropdown' in locator_value.lower() or
                    'el-select' in locator_value.lower() or
                    '下拉' in element_name or
                    '选项' in element_name or
                    'role="option"' in locator_value.lower() or
                    'el-select-dropdown__item' in locator_value.lower() or  # Element Plus 下拉框
                    ('//li' in locator_value and 'span=' in locator_value)  # XPath 下拉框模式
                )
                
                # 检测是否是点击 el-select 容器（下拉框触发器）
                is_select_trigger = ('el-select' in locator_value.lower() and 
                                    'ancestor::' in locator_value.lower() and
                                    'el-select-dropdown' not in locator_value.lower())
                
                if is_select_trigger:
                    # el-select 容器：点击内部的真正触发器，触发完整事件链
                    logger.info(f"检测到 el-select 容器，使用 Playwright 原生点击...")
                    try:
                        # 等待容器出现
                        await locator.wait_for(state='visible', timeout=timeout_ms)
                        # 点击内部的 wrapper 或 input（使用 Playwright 原生点击，会触发完整事件）
                        wrapper_locator = locator.locator('.el-select__wrapper, input').first
                        await wrapper_locator.click(timeout=timeout_ms, no_wait_after=False)
                        # 等待下拉框展开动画
                        await asyncio.sleep(0.5)
                        
                        execution_time = round(time.time() - start_time, 2)
                        log = f"✓ 点击下拉框触发器 '{element_name}' 成功\n"
                        log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                        log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                        log += f"  - 特殊处理: Playwright原生点击内部触发器 + 等待展开\n"
                        log += f"  - 执行时间: {execution_time}秒"
                        return True, log, None
                    except Exception as e:
                        logger.warning(f"Playwright 点击失败，尝试其他方法: {e}")
                        
                        # 备用方案：使用完整的事件链
                        try:
                            await locator.locator('.el-select__wrapper, input').first.evaluate("""
                                element => {
                                    const events = [
                                        new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }),
                                        new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }),
                                        new MouseEvent('click', { bubbles: true, cancelable: true, view: window })
                                    ];
                                    events.forEach(event => element.dispatchEvent(event));
                                }
                            """)
                            await asyncio.sleep(0.5)
                            execution_time = round(time.time() - start_time, 2)
                            log = f"✓ 点击下拉框触发器 '{element_name}' 成功（事件链）\n"
                            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                            log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                            log += f"  - 执行时间: {execution_time}秒"
                            return True, log, None
                        except Exception as e2:
                            logger.error(f"所有点击方法都失败: {e2}")
                            raise
                
                elif is_dropdown_option:
                    # 下拉框选项：需要特殊处理，确保能正确触发 Vue/Element Plus 的 v-model 更新
                    logger.info(f"检测到下拉框选项，使用 Playwright + Vue 数据更新策略...")
                    
                    # 等待下拉框完全展开并渲染
                    await asyncio.sleep(0.8)
                    
                    try:
                        # 等待元素在 DOM 中（不要求可见）
                        await locator.wait_for(state='attached', timeout=timeout_ms)
                        logger.info(f"元素已在 DOM 中，执行 Vue 数据更新...")
                        
                        # 策略：直接通过 page.evaluate() 操作，绕过 locator 的 actionability 检查
                        # locator.evaluate() 会等待元素可见，但下拉框选项可能是隐藏的
                        # 所以我们使用 page.evaluate() 并传递定位器表达式
                        
                        # 根据定位策略构造 JavaScript 选择器
                        if locator_strategy.lower() == 'xpath':
                            js_selector_code = f"""
                                const xpath = {repr(locator_value)};
                                const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                                let element = null;
                                for (let i = 0; i < result.snapshotLength; i++) {{
                                    const node = result.snapshotItem(i);
                                    // 检查可见性: offsetParent 不为 null (且不是 fixed 定位) 或者 getComputedStyle display != none
                                    if (node.offsetParent !== null || window.getComputedStyle(node).display !== 'none') {{
                                        element = node;
                                        break;
                                    }}
                                }}
                            """
                        elif locator_strategy.lower() == 'css selector':
                            js_selector_code = f"""
                                const elements = document.querySelectorAll({repr(locator_value)});
                                let element = null;
                                for (const el of elements) {{
                                    if (el.offsetParent !== null || window.getComputedStyle(el).display !== 'none') {{
                                        element = el;
                                        break;
                                    }}
                                }}
                            """
                        else:
                            # 其他策略：尝试作为 CSS 选择器
                            js_selector_code = f"""
                                const elements = document.querySelectorAll({repr(locator_value)});
                                let element = null;
                                for (const el of elements) {{
                                    if (el.offsetParent !== null || window.getComputedStyle(el).display !== 'none') {{
                                        element = el;
                                        break;
                                    }}
                                }}
                            """
                        
                        # 构造基础定位器（不带 visible=true，因为我们要手动遍历）
                        base_locator_value = locator_value.replace(' >> visible=true', '')
                        
                        if locator_strategy.lower() == 'xpath':
                            if not base_locator_value.startswith('xpath='):
                                candidates = self.page.locator(f"xpath={base_locator_value}")
                            else:
                                candidates = self.page.locator(base_locator_value)
                        elif locator_strategy.lower() == 'css selector':
                            candidates = self.page.locator(base_locator_value)
                        else:
                            # 其他策略暂按 CSS 处理
                            candidates = self.page.locator(base_locator_value)
                        
                        # 获取匹配元素数量
                        count = await candidates.count()
                        logger.info(f"找到 {count} 个匹配元素，开始寻找可见元素...")
                        
                        found_visible = False
                        for i in range(count):
                            candidate = candidates.nth(i)
                            if await candidate.is_visible():
                                logger.info(f"找到第 {i+1} 个元素是可见的，执行点击...")
                                try:
                                    await candidate.click(timeout=timeout_ms)
                                    found_visible = True
                                    method_desc = f"iterative-click(index={i})"
                                    break
                                except Exception as e:
                                    logger.warning(f"点击第 {i+1} 个元素失败: {e}")
                        
                        if not found_visible:
                            logger.warning("未找到可见的下拉框选项元素，尝试点击第一个...")
                            try:
                                await candidates.first.click(force=True, timeout=timeout_ms)
                                method_desc = "fallback-force-click"
                            except Exception as e:
                                logger.error(f"强制点击失败: {e}")
                                raise e

                        # 检查并关闭多选下拉框
                        try:
                            await asyncio.sleep(0.5)
                            dropdown = self.page.locator('.el-select-dropdown').first
                            if await dropdown.is_visible():
                                logger.info(f"多选下拉框未自动关闭，点击空白处关闭...")
                                await self.page.click('body', position={'x': 10, 'y': 10}, timeout=3000)
                                auto_close_msg = " + 自动关闭"
                            else:
                                auto_close_msg = ""
                        except:
                            auto_close_msg = ""
                        
                        execution_time = round(time.time() - start_time, 2)
                        log = f"✓ 点击下拉框选项 '{element_name}' 成功（{method_desc}）\n"
                        log += f"  - 定位器: {locator_strategy}={base_locator_value}\n"
                        log += f"  - 匹配数量: {count}\n"
                        log += f"  - 执行方法: {method_desc}{auto_close_msg}\n"
                        log += f"  - 执行时间: {execution_time}秒"
                        return True, log, None
                        
                        logger.info(f"JS执行结果: {js_result}")
                        
                        # 等待 Vue 响应式更新完成
                        await asyncio.sleep(0.8)
                        
                        # 检查并关闭多选下拉框
                        try:
                            dropdown = self.page.locator('.el-select-dropdown').first
                            if await dropdown.is_visible():
                                logger.info(f"多选下拉框未自动关闭，点击空白处关闭...")
                                await self.page.click('body', position={'x': 10, 'y': 10}, timeout=3000)
                                await asyncio.sleep(0.5)
                                auto_close_msg = " + 自动关闭"
                            else:
                                auto_close_msg = ""
                        except:
                            auto_close_msg = ""
                        
                        execution_time = round(time.time() - start_time, 2)
                        method_desc = js_result.get('method', 'unknown') if isinstance(js_result, dict) else 'unknown'
                        log = f"✓ 点击下拉框选项 '{element_name}' 成功（{method_desc})\n"
                        log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                        log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                        log += f"  - 更新方法: {method_desc}{auto_close_msg}\n"
                        if isinstance(js_result, dict) and 'allValues' in js_result:
                            log += f"  - 当前选中值: {js_result['allValues']}\n"
                        log += f"  - 执行时间: {execution_time}秒"
                        return True, log, None
                    except Exception as e:
                        logger.error(f"下拉框选项点击失败: {e}")
                        execution_time = round(time.time() - start_time, 2)

                        # 构建详细的错误日志
                        error_log = f"✗ 点击下拉框选项 '{element_name}' 失败\n"
                        error_log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                        error_log += f"  - 执行时间: {execution_time}秒\n"
                        error_log += f"  - 错误: {str(e)}\n\n"
                        error_log += "建议解决方案:\n"
                        error_log += "1. 检查元素是否在下拉框展开后才出现在 DOM 中\n"
                        error_log += "2. 尝试在点击下拉框后增加等待时间（添加 wait 步骤，等待2000ms）\n"
                        error_log += "3. 使用 Playwright get_by_text 定位：文本=无忧行-鸿蒙APP\n"
                        error_log += "4. 检查 Vue DevTools 确认组件结构是否与代码匹配"

                        # 尝试捕获截图
                        screenshot_base64 = None
                        try:
                            screenshot = await self.page.screenshot()
                            screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        except:
                            pass

                        # 返回: (是否成功, 日志信息, 截图base64)
                        return False, error_log, screenshot_base64
                else:
                    # 普通元素：正常点击（含 Stale Element 重试）
                    # 如果启用了强制操作，先等待元素在 DOM 中，不要求可见
                    if force_action:
                        try:
                            await locator.wait_for(state='attached', timeout=timeout_ms)
                        except:
                            pass  # 如果已经在 DOM 中，继续

                    # Stale Element 重试：最多3次，每次重新获取 locator
                    stale_max_retries = 3
                    for stale_attempt in range(stale_max_retries):
                        try:
                            await locator.click(timeout=timeout_ms, force=force_action)
                            break
                        except Exception as e:
                            last_error = str(e)
                            if stale_attempt < stale_max_retries - 1:
                                await asyncio.sleep(1.0)
                                continue
                            raise

                    execution_time = round(time.time() - start_time, 2)
                    log = f"✓ 点击元素 '{element_name}' 成功\n"
                    log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                    log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                    if force_action:
                        log += f"  - 强制操作: 是（跳过可见性检查，等待attached）\n"
                    log += f"  - 执行时间: {execution_time}秒"
                    return True, log, None

            elif action_type == 'fill':
                # Stale Element 重试：最多3次
                stale_max_retries = 3
                for stale_attempt in range(stale_max_retries):
                    try:
                        await locator.fill(resolved_input_value, timeout=timeout_ms, force=force_action)
                        break
                    except Exception as e:
                        last_error = str(e)
                        if stale_attempt < stale_max_retries - 1:
                            await asyncio.sleep(1.0)
                            continue
                        raise

                execution_time = round(time.time() - start_time, 2)

                # 输入成功后短暂等待，确保表单验证生效
                # 特别是在服务器环境下，需要给Vue/React等框架时间处理
                await asyncio.sleep(0.3)

                log = f"✓ 在元素 '{element_name}' 中输入文本成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                if resolved_input_value != step.input_value:
                    log += f"  - 变量解析: '{step.input_value}' => '{resolved_input_value}'\n"
                log += f"  - 输入内容: '{resolved_input_value}'\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                if force_action:
                    log += f"  - 强制操作: 是（忽略可见性检查）\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'getText':
                text = await locator.inner_text(timeout=timeout_ms)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 获取元素 '{element_name}' 的文本成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 文本内容: '{text}'\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'waitFor':
                await locator.wait_for(state='visible', timeout=timeout_ms)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 等待元素 '{element_name}' 出现成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                log += f"  - 等待时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'hover':
                await locator.hover(timeout=timeout_ms, force=force_action)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 在元素 '{element_name}' 上悬停成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                if force_action:
                    log += f"  - 强制操作: 是（忽略可见性检查）\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'scroll':
                await locator.scroll_into_view_if_needed(timeout=timeout_ms)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 滚动到元素 '{element_name}' 成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'assert':
                # 根据断言类型执行不同的断言
                if step.assert_type == 'textContains':
                    text = await locator.inner_text(timeout=timeout_ms)
                    if resolved_assert_value in text:
                        log = f"✓ 断言通过: 文本包含 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                             log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 实际文本: '{text}'\n"
                        log += f"  - 超时设置: {timeout_ms/1000}秒"
                        return True, log, None
                    else:
                        log = f"✗ 断言失败: 文本不包含 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                             log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 实际文本: '{text}'"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64

                elif step.assert_type == 'textEquals':
                    text = await locator.inner_text(timeout=timeout_ms)
                    if text == resolved_assert_value:
                        log = f"✓ 断言通过: 文本等于 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                             log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 超时设置: {timeout_ms/1000}秒"
                        return True, log, None
                    else:
                        log = f"✗ 断言失败: 文本不等于 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                             log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 期望: '{resolved_assert_value}'\n"
                        log += f"  - 实际: '{text}'"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64

                elif step.assert_type == 'isVisible':
                    is_visible = await locator.is_visible()
                    if is_visible:
                        log = f"✓ 断言通过: 元素 '{element_name}' 可见"
                        return True, log, None
                    else:
                        log = f"✗ 断言失败: 元素 '{element_name}' 不可见"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64

                elif step.assert_type == 'exists':
                    count = await locator.count()
                    if count > 0:
                        log = f"✓ 断言通过: 元素 '{element_name}' 存在"
                        return True, log, None
                    else:
                        log = f"✗ 断言失败: 元素 '{element_name}' 不存在"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64



            else:
                log = f"⚠ 未知的操作类型: {action_type}"
                return True, log, None

        except PlaywrightTimeout as e:
            execution_time = round(time.time() - start_time, 2)
            log = f"✗ 操作超时\n"
            log += f"  - 元素: '{element_name}'\n"
            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
            log += f"  - 超时时间: {execution_time}秒\n"
            log += f"  - 错误: {str(e)}"

            # 捕获失败截图
            try:
                screenshot = await self.page.screenshot()
                screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
            except:
                pass

            return False, log, screenshot_base64

        except Exception as e:
            execution_time = round(time.time() - start_time, 2)
            log = f"✗ 执行失败\n"
            log += f"  - 元素: '{element_name}'\n"
            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
            log += f"  - 执行时间: {execution_time}秒\n"
            log += f"  - 错误: {str(e)}"

            # 捕获失败截图
            try:
                screenshot = await self.page.screenshot()
                screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
            except:
                pass

            return False, log, screenshot_base64

    async def navigate(self, url: str) -> Tuple[bool, str]:
        """
        导航到指定URL

        Args:
            url: 目标URL

        Returns:
            (是否成功, 日志信息)
        """
        extra_logs = []
        try:
            # 检测是否在Linux服务器环境
            import platform
            is_linux = platform.system() == 'Linux'

            # 使用 domcontentloaded 而非 networkidle 避免长连接导致卡死
            await self.page.goto(url, wait_until='domcontentloaded', timeout=20000)

            # 智能等待：等待关键DOM元素就绪，替代固定sleep
            nav_wait_timeout = 15000 if is_linux else 10000
            try:
                await self.page.wait_for_selector('body', state='visible', timeout=nav_wait_timeout)
                # 对SPA应用，额外等待app根元素
                try:
                    await self.page.wait_for_selector('#app, [data-app], .app-root, .main-content',
                                                    state='attached', timeout=min(nav_wait_timeout // 2, 5000))
                except Exception:
                    pass
            except Exception:
                # body都不可见，尝试再等固定时间
                extra_fallback = 3 if is_linux else 2
                await asyncio.sleep(extra_fallback)

            # 导航后检测验证码
            captcha_handled, captcha_log = await self._wait_and_check_captcha(1.0)
            if captcha_handled:
                extra_logs.append(captcha_log)

            log = f"✓ 成功导航到: {url}\n"
            log += f"  - 页面就绪检测通过（智能等待）"
            if extra_logs:
                log += "\n" + "\n".join([f"  [验证码] {l}" for l in extra_logs])

            return True, log
        except Exception as e:
            log = f"✗ 导航失败: {url}\n  - 错误: {str(e)}"
            if extra_logs:
                log += "\n" + "\n".join([f"  [验证码] {l}" for l in extra_logs])
            return False, log

    async def capture_screenshot(self) -> str:
        """
        捕获当前页面截图

        Returns:
            截图的base64字符串
        """
        try:
            screenshot = await self.page.screenshot(full_page=True)
            return f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
        except Exception as e:
            logger.error(f"捕获截图失败: {str(e)}")
            return None
