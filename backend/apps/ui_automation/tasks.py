"""
UI自动化测试 - Celery 异步任务
功能：
1. 后台执行自动化测试（用户离开页面也不中断）
2. 断点续跑（异常中断后保留进度，可一键恢复）
3. 批量执行
4. 需求评审生成用例 -> 一键执行

执行内核复用 test_executor.TestExecutor（全异步 Playwright），
步骤来自数据库 ExecutionStep 定义，执行过程逐步截图/录屏/落库。
"""
import logging
import traceback
from django.utils import timezone
from asgiref.sync import async_to_sync
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

logger = logging.getLogger(__name__)


def _import_models():
    from .models import AutomationExecution, ExecutionStep, ExecutionEvidence, ExecutionLog
    return AutomationExecution, ExecutionStep, ExecutionEvidence, ExecutionLog


def _log(execution, level, message):
    """写执行日志（落库 + logger）"""
    try:
        from .models import ExecutionLog
        ExecutionLog.objects.create(execution=execution, log_level=level, message=message)
    except Exception:
        pass
    getattr(logger, level if level in ('debug', 'info', 'warning', 'error') else 'info')(
        f"[{execution.task_id}] {message}"
    )


def _build_test_func(execution, resume_from: int = 0):
    """
    根据数据库中的步骤定义，构建一个异步测试函数。
    每个步骤通过 StepExecutor 统一执行，执行后把结果回写到 ExecutionStep。
    """
    from .models import ExecutionStep

    # 预读步骤定义（在同步上下文）
    db_steps = list(ExecutionStep.objects.filter(execution=execution).order_by('step_index'))

    async def test_func(step_executor):
        from asgiref.sync import sync_to_async

        for db_step in db_steps:
            if db_step.step_index < resume_from:
                continue  # 跳过已执行步骤（续跑）

            action_type = (db_step.action_type or '').strip().lower()
            target = ''
            value = ''
            # steps_definition 中可能带 target/value
            try:
                defs = execution.steps_definition or []
                if isinstance(defs, list) and db_step.step_index < len(defs):
                    d = defs[db_step.step_index] or {}
                    target = d.get('target', '') or d.get('selector', '') or d.get('url', '')
                    value = d.get('value', '') or d.get('text', '')
            except Exception:
                pass

            desc = db_step.step_desc or db_step.step_name

            # 根据动作类型分派到 StepExecutor 的对应方法
            if action_type in ('goto', 'navigate', 'open'):
                result = await step_executor.goto(target, step_desc=desc)
            elif action_type == 'click':
                result = await step_executor.click(step_executor.page.locator(target), step_desc=desc, element_name=target)
            elif action_type in ('fill', 'input'):
                result = await step_executor.fill(step_executor.page.locator(target), value, step_desc=desc, element_name=target)
            elif action_type == 'wait_selector':
                result = await step_executor.wait_for_selector(target, step_desc=desc)
            elif action_type == 'wait':
                ms = int(value) if str(value).isdigit() else 1000
                result = await step_executor.wait_for_timeout(ms, step_desc=desc)
            elif action_type == 'press':
                result = await step_executor.press(value or target or 'Enter', step_desc=desc)
            elif action_type in ('assert_text', 'assert_text_contains'):
                result = await step_executor.assert_text_contains(step_executor.page.locator(target), value, step_desc=desc)
            elif action_type in ('assert_title', 'assert_title_contains'):
                result = await step_executor.assert_title_contains(value or target, step_desc=desc)
            elif action_type in ('assert_url', 'assert_url_contains'):
                result = await step_executor.assert_url_contains(value or target, step_desc=desc)
            elif action_type == 'screenshot':
                result = await step_executor.execute_step("截图", lambda: step_executor.page.wait_for_timeout(100), step_desc=desc, action_type='screenshot')
            else:
                # 默认：等待+截图，保证每步都有证据
                result = await step_executor.execute_step(
                    db_step.step_name,
                    lambda: step_executor.page.wait_for_timeout(300),
                    step_desc=desc,
                    action_type=action_type or 'custom',
                )

            # 回写步骤结果到数据库
            await sync_to_async(_persist_step_result, thread_sensitive=True)(
                execution, db_step, result
            )

    return test_func


