import asyncio
import json
import logging
import re
from typing import Any, Dict, Iterable, Optional, Tuple

from asgiref.sync import async_to_sync

from .captcha_handler import captcha_block_reason, detect_captcha

logger = logging.getLogger(__name__)

DIAGNOSTIC_ROLES = ['browser_use_vision', 'browser_use_text', 'ai_tester', 'writer']
MAX_HTML_CHARS = 12000
MAX_CONTEXT_CHARS = 6000


def _strip_html_noise(html: str) -> str:
    text = str(html or '')
    text = re.sub(r'<(script|style|noscript)[^>]*>.*?</\\1>', ' ', text, flags=re.I | re.S)
    text = re.sub(r'<!--.*?-->', ' ', text, flags=re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\\s+', ' ', text).strip()
    return text[:MAX_HTML_CHARS]


def _trim(value: Any, limit: int = MAX_CONTEXT_CHARS) -> str:
    text = str(value or '').strip()
    text = re.sub(r'\\s+', ' ', text)
    return text[:limit]


def _extract_ai_content(response: Any) -> str:
    if isinstance(response, dict):
        choices = response.get('choices') or []
        if choices:
            message = choices[0].get('message') or {}
            content = message.get('content')
            if content:
                return str(content).strip()
        if response.get('content'):
            return str(response['content']).strip()
    return str(response or '').strip()


def _keyword_in(text: str, keywords) -> bool:
    return any(k and k.lower() in text for k in keywords)


def local_issue_diagnosis(
    *,
    reason: str = '',
    url: str = '',
    title: str = '',
    page_html: str = '',
    page_text: str = '',
    error_message: str = '',
    action_context: str = '',
) -> Tuple[str, Dict[str, Any]]:
    evidence_source = ' '.join([page_html or '', page_text or '', error_message or '', reason or '', title or '', action_context or ''])
    has_captcha, captcha_type = detect_captcha(evidence_source)
    lower = evidence_source.lower()

    issue_type = 'unknown_page_issue'
    suggestion = 'Inspect current page state and visible elements. If no safe recovery is possible, mark the current subtask failed.'
    handoff = 'no'
    status = 'failed'
    cause = 'The automation reached an abnormal or insufficiently understood page state.'

    if has_captcha:
        issue_type = captcha_type
        cause = captcha_block_reason(captcha_type)
        if captcha_type == 'slider_captcha':
            handoff = 'maybe'  # 自动化引擎会多次尝试
            status = 'in_progress'
            suggestion = (
                '自动化引擎已尝试最多3次拟人化拖动。如果滑块仍然存在，'
                '建议调用 handle_verification_barrier 让引擎再次尝试。'
                '只有所有尝试均失败后才标记 skipped。'
            )
        elif captcha_type == 'text_captcha':
            handoff = 'maybe'  # OCR会尝试识别
            status = 'in_progress'
            suggestion = (
                '自动化引擎将尝试OCR识别图形验证码。'
                '如果OCR失败，建议刷新验证码后再次尝试。'
                '只有多次尝试失败后才标记 skipped。'
            )
        elif captcha_type in ('click_captcha',):
            handoff = 'maybe'
            status = 'in_progress'
            suggestion = (
                '检测到点选验证码。先尝试关闭弹窗遮挡，'
                '调用 handle_verification_barrier 让引擎尝试自动处理。'
                '如果持续被阻塞再标记 skipped。'
            )
        elif captcha_type in ('third_party_captcha',):
            handoff = 'yes'
            status = 'skipped'
            suggestion = '第三方人机验证（reCAPTCHA/Cloudflare等）无法自动绕过，需要人工完成验证。'
        elif captcha_type == 'sms_verify':
            handoff = 'yes'
            status = 'skipped'
            suggestion = '短信/手机验证码需要人工输入动态码，自动化无法完成。'
        else:
            handoff = 'maybe'
            status = 'in_progress'
            suggestion = (
                '检测到通用验证码。调用 handle_verification_barrier 让自动化引擎尝试处理。'
                '请勿在引擎尝试前直接跳过。'
            )
    elif _keyword_in(lower, ['timeout', 'timed out', 'net::err', 'navigation failed', 'load failed']):
        issue_type = 'page_load_timeout_or_network'
        cause = 'Page load or network request timed out or failed.'
        suggestion = 'Refresh once and verify URL. If it still fails, mark current subtask failed and keep logs.'
    elif _keyword_in(lower, ['404', '500', '502', '503', 'error page', 'server error', 'maintenance']):
        issue_type = 'server_or_error_page'
        cause = 'Target page shows server error or maintenance state.'
        suggestion = 'Log current URL and error evidence, then mark current subtask failed.'
    elif _keyword_in(lower, ['login failed', 'invalid credentials', 'incorrect password', 'unauthorized', 'forbidden']):
        issue_type = 'auth_failure'
        cause = 'Authentication failed or permission is insufficient.'
        suggestion = 'Do not invent credentials. Retry only with provided credentials, then mark failed.'
    elif _keyword_in(lower, ['element', 'selector', 'not found', 'strict mode violation', 'not visible', 'detached']):
        issue_type = 'element_not_found'
        cause = 'Target element is missing, hidden, blocked by overlay, or page state differs from expectation.'
        suggestion = 'Check modal/overlay/validation messages, then re-locate by visible text, aria-label, or nearby elements.'
    elif _keyword_in(lower, ['blank', 'about:blank']):
        issue_type = 'blank_page'
        cause = 'Current tab is blank or navigation did not complete.'
        suggestion = 'Switch back to business tab or reopen target URL. If still blank, mark failed.'

    result = {
        'issue_type': issue_type,
        'evidence': _trim(' | '.join([url, title, reason, error_message, _strip_html_noise(page_html or page_text)])[:1200], 1200),
        'cause': cause,
        'recommended_action': suggestion,
        'requires_human': handoff,
        'status_suggestion': status,
        'ai_provider': 'local_fallback',
    }
    return format_diagnosis(result), result


def format_diagnosis(data: Dict[str, Any]) -> str:
    return (
        '\n[AI_DIAGNOSIS]\n'
        f"- issue_type: {data.get('issue_type') or 'unknown'}\n"
        f"- evidence: {data.get('evidence') or 'no page evidence collected'}\n"
        f"- cause: {data.get('cause') or 'unknown'}\n"
        f"- recommended_action: {data.get('recommended_action') or 'manual review'}\n"
        f"- requires_human: {data.get('requires_human') or 'unknown'}\n"
        f"- status_suggestion: {data.get('status_suggestion') or 'failed'}\n"
        f"- source: {data.get('ai_provider') or 'configured_ai'}"
    )


def parse_diagnosis_text(text: str, provider: str = 'configured_ai') -> Dict[str, Any]:
    raw = (text or '').strip()
    json_match = re.search(r'\{.*\}', raw, flags=re.S)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            if isinstance(data, dict):
                return {
                    'issue_type': data.get('issue_type') or data.get('problem_type') or data.get('type') or 'ai_diagnosed_issue',
                    'evidence': data.get('evidence') or data.get('page_evidence') or '',
                    'cause': data.get('cause') or data.get('reason') or '',
                    'recommended_action': data.get('recommended_action') or data.get('action') or '',
                    'requires_human': data.get('requires_human') or data.get('manual_handoff') or 'unknown',
                    'status_suggestion': data.get('status_suggestion') or data.get('task_status') or 'failed',
                    'ai_provider': provider,
                }
        except Exception:
            pass

    return {
        'issue_type': 'ai_diagnosed_issue',
        'evidence': _trim(raw, 1000),
        'cause': raw or 'AI returned empty diagnosis.',
        'recommended_action': 'Handle according to AI diagnosis and current test objective.',
        'requires_human': 'unknown',
        'status_suggestion': 'failed',
        'ai_provider': provider,
    }


async def diagnose_page_issue(
    *,
    reason: str = '',
    url: str = '',
    title: str = '',
    page_html: str = '',
    page_text: str = '',
    error_message: str = '',
    action_context: str = '',
    planned_tasks: Optional[Iterable[Dict[str, Any]]] = None,
    max_tokens: int = 800,
) -> Tuple[str, Dict[str, Any]]:
    visible_text = _strip_html_noise(page_html) or _trim(page_text, MAX_HTML_CHARS)
    local_log, local_data = local_issue_diagnosis(
        reason=reason,
        url=url,
        title=title,
        page_html=page_html,
        page_text=page_text,
        error_message=error_message,
        action_context=action_context,
    )

    task_context = ''
    if planned_tasks:
        task_context = json.dumps(list(planned_tasks)[:30], ensure_ascii=False, default=str)

    prompt = f'''
You are an enterprise QA automation page-issue diagnostician.
Analyze why the automation is blocked and return ONLY compact JSON.
Rules:
1. Never claim that third-party, image, SMS, or email CAPTCHA was bypassed.
2. Slider CAPTCHA may receive one normal human-like drag attempt only; if still present, recommend skipped/manual handoff.
3. Diagnose form validation, overlay blocking, element location failure, unexpected redirect, blank page, auth failure, server error, and timeout with concrete evidence.
4. JSON schema: {{"issue_type":"captcha|slider_captcha|text_captcha|sms_verify|element_not_found|form_validation|auth_failure|page_load_timeout|server_or_error_page|blank_page|unexpected_redirect|unknown", "evidence":"...", "cause":"...", "recommended_action":"...", "requires_human":"yes|no|maybe", "status_suggestion":"completed|failed|skipped|in_progress"}}

Trigger reason: {_trim(reason, 1200)}
URL: {_trim(url, 1200)}
Title: {_trim(title, 300)}
Error: {_trim(error_message, 2000)}
Action context: {_trim(action_context, 2500)}
Planned tasks: {_trim(task_context, 3000)}
Visible text / DOM summary: {_trim(visible_text, MAX_HTML_CHARS)}
Local fallback guess: {json.dumps(local_data, ensure_ascii=False)}
'''.strip()

    messages = [
        {'role': 'system', 'content': 'Return only valid JSON with ASCII keys. Be concise and auditable.'},
        {'role': 'user', 'content': prompt},
    ]

    try:
        from apps.requirement_analysis.models import AIModelService

        response, config = await AIModelService.call_with_auto_model_from_roles(
            DIAGNOSTIC_ROLES,
            messages,
            max_tokens=max_tokens,
        )
        provider = f"{getattr(config, 'role', 'ai')}:{getattr(config, 'name', '') or getattr(config, 'model_name', '')}"
        data = parse_diagnosis_text(_extract_ai_content(response), provider=provider)
        return format_diagnosis(data), data
    except Exception as exc:
        logger.warning('AI page diagnosis failed, using local fallback: %s', exc)
        local_data['ai_provider'] = f"local_fallback(ai_unavailable: {_trim(exc, 180)})"
        return format_diagnosis(local_data), local_data


def diagnose_page_issue_sync(**kwargs) -> Tuple[str, Dict[str, Any]]:
    try:
        return async_to_sync(diagnose_page_issue)(**kwargs)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(diagnose_page_issue(**kwargs))
        finally:
            loop.close()
