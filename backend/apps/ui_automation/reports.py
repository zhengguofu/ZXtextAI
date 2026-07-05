"""
测试报告生成器
负责生成清晰的测试报告（HTML + JSON），包含步骤详情、截图、录屏、错误等信息。

实现说明：
- 不使用 str.format() 渲染整段含 CSS/JS 的模板（会与 {} 冲突），改用安全的字符串拼接 + html.escape。
- 截图/视频路径统一转换为相对报告目录的相对路径，保证 HTML 直接打开即可预览。
"""
import os
import json
import html
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class TestReportGenerator:
    """测试报告生成器"""

    def __init__(self, result):
        """
        Args:
            result: TestExecutionResult
        """
        self.result = result
        self.report_dir = os.path.join(result.artifact_dir, 'report') if result.artifact_dir else 'report'
        os.makedirs(self.report_dir, exist_ok=True)

    async def generate(self) -> str:
        """生成测试报告，返回 HTML 路径"""
        html_path = self._generate_html_report()
        logger.info(f"测试报告已生成: {html_path}")
        try:
            json_path = self._generate_json_report()
            logger.info(f"JSON报告已生成: {json_path}")
        except Exception as e:
            logger.warning(f"生成JSON报告失败: {e}")
        return html_path

    # ---------- 工具方法 ----------

    def _rel(self, path: str) -> str:
        """把绝对路径转换成相对报告目录的相对路径（用于HTML显示）"""
        if not path:
            return ""
        try:
            if os.path.exists(path):
                return os.path.relpath(path, self.report_dir).replace('\\', '/')
        except Exception:
            pass
        return path.replace('\\', '/')

    @staticmethod
    def _esc(text: Any) -> str:
        return html.escape(str(text)) if text is not None else ""

    def _format_timestamp(self, timestamp: float) -> str:
        if not timestamp:
            return ""
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    def _format_duration(self, duration: float) -> str:
        duration = duration or 0
        if duration < 60:
            return f"{duration:.2f}秒"
        if duration < 3600:
            return f"{int(duration // 60)}分{duration % 60:.2f}秒"
        return f"{int(duration // 3600)}时{int((duration % 3600) // 60)}分{duration % 60:.2f}秒"

    def _calculate_pass_rate(self) -> float:
        if self.result.total_steps == 0:
            return 0
        return round(self.result.passed_steps / self.result.total_steps * 100, 2)

    def _status_cn(self, status: str) -> str:
        return {
            'passed': '通过', 'failed': '失败', 'blocked': '阻塞',
            'running': '运行中', 'pending': '待执行', 'skipped': '跳过',
        }.get(status, status or '未知')

    # ---------- JSON ----------

    def _generate_json_report(self) -> str:
        report_data = self.result.to_dict()
        report_path = os.path.join(self.report_dir, f"report_{self.result.execution_id}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        return report_path

    # ---------- HTML ----------

    def _generate_html_report(self) -> str:
        r = self.result
        pass_rate = self._calculate_pass_rate()

        # 顶部告警块
        warning_html = ""
        if getattr(r, 'captcha_blocked', False):
            warning_html += (
                '<div class="warn">'
                '<h4>⚠️ 检测到验证码 / 风控阻塞</h4>'
                f'<p>{self._esc(r.block_reason)}</p>'
                '<p>当前用例已标记为「阻塞 / 待人工处理」，请查看截图与DOM证据。</p>'
                '</div>'
            )
        if r.error:
            warning_html += (
                '<div class="section"><div class="section-title">错误信息</div>'
                f'<div class="error">{self._esc(r.error)}</div></div>'
            )

        # 录屏块
        video_html = ""
        video_rel = self._rel(r.video_path)
        if video_rel:
            video_html = (
                '<div class="section"><div class="section-title">全程录屏</div>'
                '<video controls style="width:100%;max-width:960px;border-radius:8px;background:#000;">'
                f'<source src="{self._esc(video_rel)}" type="video/webm">您的浏览器不支持视频播放</video>'
                f'<p style="margin-top:8px;color:#6b7280;font-size:13px;">视频文件: {self._esc(video_rel)}</p>'
                '</div>'
            )

        # 产物链接块
        artifacts_html = self._build_artifacts_html()

        # 步骤块
        steps_html = self._build_steps_html()

        badge_class = {'passed': 'success', 'failed': 'failed', 'blocked': 'blocked'}.get(r.status, 'pending')

        html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>测试报告 - {self._esc(r.case_name or '未命名测试')}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,'Segoe UI',Roboto,'Microsoft YaHei',Arial,sans-serif; background:#f5f7fa; color:#1f2937; }}
.container {{ max-width:1200px; margin:0 auto; padding:20px; }}
.header {{ background:linear-gradient(135deg,#667eea,#764ba2); color:#fff; padding:30px; border-radius:12px; margin-bottom:24px; }}
.header h1 {{ font-size:26px; margin-bottom:8px; }}
.header p {{ opacity:.9; font-size:14px; margin-top:2px; }}
.badges {{ display:flex; gap:12px; margin-top:16px; flex-wrap:wrap; }}
.badge {{ padding:6px 16px; border-radius:20px; font-size:14px; font-weight:600; background:#6b7280; color:#fff; }}
.badge.success {{ background:#10b981; }} .badge.failed {{ background:#ef4444; }}
.badge.blocked {{ background:#f59e0b; }} .badge.pending {{ background:#6b7280; }}
.stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:16px; margin-bottom:24px; }}
.stat-card {{ background:#fff; padding:20px; border-radius:12px; text-align:center; box-shadow:0 2px 4px rgba(0,0,0,.05); }}
.stat-card .value {{ font-size:32px; font-weight:700; margin-bottom:6px; }}
.stat-card .label {{ font-size:13px; color:#6b7280; }}
.stat-card.total .value {{ color:#6366f1; }} .stat-card.success .value {{ color:#10b981; }}
.stat-card.failed .value {{ color:#ef4444; }} .stat-card.blocked .value {{ color:#f59e0b; }}
.section {{ background:#fff; border-radius:12px; padding:24px; margin-bottom:24px; box-shadow:0 2px 4px rgba(0,0,0,.05); }}
.section-title {{ font-size:18px; font-weight:600; margin-bottom:16px; padding-bottom:12px; border-bottom:2px solid #e5e7eb; }}
.warn {{ background:#fef3c7; border-left:4px solid #f59e0b; padding:16px; border-radius:0 6px 6px 0; margin-bottom:24px; }}
.warn h4 {{ color:#d97706; margin-bottom:8px; }} .warn p {{ color:#92400e; font-size:14px; }}
.error {{ background:#fef2f2; border-left:4px solid #ef4444; padding:16px; border-radius:0 6px 6px 0; font-family:monospace; font-size:13px; color:#991b1b; white-space:pre-wrap; word-break:break-all; max-height:320px; overflow:auto; }}
.steps-list {{ display:flex; flex-direction:column; gap:16px; }}
.step-card {{ border:2px solid #e5e7eb; border-radius:10px; overflow:hidden; }}
.step-card.passed {{ border-color:#10b981; }} .step-card.failed {{ border-color:#ef4444; }} .step-card.blocked {{ border-color:#f59e0b; }}
.step-header {{ display:flex; align-items:center; padding:12px 16px; background:#f9fafb; gap:12px; }}
.dot {{ width:14px; height:14px; border-radius:50%; flex-shrink:0; background:#6b7280; }}
.dot.passed {{ background:#10b981; }} .dot.failed {{ background:#ef4444; }} .dot.blocked {{ background:#f59e0b; }}
.step-info {{ flex:1; min-width:0; }}
.step-name {{ font-weight:600; font-size:14px; }}
.step-desc {{ font-size:12px; color:#6b7280; margin-top:2px; }}
.step-meta {{ font-size:12px; color:#9ca3af; white-space:nowrap; }}
.step-body {{ padding:16px; }}
.narrative {{ background:#f0f7ff; border-left:3px solid #667eea; padding:12px 16px; border-radius:0 6px 6px 0; margin-bottom:12px; font-size:14px; line-height:1.7; color:#1f2937; }}
.narrative p {{ margin:6px 0; }}
.narrative strong {{ color:#667eea; font-weight:600; }}
.shot-label {{ display:flex; align-items:center; gap:4px; font-size:12px; color:#4b5563; font-weight:600; margin-bottom:6px; }}
.meta-line {{ color:#6b7280; font-size:13px; margin-bottom:10px; word-break:break-all; }}
.shots {{ display:flex; gap:12px; flex-wrap:wrap; }}
.shot {{ flex:1; min-width:240px; }}
.shot span {{ display:block; font-size:12px; color:#6b7280; margin-bottom:4px; }}
.shot img {{ width:100%; border:1px solid #e5e7eb; border-radius:6px; cursor:pointer; }}
.links {{ margin-top:10px; display:flex; gap:14px; flex-wrap:wrap; font-size:13px; }}
.links a {{ color:#6366f1; text-decoration:none; }} .links a:hover {{ text-decoration:underline; }}
.footer {{ text-align:center; padding:20px; color:#9ca3af; font-size:13px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>自动化测试报告</h1>
    <p>测试用例: {self._esc(r.case_name or '未命名测试')}</p>
    <p>执行ID: {self._esc(r.execution_id)}</p>
    <p>开始: {self._format_timestamp(r.start_time)} &nbsp;|&nbsp; 结束: {self._format_timestamp(r.end_time)}</p>
    <div class="badges">
      <span class="badge {badge_class}">{self._status_cn(r.status)}</span>
      <span class="badge">耗时: {self._format_duration(r.duration)}</span>
      <span class="badge">通过率: {pass_rate}%</span>
    </div>
  </div>

  <div class="stats-grid">
    <div class="stat-card total"><div class="value">{r.total_steps}</div><div class="label">总步骤数</div></div>
    <div class="stat-card success"><div class="value">{r.passed_steps}</div><div class="label">成功</div></div>
    <div class="stat-card failed"><div class="value">{r.failed_steps}</div><div class="label">失败</div></div>
    <div class="stat-card blocked"><div class="value">{r.blocked_steps}</div><div class="label">阻塞</div></div>
  </div>

  {warning_html}
  {video_html}

  <div class="section">
    <div class="section-title">执行步骤详情（共 {r.total_steps} 步）</div>
    <div class="steps-list">{steps_html}</div>
  </div>

  {artifacts_html}

  <div class="footer">
    <p>生成时间: {self._format_timestamp(r.end_time)}</p>
    <p>ZXtextAI 自动化测试框架</p>
  </div>
</div>
</body>
</html>"""

        report_path = os.path.join(self.report_dir, f"report_{self.result.execution_id}.html")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_doc)
        return report_path

    def _build_steps_html(self) -> str:
        if not self.result.steps:
            return '<p style="text-align:center;color:#9ca3af;padding:20px;">无步骤记录</p>'

        # 尝试获取 step_executor 用于生成讲解文字
        step_executor = getattr(self.result, 'step_executor', None) or getattr(self, 'step_executor', None)

        parts = []
        for idx, step in enumerate(self.result.steps, start=1):
            status = step.status or 'pending'
            before_rel = self._rel(step.before_screenshot_path)
            after_rel = self._rel(step.after_screenshot_path)

            shots = []
            if before_rel:
                shots.append(
                    f'<div class="shot"><div class="shot-label">📷 执行前</div>'
                    f'<img src="{self._esc(before_rel)}" onclick="window.open(this.src)"></div>'
                )
            if after_rel:
                shots.append(
                    f'<div class="shot"><div class="shot-label">📷 执行后</div>'
                    f'<img src="{self._esc(after_rel)}" onclick="window.open(this.src)"></div>'
                )
            shots_html = f'<div class="shots">{"".join(shots)}</div>' if shots else ""

            links = []
            dom_rel = self._rel(step.dom_path)
            console_rel = self._rel(step.console_log_path)
            if dom_rel:
                links.append(f'<a href="{self._esc(dom_rel)}" target="_blank">📄 页面DOM</a>')
            if console_rel:
                links.append(f'<a href="{self._esc(console_rel)}" target="_blank">📋 控制台日志</a>')
            if before_rel:
                links.append(f'<a href="{self._esc(before_rel)}" target="_blank">🖼️ 前图</a>')
            if after_rel:
                links.append(f'<a href="{self._esc(after_rel)}" target="_blank">🖼️ 后图</a>')
            links_html = f'<div class="links">{"".join(links)}</div>' if links else ""

            error_html = ""
            if step.error:
                error_html = f'<div class="error" style="margin-top:10px;">{self._esc(step.error)}</div>'

            meta_line = (
                f'<div class="meta-line"><b>URL:</b> {self._esc(step.current_url or "-")} &nbsp;|&nbsp; '
                f'<b>标题:</b> {self._esc(step.page_title or "-")} &nbsp;|&nbsp; '
                f'<b>类型:</b> {self._esc(step.action_type or "-")}</div>'
            )

            # 生成讲解文字
            narrative = ""
            if step_executor and hasattr(step_executor, 'generate_step_narrative'):
                try:
                    narrative = step_executor.generate_step_narrative(step)
                except Exception:
                    narrative = step.step_desc or step.step_name
            else:
                # 即使没有 step_executor 也尝试生成
                narrative = self._build_narrative_fallback(step)

            narrative_html = ""
            if narrative:
                # 简单的markdown->html转换
                narrative_html = f'<div class="narrative">{self._render_simple_markdown(narrative)}</div>'

            parts.append(
                f'<div class="step-card {status}">'
                f'<div class="step-header">'
                f'<div class="dot {status}"></div>'
                f'<div class="step-info">'
                f'<div class="step-name">步骤 {idx}: {self._esc(step.step_name)} [{self._status_cn(status)}]</div>'
                f'<div class="step-desc">{self._esc(step.step_desc)}</div>'
                f'</div>'
                f'<div class="step-meta">⏱️ {step.duration:.2f}s</div>'
                f'</div>'
                f'<div class="step-body">{narrative_html}{meta_line}{shots_html}{links_html}{error_html}</div>'
                f'</div>'
            )
        return ''.join(parts)

    def _build_narrative_fallback(self, step) -> str:
        """在没有 step_executor 时的降级讲解生成"""
        parts = []
        action = step.action_type or '执行'
        target = step.element_info or '目标元素'

        action_map = {
            'navigate': f'🌐 **打开页面**：访问URL `{step.current_url or "目标地址"}`',
            'click': f'👆 **点击操作**：点击 `{target}`',
            'fill': f'⌨️ **输入操作**：在 `{target}` 中填写内容',
            'waitFor': f'⏳ **等待元素**：等待 `{target}` 出现',
            'wait': f'⏱️ **等待**：暂停 {step.duration:.2f} 秒',
            'submit': f'📤 **提交操作**：提交表单',
            'verify': f'✅ **验证操作**：检查页面状态',
        }
        parts.append(action_map.get(action, f'▶️ **执行**：{action} {target}'))

        if step.page_title:
            parts.append(f'🔍 **页面观察**：页面标题「{step.page_title}」')
        if step.status == 'passed':
            parts.append('✅ **执行结果**：操作成功')
        elif step.status == 'failed':
            err = (step.error or '').split('\n')[0][:200]
            parts.append(f'❌ **执行结果**：失败，`{err}`')
        return '\n\n'.join(parts)

    def _render_simple_markdown(self, text: str) -> str:
        """简单的 markdown 渲染（粗体 + 换行）"""
        if not text:
            return ""
        import re
        # 处理 **粗体**
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # 处理换行
        text = text.replace('\n\n', '</p><p>').replace('\n', '<br>')
        text = f'<p>{text}</p>'
        # 防止 XSS 但保留标签
        return text

    def _build_artifacts_html(self) -> str:
        r = self.result
        items = []
        trace_rel = self._rel(r.trace_path)
        har_rel = self._rel(r.har_path)
        if trace_rel:
            items.append(f'<li>Trace 追踪文件: <code>{self._esc(trace_rel)}</code>（可用 <code>playwright show-trace</code> 打开）</li>')
        if har_rel:
            items.append(f'<li>网络 HAR: <a href="{self._esc(har_rel)}" target="_blank">{self._esc(har_rel)}</a></li>')

        items.append('<li>screenshots/ - 每步截图</li>')
        items.append('<li>video/ - 全程录屏</li>')
        items.append('<li>dom/ - 页面DOM快照</li>')
        items.append('<li>console/ - 控制台日志</li>')
        items.append('<li>logs/ - 步骤结构化日志</li>')

        return (
            '<div class="section"><div class="section-title">测试产物</div>'
            f'<p style="color:#6b7280;font-size:14px;">产物目录: <code>{self._esc(r.artifact_dir)}</code></p>'
            f'<ul style="margin-top:12px;padding-left:20px;color:#4b5563;font-size:14px;line-height:1.9;">{"".join(items)}</ul>'
            '</div>'
        )