def _persist_step_result(execution, db_step, result):
    """把 StepResult 回写到 ExecutionStep + 更新执行断点"""
    from datetime import datetime
    db_step.status = result.status
    db_step.action_type = result.action_type or db_step.action_type
    db_step.url = (result.current_url or '')[:1000]
    db_step.page_title = (result.page_title or '')[:500]
    db_step.screenshot_before = result.before_screenshot_path or ''
    db_step.screenshot_after = result.after_screenshot_path or ''
    db_step.dom_path = result.dom_path or ''
    db_step.console_log_path = result.console_log_path or ''
    db_step.error_message = result.error or ''
    db_step.duration = result.duration
    if result.start_time:
        db_step.started_at = timezone.make_aware(datetime.fromtimestamp(result.start_time))
    if result.end_time:
        db_step.completed_at = timezone.make_aware(datetime.fromtimestamp(result.end_time))
    db_step.save()

    # 更新断点位置
    execution.current_step_index = db_step.step_index + 1
    execution.last_executed_step_id = db_step.step_id
    execution.save(update_fields=['current_step_index', 'last_executed_step_id', 'updated_at'])


def _run_execution(execution, resume_from: int = 0):
    """同步入口：构建测试函数并通过 TestExecutor 执行"""
    from .test_executor import run_test_async

    test_func = _build_test_func(execution, resume_from=resume_from)

    result = async_to_sync(run_test_async)(
        execution.case_name,
        test_func,
        browser_type=execution.browser_type or 'chromium',
        headless=execution.headless,
        execution_id=execution.task_id,
        resume_from_step=resume_from,
    )
    return result


def _apply_result(execution, result):
    """把整体执行结果写回 AutomationExecution"""
    execution.status = result.status
    execution.completed_at = timezone.now()
    execution.duration = result.duration
    execution.total_steps = result.total_steps
    execution.passed_steps = result.passed_steps
    execution.failed_steps = result.failed_steps
    execution.artifact_dir = result.artifact_dir or execution.artifact_dir
    execution.video_path = result.video_path or ''
    execution.report_path = result.report_path or ''
    execution.trace_path = getattr(result, 'trace_path', '') or ''
    execution.har_path = getattr(result, 'har_path', '') or ''
    if result.captcha_blocked:
        execution.status = 'blocked'
        execution.blocking_reason = result.block_reason or '检测到验证码/风控阻塞'
    if result.error:
        execution.error_message = result.error
    # 阻塞或失败时允许续跑
    execution.can_resume = result.status in ('failed', 'blocked', 'interrupted')
    execution.save()

    # 同步证据记录
    _sync_evidences(execution, result)


def _sync_evidences(execution, result):
    """把产物登记到 ExecutionEvidence，方便前端检索"""
    import os
    from .models import ExecutionEvidence

    def add(ev_type, path):
        if path and os.path.exists(path):
            ExecutionEvidence.objects.create(
                execution=execution,
                evidence_type=ev_type,
                file_path=path,
                file_name=os.path.basename(path),
            )

    add('video', result.video_path)
    add('report', result.report_path)
    add('trace', getattr(result, 'trace_path', ''))
    add('har', getattr(result, 'har_path', ''))


@shared_task(bind=True, soft_time_limit=3600, time_limit=7200)
def run_automation_test(self, execution_id: str):
    """执行自动化测试任务（后台）"""
    AutomationExecution, _, _, _ = _import_models()
    try:
        execution = AutomationExecution.objects.get(task_id=execution_id)
    except AutomationExecution.DoesNotExist:
        logger.error(f"执行记录不存在: {execution_id}")
        return 'not_found'

    try:
        execution.status = 'running'
        execution.started_at = timezone.now()
        execution.celery_task_id = self.request.id or ''
        execution.save()
        _log(execution, 'info', f"开始执行自动化测试: {execution.case_name}")

        result = _run_execution(execution, resume_from=0)
        _apply_result(execution, result)

        _log(execution, 'info', f"测试执行完成: {execution.status}, 耗时: {execution.duration or 0:.2f}秒")
        return execution.status

    except SoftTimeLimitExceeded:
        execution.refresh_from_db()
        execution.status = 'interrupted'
        execution.can_resume = True
        execution.error_message = '测试执行超时，已中断（可恢复续跑）'
        execution.save()
        _log(execution, 'error', '测试执行超时，已中断')
        return 'interrupted'

    except Exception as e:
        try:
            execution.refresh_from_db()
            execution.status = 'failed'
            execution.can_resume = True
            execution.error_message = f"{e}\n{traceback.format_exc()}"
            execution.save()
            _log(execution, 'error', f"测试执行失败: {e}")
        except Exception:
            logger.error(f"执行失败且回写异常: {e}")
        return 'failed'


