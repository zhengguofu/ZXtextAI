"""
ZXtextAI UI自动化测试模块

核心组件（按需从子模块导入，避免在 app 加载时强依赖 playwright）：
- step_executor.StepExecutor: 统一步骤执行器（全异步）
- test_executor.TestExecutor / run_test_async: 测试执行器
- artifact_manager.ArtifactManager: 产物管理器
- captcha_detector.CaptchaDetector: 验证码/风控检测器
- reports.TestReportGenerator: 报告生成器

使用示例：
    from apps.ui_automation.test_executor import run_test_async

    async def my_test(step):
        await step.goto("https://example.com")
        await step.click(step.page.locator("button"))

    result = await run_test_async("示例", my_test, headless=True)
"""

__version__ = "1.0.0"