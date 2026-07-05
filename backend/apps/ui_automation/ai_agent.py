import logging
import asyncio
from .ai_base import BaseBrowserAgent

logger = logging.getLogger('django')

class BrowserAgent(BaseBrowserAgent):
    """
    Standard Browser Agent for Text Mode.
    Inherits all base functionality without applying dangerous visual patches.
    """
    def __init__(self, execution_mode='text', enable_gif=True, case_name=None, headless=None):
        self.enable_gif = enable_gif
        self.case_name = case_name or "Adhoc Task"
        super().__init__(execution_mode=execution_mode, enable_gif=enable_gif, case_name=case_name, headless=headless)

# ============================================================================
# EXPORTED FUNCTIONS (FACTORY)
# ============================================================================

def get_agent_class(execution_mode='text'):
    # 始终返回文本模式实现
    return BrowserAgent

def run_ai_task_sync(task_description: str, planned_tasks=None, callback=None, should_stop=None, execution_mode='text', headless=None):
    agent = BrowserAgent(execution_mode=execution_mode, headless=headless)
    return asyncio.run(agent.run_task(task_description, planned_tasks, callback, should_stop))
    
def analyze_task_sync(task_description: str, execution_mode='text', headless=None):
    agent = BrowserAgent(execution_mode=execution_mode, headless=headless)
    return asyncio.run(agent.analyze_task(task_description))

def run_full_process_sync(task_description: str, analysis_callback=None, step_callback=None, should_stop=None, execution_mode='text', enable_gif=True, case_name=None, url: str = None, custom_headers: list = None, testcase_callback=None, headless=None):
    logger.info(f"DEBUG: Entering run_full_process_sync with execution_mode={execution_mode}, enable_gif={enable_gif}, url={url}, headless={headless}")
    
    async def _run():
        agent = BrowserAgent(execution_mode=execution_mode, enable_gif=enable_gif, case_name=case_name, headless=headless)
        logger.info(f"DEBUG: Agent created successfully ({type(agent).__name__}), starting run_full_process")
        return await agent.run_full_process(
            task_description=task_description,
            analysis_callback=analysis_callback,
            step_callback=step_callback,
            should_stop=should_stop,
            url=url,
            custom_headers=custom_headers,
            testcase_callback=testcase_callback,
        )
    
    try:
        return asyncio.run(asyncio.wait_for(_run(), timeout=600))
    except asyncio.TimeoutError:
        raise Exception("任务执行超时（超过10分钟）")
