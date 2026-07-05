"""
自动化测试示例 / 本地验证脚本（不依赖 Django）

直接运行可验证：截图、录屏、DOM、报告是否真实生成。
用法（在项目根目录）：
    python -m apps.ui_automation.example_test
或：
    python apps/ui_automation/example_test.py

注意：需先执行 `playwright install chromium` 安装浏览器内核。
"""
import os
import sys
import asyncio

# 允许直接以脚本方式运行（把项目根加入 sys.path）
_CUR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_CUR, '..', '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from apps.ui_automation.test_executor import run_test_async  # noqa: E402


async def demo_test(step):
    """演示：打开示例站点，断言标题，截图、获取文本。"""
    await step.goto("https://example.com", step_desc="打开 example.com 首页")
    await step.assert_title_contains("Example", step_desc="断言标题包含 Example")
    await step.wait_for_selector("h1", step_desc="等待 h1 标题出现")
    await step.assert_text_contains(
        step.page.locator("h1"), "Example Domain", step_desc="断言 h1 文本"
    )
    await step.wait_for_timeout(500, step_desc="停留 0.5 秒以便录屏")


async def main():
    print("===== 开始运行自动化测试验证 =====")
    result = await run_test_async(
        "示例站点验证", demo_test, browser_type="chromium", headless=True
    )

    print("\n========== 执行结果 ==========")
    print(f"执行ID  : {result.execution_id}")
    print(f"状态    : {result.status}")
    print(f"总步骤  : {result.total_steps}  通过: {result.passed_steps}  失败: {result.failed_steps}")
    print(f"耗时    : {result.duration:.2f}s")
    print(f"产物目录: {result.artifact_dir}")
    print(f"视频    : {result.video_path}")
    print(f"报告    : {result.report_path}")
    print(f"Trace   : {result.trace_path}")
    print(f"HAR     : {result.har_path}")

    # 校验产物真实存在
    print("\n========== 产物校验 ==========")
    shots_dir = os.path.join(result.artifact_dir, 'screenshots')
    shots = os.listdir(shots_dir) if os.path.isdir(shots_dir) else []
    print(f"截图数量: {len(shots)} -> {shots[:6]}")
    print(f"视频存在: {bool(result.video_path) and os.path.exists(result.video_path)}")
    print(f"报告存在: {bool(result.report_path) and os.path.exists(result.report_path)}")
    return result


if __name__ == "__main__":
    asyncio.run(main())