@shared_task(bind=True, soft_time_limit=3600, time_limit=7200)
def resume_automation_test(self, execution_id: str):
    """恢复中断的自动化测试（从断点续跑）"""
    AutomationExecution, _, _, _ = _import_models()
    try:
        execution = AutomationExecution.objects.get(task_id=execution_id)
    except AutomationExecution.DoesNotExist:
        return 'not_found'

    if not execution.can_resume:
        _log(execution, 'warning', '该任务不可恢复')
        return 'cannot_resume'

    try:
        resume_from = execution.current_step_index or 0
        execution.status = 'running'
        execution.celery_task_id = self.request.id or ''
        execution.save()
        _log(execution, 'info', f"恢复执行，从步骤 {resume_from} 开始")

        result = _run_execution(execution, resume_from=resume_from)
        _apply_result(execution, result)
        _log(execution, 'info', f"恢复执行完成: {execution.status}")
        return execution.status

    except Exception as e:
        execution.refresh_from_db()
        execution.status = 'failed'
        execution.can_resume = True
        execution.error_message = f"{e}\n{traceback.format_exc()}"
        execution.save()
        _log(execution, 'error', f"恢复执行失败: {e}")
        return 'failed'


@shared_task(bind=True)
def run_batch_test(self, execution_ids: list):
    """批量执行（逐个派发到 worker）"""
    results = []
    for execution_id in execution_ids:
        try:
            async_result = run_automation_test.apply_async(args=[execution_id])
            results.append({'execution_id': execution_id, 'celery_task_id': async_result.id, 'status': 'queued'})
        except Exception as e:
            results.append({'execution_id': execution_id, 'error': str(e)})
    return results


@shared_task(bind=True, soft_time_limit=7200, time_limit=14400)
def run_generated_testcases(self, generated_case_ids: list, project_id=None,
                            target_url: str = '', browser_type: str = 'chromium', headless: bool = True):
    """
    执行需求评审生成的测试用例（一键执行）
    为每个用例创建 AutomationExecution + 解析步骤，然后派发执行。
    """
    from .models import AutomationExecution, ExecutionStep
    from apps.requirement_analysis.models import GeneratedTestCase

    results = []
    for case_id in generated_case_ids:
        try:
            gen = GeneratedTestCase.objects.select_related(
                'requirement__analysis__document__uploaded_by'
            ).get(id=case_id)

            creator = gen.requirement.analysis.document.uploaded_by

            execution = AutomationExecution.objects.create(
                task_id=f"gen_{case_id}_{int(timezone.now().timestamp())}",
                case_name=gen.title[:200],
                description=gen.precondition or '',
                source_type='requirement',
                source_id=str(case_id),
                generated_testcase=gen,
                project_id=project_id,
                target_url=target_url or '',
                browser_type=browser_type,
                headless=headless,
                status='pending',
                execution_mode='single',
                created_by=creator,
            )

            steps = parse_test_steps(gen.test_steps, target_url=target_url)
            execution.total_steps = len(steps)
            execution.steps_definition = steps
            execution.save()

            for i, step in enumerate(steps):
                ExecutionStep.objects.create(
                    execution=execution,
                    step_id=f"step_{i+1}",
                    step_name=step.get('desc', f'步骤{i+1}')[:200],
                    step_desc=step.get('desc', ''),
                    step_index=i,
                    action_type=step.get('action_type', 'custom'),
                )

            async_result = run_automation_test.apply_async(args=[execution.task_id])

            # 更新生成用例状态为已采纳
            gen.status = 'adopted'
            gen.save(update_fields=['status', 'updated_at'])

            results.append({
                'case_id': case_id,
                'execution_id': execution.task_id,
                'celery_task_id': async_result.id,
                'status': 'queued',
            })
        except Exception as e:
            results.append({'case_id': case_id, 'error': str(e)})

    return results


def parse_test_steps(test_steps_text: str, target_url: str = '') -> list:
    """
    把测试用例的文本步骤解析为结构化步骤列表。
    若提供 target_url，则自动在首位插入一个打开页面的步骤。
    返回: [{'action_type': 'goto'|'custom'|..., 'target': '', 'value': '', 'desc': ''}]
    """
    steps = []

    if target_url:
        steps.append({'action_type': 'goto', 'target': target_url, 'value': '', 'desc': f'打开页面: {target_url}'})

    if not test_steps_text:
        return steps

    import re
    lines = [ln.strip() for ln in str(test_steps_text).replace('\r', '\n').split('\n') if ln.strip()]

    for line in lines:
        # 去掉前导编号: "1." "1)" "- " "步骤1:" 等
        content = re.sub(r'^\s*(?:步骤\s*)?\d+\s*[\.\)、:：]\s*', '', line)
        content = re.sub(r'^\s*[-*•]\s*', '', content)
        if not content:
            continue
        # 跳过纯"预期结果"行（作为上一步描述补充）
        steps.append({
            'action_type': 'custom',
            'target': '',
            'value': '',
            'desc': content[:500],
        })

    return steps