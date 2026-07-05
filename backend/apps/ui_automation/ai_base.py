import logging
import sys
import io
import os

logger = logging.getLogger('django')

# Windows GBK 编码修复：通过设置环境变量而非修改 stdout/stderr 对象
# 修改 stdout/stderr 对象会导致 uvicorn 在多进程模式下出现 "I/O operation on closed file" 错误
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'

# 禁用 browser-use 遥测
os.environ['ANONYMIZED_TELEMETRY'] = 'false'

import asyncio
import functools
import json
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 加载环境变量
load_dotenv()

# ============================================================
# Windows asyncio.subprocess 修复
# ============================================================
# Windows 默认的 ProactorEventLoop 不支持 asyncio.create_subprocess_exec
# 需要切换到 SelectorEventLoop 或使用 SubprocessProtocol
# 此修复在模块加载时执行，确保 browser-use 能够正常启动浏览器
if sys.platform == 'win32':
    try:
        # 尝试设置 Windows 事件循环策略为 SelectorEventLoop
        # 这是解决 asyncio.create_subprocess_exec NotImplementedError 的关键
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logger.info("✅ Windows asyncio event loop policy set to WindowsSelectorEventLoopPolicy")
    except AttributeError:
        # Python 3.8+ 支持，旧版本可能没有此策略
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.info("✅ Windows asyncio event loop initialized")
        except Exception as e:
            logger.warning(f"⚠️ Windows asyncio event loop setup failed: {e}")

TASK_STATUS_ACTIONS = {'mark_task_complete', 'mark_task_failed', 'mark_task_skipped'}


def _normalize_action_params(action_name, action_params):
    """Normalize common LLM-generated action parameter variants to browser-use schema."""
    if isinstance(action_params, int):
        if action_name in TASK_STATUS_ACTIONS:
            return {'task_id': action_params}
        return {'index': action_params}

    if action_name == 'switch_tab' and isinstance(action_params, str) and not isinstance(action_params, dict):
        return {'tab_id': action_params}

    if not isinstance(action_params, dict):
        return action_params

    normalized_params = {}
    for key, value in action_params.items():
        normalized_key = key
        if key in {'element_index', 'element_id', 'node_id', 'id'} and action_name not in TASK_STATUS_ACTIONS:
            normalized_key = 'index'
        elif key in {'tab', 'target', 'target_id'} and action_name in {'switch_tab', 'switch'}:
            normalized_key = 'tab_id'
        elif key in {'content', 'value'} and action_name in {'input', 'input_text'}:
            normalized_key = 'text'
        normalized_params[normalized_key] = value
    return normalized_params


def _is_terminal_status_action(action_name, action_params):
    if action_name in TASK_STATUS_ACTIONS:
        return True
    if action_name != 'update_task_status' or not isinstance(action_params, dict):
        return False
    return str(action_params.get('status', '')).strip().lower() in {'completed', 'failed', 'skipped'}


def _enforce_single_task_step(actions):
    """
    Enforce single-task-per-step:
    once a terminal task status action appears, discard any later business actions.
    """
    if not isinstance(actions, list):
        return actions

    trimmed_actions = []
    terminal_seen = False
    dropped_count = 0

    for action in actions:
        if not isinstance(action, dict):
            trimmed_actions.append(action)
            continue

        if terminal_seen:
            dropped_count += 1
            continue

        trimmed_actions.append(action)
        for action_name, action_params in action.items():
            if _is_terminal_status_action(action_name, action_params):
                terminal_seen = True
                break
            if action_name == 'done':
                terminal_seen = True
                break

    if dropped_count:
        logger.warning(
            f"⚠️ Enforced single-task step boundary: dropped {dropped_count} action(s) after terminal status update"
        )

    return trimmed_actions


def _get_task_status_action_task_id(action):
    if not isinstance(action, dict):
        return None

    for action_name, action_params in action.items():
        if action_name in TASK_STATUS_ACTIONS and isinstance(action_params, dict):
            return action_params.get('task_id')
        if action_name == 'update_task_status' and isinstance(action_params, dict):
            status = str(action_params.get('status', '')).strip().lower()
            if status in {'completed', 'failed', 'skipped'}:
                return action_params.get('task_id')
    return None


def _has_real_business_action(action):
    if not isinstance(action, dict):
        return False
    return any(
        action_name not in {'mark_task_complete', 'mark_task_failed', 'mark_task_skipped', 'update_task_status', 'done'}
        for action_name in action.keys()
    )


def _extract_task_literals(task_description):
    if not task_description:
        return []

    text = str(task_description)
    literals = []
    literals.extend(re.findall(r'「([^」]+)」', text))
    literals.extend(re.findall(r'"([^"\n]+)"', text))
    literals.extend(re.findall(r"'([^'\n]+)'", text))
    literals.extend(re.findall(r'https?://[^\s]+', text))
    literals.extend(re.findall(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', text))

    deduped = []
    for item in literals:
        cleaned = str(item).strip()
        if cleaned and cleaned not in deduped:
            deduped.append(cleaned)
    return deduped


def _action_matches_pending_task(action, pending_task_description):
    if not isinstance(action, dict):
        return False

    literals = _extract_task_literals(pending_task_description)
    if not literals:
        return False

    action_payload = json.dumps(action, ensure_ascii=False)
    return any(literal in action_payload for literal in literals)


def _enforce_pending_status_settlement(actions, pending_task_id, pending_task_description=None):
    """
    If the previous step executed a task but forgot to mark it, the next step must settle
    that pending task status first and must not start the following business task in the same step.
    """
    if not pending_task_id or not isinstance(actions, list):
        return actions

    marked_pending_task = any(
        str(_get_task_status_action_task_id(action)) == str(pending_task_id)
        for action in actions
    )
    has_real_action = any(_has_real_business_action(action) for action in actions)

    if not (marked_pending_task and has_real_action):
        return actions

    real_actions = [action for action in actions if _has_real_business_action(action)]
    if pending_task_description and any(
        _action_matches_pending_task(action, pending_task_description)
        for action in real_actions
    ):
        return actions

    settled_actions = [
        action for action in actions
        if str(_get_task_status_action_task_id(action)) == str(pending_task_id)
    ]

    if settled_actions:
        logger.warning(
            f"⚠️ Settling pending task {pending_task_id} first: dropped business actions from the same step"
        )
        return settled_actions

    return actions


def _contains_auth_failure_signal(text):
    if not text:
        return False

    normalized = str(text).lower()
    keywords = [
        '登录失败', 'login failed', 'invalid credentials', 'incorrect password',
        '用户名或密码', '账号或密码', 'authentication failed', 'auth failed',
        'bad credentials', 'unauthorized', '401', '403'
    ]
    return any(keyword in normalized for keyword in keywords)

# ============================================================================
# PART 1: Common Patches (Pydantic, ActionModel, TokenCost, Basic Connection)
# ============================================================================

# Patch ChatOpenAI to allow setting attributes (required for browser-use token counting)
try:
    from pydantic import ConfigDict

    if hasattr(ChatOpenAI, 'model_config'):
        if isinstance(ChatOpenAI.model_config, dict):
            ChatOpenAI.model_config['extra'] = 'allow'
        else:
            ChatOpenAI.model_config = ConfigDict(extra='allow', arbitrary_types_allowed=True)
    else:
        ChatOpenAI.model_config = ConfigDict(extra='allow', arbitrary_types_allowed=True)
except ImportError:
    if hasattr(ChatOpenAI, 'model_config'):
        ChatOpenAI.model_config['extra'] = 'allow'

# 修改 ActionModel 配置以允许额外字段
try:
    from browser_use.tools.registry.views import ActionModel
    from pydantic import ConfigDict

    ActionModel.model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')
    logger.info("✅ Modified ActionModel.model_config to allow extra fields")
except Exception as e:
    logger.warning(f"⚠️ Failed to modify ActionModel config: {e}")

# Patch Agent.get_model_output 方法
try:
    from browser_use.agent.service import Agent
    from browser_use.agent.message_manager.service import AgentOutput
    import json as json_module

    _original_get_model_output = Agent.get_model_output


    async def _patched_get_model_output(self, input_messages):
        """修补后的 get_model_output，直接从 response.content 解析 JSON"""
        # logger.info("🔧 _patched_get_model_output called")

        if hasattr(self, '_task_was_done') and self._task_was_done:
            logger.info("🔧 Task was marked as done, stopping LLM interaction")
            raise KeyboardInterrupt("Task finished")

        kwargs = {'output_format': self.AgentOutput}

        # Add retry logic for LLM invocation with timeout
        max_retries = 2  # 重试次数为2次
        last_exception = None
        response = None
        for attempt in range(max_retries):
            try:
                # 添加超时控制，设置为60秒（支持硅基流动等大模型API的响应时间）
                response = await asyncio.wait_for(
                    self.llm.ainvoke(input_messages, **kwargs),
                    timeout=60.0  # 超时时间60秒
                )
                break
            except asyncio.TimeoutError as te:
                last_exception = te
                logger.warning(f"⚠️ LLM invocation timed out (attempt {attempt + 1}/{max_retries}): {te}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)  # 重试间隔0.5秒
            except Exception as e:
                last_exception = e
                logger.warning(f"⚠️ LLM invocation failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)  # 重试间隔0.5秒
        else:
            logger.error(f"❌ LLM invocation failed after {max_retries} attempts.")
            raise last_exception

        # 检查响应是否为空或无效
        if not response or not hasattr(response, 'content'):
            error_msg = "LLM returned invalid response (no content attribute)"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # 检查content是否为空字符串
        content = response.content
        if not content or not isinstance(content, str) or not content.strip():
            error_msg = "LLM returned empty content - possible API error or timeout"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        try:
            if hasattr(response, 'content') and isinstance(response.content, str):
                # 处理带有 <thinking> 标签的响应
                content_text = response.content.strip()
                # 移除开头的 <thinking>...</thinking> 标签块
                import re
                thinking_pattern = r'^<thinking>.*?</thinking>\s*'
                if re.match(thinking_pattern, content_text, re.DOTALL):
                    content_text = re.sub(thinking_pattern, '', content_text, count=1, flags=re.DOTALL)
                    logger.info("🔧 Fixed: removed leading <thinking> block from response")

                content_dict = json_module.loads(content_text)

                # 规范化 action 字典
                if 'action' in content_dict:
                    import re
                    normalized_actions = []
                    for action_dict in content_dict['action']:
                        # 处理字符串格式的 action（如 "mark_task_complete(task_id=8)"）
                        if isinstance(action_dict, str):
                            match = re.match(r'(\w+)\(([^)]*)\)', action_dict.strip())
                            if match:
                                action_name = match.group(1)
                                params_str = match.group(2)
                                # 解析参数
                                if action_name in TASK_STATUS_ACTIONS:
                                    task_id_match = re.search(r'task_id=(\d+)', params_str)
                                    if task_id_match:
                                        normalized_actions.append({action_name: {'task_id': int(task_id_match.group(1))}})
                                        logger.info(f"🔧 Fixed: parsed string action '{action_dict}'")
                                elif action_name == 'update_task_status':
                                    task_id_match = re.search(r'task_id=(\d+)', params_str)
                                    status_match = re.search(r"status=['\"]?(\w+)['\"]?", params_str)
                                    if task_id_match and status_match:
                                        normalized_actions.append({
                                            action_name: {
                                                'task_id': int(task_id_match.group(1)),
                                                'status': status_match.group(1)
                                            }
                                        })
                                        logger.info(f"🔧 Fixed: parsed string action '{action_dict}'")
                                elif action_name == 'done':
                                    normalized_actions.append({'done': {}})
                            continue

                        normalized_action = {}
                        for action_name, action_params in action_dict.items():
                            normalized_value = _normalize_action_params(action_name, action_params)
                            # 忽略无效的字符串参数（如 {"click": "保存"}）
                            if isinstance(normalized_value, str) and action_name not in ['done', 'switch_tab']:
                                logger.warning(f"⚠️ Invalid action format: {action_name}: {normalized_value}, skipping")
                                continue
                            normalized_action[action_name] = normalized_value
                        if normalized_action:  # 只添加非空的 action
                            normalized_actions.append(normalized_action)
                    normalized_actions = _enforce_single_task_step(normalized_actions)
                    pending_task_id = getattr(self, '_pending_status_task_id', None)
                    pending_task_description = getattr(self, '_pending_status_task_description', None)
                    content_dict['action'] = _enforce_pending_status_settlement(
                        normalized_actions,
                        pending_task_id,
                        pending_task_description
                    )

                # 检查 action 数组外部的 mark_task_complete（错误格式）
                # 如果存在，将其添加到 action 数组中
                for action_name in [*TASK_STATUS_ACTIONS, 'update_task_status']:
                    if action_name not in content_dict:
                        continue
                    if 'action' not in content_dict:
                        content_dict['action'] = []
                    if isinstance(content_dict[action_name], dict):
                        content_dict['action'].append({action_name: content_dict[action_name]})
                        logger.info(f"🔧 Fixed: moved {action_name} into action array")
                    elif isinstance(content_dict[action_name], int) and action_name in TASK_STATUS_ACTIONS:
                        task_id = content_dict[action_name]
                        content_dict['action'].append({action_name: {'task_id': task_id}})
                        logger.info(f"🔧 Fixed: converted {action_name}({task_id}) to proper format and added to action array")

                parsed = AgentOutput.model_construct(
                    thinking=content_dict.get('thinking'),
                    evaluation_previous_goal=content_dict.get('evaluation_previous_goal'),
                    memory=content_dict.get('memory'),
                    next_goal=content_dict.get('next_goal'),
                    action=[]
                )

                class _ActionWrapper:
                    def __init__(self, action_dict):
                        self._action_dict = action_dict

                    def model_dump(self, **kwargs):
                        return self._action_dict

                    def get_index(self):
                        for action_params in self._action_dict.values():
                            if isinstance(action_params, dict) and 'index' in action_params:
                                return action_params['index']
                        return None

                action_list = []
                for action_dict in content_dict.get('action', []):
                    action_list.append(_ActionWrapper(action_dict))

                object.__setattr__(parsed, 'action', action_list)

                if len(parsed.action) > self.settings.max_actions_per_step:
                    parsed.action = parsed.action[:self.settings.max_actions_per_step]

                return parsed
        except Exception as e:
            # If our complex normalization fails, fall back to the original method
            logger.warning(f"⚠️ Custom output normalization failed, falling back: {e}")
            return await _original_get_model_output(self, input_messages)


    Agent.get_model_output = _patched_get_model_output
    logger.info("✅ Successfully patched Agent.get_model_output")
except Exception as e:
    logger.error(f"❌ Failed to patch Agent.get_model_output: {e}")

# Patch TokenCost
try:
    from browser_use.tokens.service import TokenCost
    from langchain_core.messages import HumanMessage, SystemMessage as LangChainSystemMessage, AIMessage


    def _patched_register_llm(self, llm):
        """修补后的 register_llm，修复 langchain 兼容性"""
        instance_id = str(id(llm))
        if instance_id in self.registered_llms:
            return llm

        self.registered_llms[instance_id] = llm
        _original_ainvoke = llm.ainvoke
        _token_service = self

        async def _fixed_tracked_ainvoke(messages, output_format=None, **kwargs):
            # Sanitize message contents
            def _content_to_str(content):
                if isinstance(content, str): return content
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, str):
                            parts.append(item)
                        elif isinstance(item, dict):
                            if 'text' in item:
                                parts.append(str(item['text']))
                            elif 'image' in item or 'image_url' in item:
                                parts.append("[image]")
                        else:
                            parts.append(str(item))
                    return "\n".join(parts)
                if isinstance(content, dict):
                    if 'text' in content: return str(content['text'])
                    if 'content' in content: return str(content['content'])
                    if 'image' in content or 'image_url' in content: return "[image]"
                return str(content)

            def _sanitize_message(msg):
                msg_type_name = type(msg).__name__
                content = getattr(msg, 'content', msg)
                content_str = _content_to_str(content)
                if msg_type_name == 'SystemMessage': return LangChainSystemMessage(content=content_str)
                if msg_type_name in ('HumanMessage', 'UserMessage'): return HumanMessage(content=content_str)
                if msg_type_name == 'AIMessage': return AIMessage(content=content_str)
                if isinstance(msg, (HumanMessage, LangChainSystemMessage, AIMessage)): return type(msg)(
                    content=content_str)
                return HumanMessage(content=str(content_str))

            sanitized_messages = [_sanitize_message(m) for m in messages]

            output_format = kwargs.pop('output_format', None)
            if output_format:
                kwargs['response_format'] = {"type": "json_object"}

            # Add retry logic for LLM invocation
            max_retries = 2  # 重试次数为2次
            last_exception = None
            for attempt in range(max_retries):
                try:
                    result = await _original_ainvoke(sanitized_messages, **kwargs)
                    break
                except Exception as e:
                    last_exception = e
                    err_str = str(e)
                    if "response_format" in err_str:
                        kwargs.pop('response_format', None)
                        # retry immediately without response_format
                        continue

                    # === 新增：处理 token 超限错误 ===
                    # Moonshot/DeepSeek 等模型返回 "exceeded model token limit" 或 "context_length_exceeded"
                    if ("token limit" in err_str.lower()
                            or "context_length_exceeded" in err_str.lower()
                            or "exceeded" in err_str.lower() and "token" in err_str.lower()):
                        logger.warning(f"⚠️ 检测到 token 超限，自动截断消息重试 (attempt {attempt + 1})")
                        # 保留 system message，压缩最后一条 human message 到约 60%
                        truncated_messages = []
                        for i, m in enumerate(sanitized_messages):
                            c = getattr(m, 'content', '')
                            # 对超长内容（>2000字）截断到前 40% + "...(截断)..." + 后 20%
                            if isinstance(c, str) and len(c) > 2000:
                                keep_head = int(len(c) * 0.4)
                                keep_tail = int(len(c) * 0.2)
                                new_c = c[:keep_head] + "\n...(内容因token限制被截断)...\n" + c[-keep_tail:]
                                truncated_messages.append(type(m)(content=new_c))
                            else:
                                truncated_messages.append(m)
                        sanitized_messages = truncated_messages
                        # 继续下一次 attempt
                        await asyncio.sleep(0.3)
                        continue

                    logger.warning(f"⚠️ LLM ainvoke failed (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 等待0.5秒
            else:
                logger.error(f"❌ LLM ainvoke failed after {max_retries} attempts.")
                raise last_exception

            # Enhance response parsing
            import json as json_module
            clean_content = result.content.strip() if hasattr(result, 'content') else str(result).strip()

            # 处理带有 <thinking> 标签的响应
            thinking_pattern = r'^<thinking>.*?</thinking>\s*'
            if re.match(thinking_pattern, clean_content, re.DOTALL):
                clean_content = re.sub(thinking_pattern, '', clean_content, count=1, flags=re.DOTALL)
                logger.info("🔧 Fixed in TokenCost: removed leading <thinking> block from response")

            # Remove Markdown
            if '```' in clean_content:
                match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', clean_content, re.DOTALL)
                if match:
                    clean_content = match.group(1).strip()
                else:
                    clean_content = re.sub(r'```[a-z]*', '', clean_content).replace('```', '').strip()

            parsed_data = None
            try:
                parsed_data = json_module.loads(clean_content)
            except:
                try:
                    match = re.search(r'(\{.*\})', clean_content, re.DOTALL)
                    if match: parsed_data = json_module.loads(match.group(1))
                except:
                    pass

            # Wrapper classes
            class _ActionWrapper:
                def __init__(self, action_dict):
                    self._dict = {}
                    for k, v in action_dict.items():
                        if isinstance(v, dict):
                            self._dict[k] = _normalize_action_params(k, v)
                        else:
                            self._dict[k] = v
                    for k, v in self._dict.items(): setattr(self, k, v)

                def model_dump(self, **kwargs):
                    return self._dict

                def get_index(self):
                    for v in self._dict.values():
                        if isinstance(v, dict) and 'index' in v: return v['index']
                    return None

            # Construct AgentOutput manually
            agent_output = None
            if parsed_data and 'action' in parsed_data:
                # Normalize actions
                normalized_actions = []
                for action_dict in parsed_data['action']:
                    # 处理字符串格式的 action（如 "mark_task_complete(task_id=8)"）
                    if isinstance(action_dict, str):
                        match = re.match(r'(\w+)\(([^)]*)\)', action_dict.strip())
                        if match:
                            action_name = match.group(1)
                            params_str = match.group(2)
                            # 解析参数
                            if action_name in TASK_STATUS_ACTIONS:
                                task_id_match = re.search(r'task_id=(\d+)', params_str)
                                if task_id_match:
                                    normalized_actions.append({action_name: {'task_id': int(task_id_match.group(1))}})
                                    logger.info(f"🔧 Fixed in TokenCost: parsed string action '{action_dict}'")
                            elif action_name == 'update_task_status':
                                task_id_match = re.search(r'task_id=(\d+)', params_str)
                                status_match = re.search(r"status=['\"]?(\w+)['\"]?", params_str)
                                if task_id_match and status_match:
                                    normalized_actions.append({
                                        action_name: {
                                            'task_id': int(task_id_match.group(1)),
                                            'status': status_match.group(1)
                                        }
                                    })
                                    logger.info(f"🔧 Fixed in TokenCost: parsed string action '{action_dict}'")
                            elif action_name == 'done':
                                normalized_actions.append({'done': {}})
                        continue

                    normalized_action = {}
                    for action_name, action_params in action_dict.items():
                        normalized_value = _normalize_action_params(action_name, action_params)
                        # 忽略无效的字符串参数（如 {"click": "保存"}）
                        if isinstance(normalized_value, str) and action_name not in ['done', 'switch_tab']:
                            logger.warning(f"⚠️ Invalid action format in TokenCost: {action_name}: {normalized_value}, skipping")
                            continue
                        normalized_action[action_name] = normalized_value
                    if normalized_action:  # 只添加非空的 action
                        normalized_actions.append(normalized_action)
                normalized_actions = _enforce_single_task_step(normalized_actions)
                pending_task_id = getattr(llm, '_pending_status_task_id', None)
                pending_task_description = getattr(llm, '_pending_status_task_description', None)
                parsed_data['action'] = _enforce_pending_status_settlement(
                    normalized_actions,
                    pending_task_id,
                    pending_task_description
                )

                # 检查 action 数组外部的 mark_task_complete（错误格式）
                for action_name in [*TASK_STATUS_ACTIONS, 'update_task_status']:
                    if action_name not in parsed_data:
                        continue
                    if isinstance(parsed_data[action_name], dict):
                        parsed_data['action'].append({action_name: parsed_data[action_name]})
                        logger.info(f"🔧 Fixed in TokenCost: moved {action_name} into action array")
                    elif isinstance(parsed_data[action_name], int) and action_name in TASK_STATUS_ACTIONS:
                        task_id = parsed_data[action_name]
                        parsed_data['action'].append({action_name: {'task_id': task_id}})
                        logger.info(f"🔧 Fixed in TokenCost: moved {action_name}(task_id={task_id}) into action array")

                try:
                    from browser_use.agent.message_manager.service import AgentOutput
                    agent_output = AgentOutput.model_construct(
                        thinking=parsed_data.get('thinking'),
                        evaluation_previous_goal=parsed_data.get('evaluation_previous_goal'),
                        memory=parsed_data.get('memory'),
                        next_goal=parsed_data.get('next_goal'),
                        action=[]
                    )
                    action_list = []
                    for action_dict in parsed_data.get('action', []):
                        action_list.append(_ActionWrapper(action_dict))
                    object.__setattr__(agent_output, 'action', action_list)
                except Exception as e:
                    logger.error(f"🔧 Failed to create AgentOutput: {e}")

            class _ResponseWrapper:
                def __init__(self, orig, completion_obj):
                    self._orig = orig
                    self.content = getattr(orig, 'content', '')
                    self.response_metadata = getattr(orig, 'response_metadata', {})
                    self.completion = completion_obj
                    usage = getattr(orig, 'usage', None) or (
                        orig.response_metadata.get('token_usage') if hasattr(orig, 'response_metadata') else None)
                    if not usage: usage = {}
                    # Fix usage
                    usage = dict(usage) if hasattr(usage, '__dict__') else usage
                    usage.setdefault('prompt_tokens', 0)
                    usage.setdefault('completion_tokens', 0)
                    usage.setdefault('total_tokens', 0)
                    self.usage = usage

                def __getattr__(self, name): return getattr(self._orig, name)

            wrapped = _ResponseWrapper(result, agent_output)
            if hasattr(wrapped, 'usage') and wrapped.usage:
                try:
                    _token_service.add_usage(llm.model, wrapped.usage)
                except:
                    pass

            return wrapped

        setattr(llm, 'ainvoke', _fixed_tracked_ainvoke)
        return llm


    TokenCost.register_llm = _patched_register_llm
    logger.info("✅ Successfully patched TokenCost.register_llm")
except Exception as e:
    logger.error(f"❌ Failed to patch TokenCost: {e}")

# Patch BrowserSession.connect (Windows CDP fix)
try:
    from browser_use.browser.session import BrowserSession
    import httpx

    _original_connect = BrowserSession.connect


    async def _patched_connect(self, cdp_url=None):
        if cdp_url: return await _original_connect(self, cdp_url=cdp_url)

        browser_profile = getattr(self, 'browser_profile', None)
        if hasattr(browser_profile, 'cdp_url') and browser_profile.cdp_url:
            return await _original_connect(self, cdp_url=browser_profile.cdp_url)

        port = 9222
        if hasattr(browser_profile, 'extra_chromium_args'):
            for arg in browser_profile.extra_chromium_args:
                if '--remote-debugging-port=' in str(arg):
                    try:
                        port = int(arg.split('=')[1]); break
                    except:
                        pass
        if hasattr(browser_profile, 'remote_debugging_port'):
            port = browser_profile.remote_debugging_port

        cdp_endpoint = f"http://localhost:{port}/json/version"

        for attempt in range(10): # 增加重试次数
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(cdp_endpoint)
                    if response.status_code == 200 and response.text:
                        version_info = response.json()
                        browser_profile.cdp_url = version_info['webSocketDebuggerUrl']
                        return await _original_connect(self, cdp_url=browser_profile.cdp_url)
            except Exception:
                if attempt < 4: await asyncio.sleep(1.0)

        return await _original_connect(self, cdp_url=cdp_url)


    BrowserSession.connect = _patched_connect
    logger.info("✅ Successfully patched BrowserSession.connect")
except Exception as e:
    logger.error(f"❌ Failed to patch BrowserSession.connect: {e}")

# Patch ClickElementAction parameters
try:
    from browser_use.tools.views import ClickElementAction

    _original_click_init = ClickElementAction.__init__


    def _patched_click_init(self, **kwargs):
        fixed_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, int) and key not in ['index']:
                fixed_kwargs['index'] = value
            else:
                fixed_kwargs[key] = value
        if len(kwargs) == 1:
            key, value = list(kwargs.items())[0]
            if isinstance(value, int) and key != 'index':
                fixed_kwargs = {'index': value}
        try:
            return _original_click_init(self, **fixed_kwargs)
        except TypeError:
            if fixed_kwargs and isinstance(list(fixed_kwargs.values())[0], int):
                return _original_click_init(self, **{'index': list(fixed_kwargs.values())[0]})
            raise


    ClickElementAction.__init__ = _patched_click_init
except Exception:
    pass

# Patch ToolRegistry
try:
    from browser_use.tools.registry.service import Registry as ToolRegistry

    # Force patch Registry class
    _original_execute_action = ToolRegistry.execute_action


    async def _patched_execute_action(self, action_name: str, params: dict, **kwargs):
        # 自动映射 switch_tab -> switch (强制映射)
        if action_name == 'switch_tab':
            logger.info(f"🔧 Force aliasing: switch_tab -> switch")
            action_name = 'switch'

        if isinstance(params, int):
            params = {'index': params}
        elif not isinstance(params, dict) and params is not None:
            # 针对 switch_tab 可能是纯字符串的情况
            if action_name in ['switch_tab', 'switch']:
                params = {'tab_id': params}
            else:
                params = {'value': params} if params else {}

        if isinstance(params, dict):
            normalized_params = _normalize_action_params(action_name, params)
            if normalized_params != params:
                logger.info(f"🔧 Normalized action params for {action_name}: {params} -> {normalized_params}")
            params = normalized_params

        # 针对点击增加延迟，确保 UI 更新 (如弹窗弹出、下拉框展开)
        if action_name in ['click_element', 'click']:
            result = await _original_execute_action(self, action_name, params, **kwargs)
            # 增加延迟到 1.5s，并强制在点击后等待浏览器渲染
            # 尤其是对于 element-plus 等 UI 框架，下拉列表渲染需要时间
            await asyncio.sleep(1.5)
            return result

        return await _original_execute_action(self, action_name, params, **kwargs)


    ToolRegistry.execute_action = _patched_execute_action
    logger.info("✅ Successfully patched ToolRegistry.execute_action with alias support")
except Exception as e:
    logger.error(f"❌ Failed to patch ToolRegistry: {e}")

# Patch ScreenshotWatchdog GLOBALLY to fix timeouts
try:
    from browser_use.browser.watchdogs.screenshot_watchdog import ScreenshotWatchdog

    _original_on_screenshot_event = ScreenshotWatchdog.on_ScreenshotEvent

    # Check if already patched to avoid double patching
    if not getattr(_original_on_screenshot_event, '_is_patched_global', False):
        async def on_ScreenshotEvent(self, event):
            """
            Patched screenshot event handler with increased timeout and optimized parameters.
            """
            try:
                # Try original method first with strict timeout
                result = await asyncio.wait_for(
                    _original_on_screenshot_event(self, event),
                    timeout=3.0  # Reduced for fail-fast
                )
                return result
            except asyncio.TimeoutError:
                logger.warning(f"DEBUG: Watchdog timeout (3s), trying optimized approach...")
                try:
                    # Get CDP session
                    cdp_session = await self.browser_session.get_or_create_cdp_session(target_id=None)
                    if not cdp_session: raise Exception("Failed to get CDP session")

                    params = {'format': 'png', 'quality': 50, 'from_surface': True, 'capture_beyond_viewport': False}

                    # One quick retry
                    result = await asyncio.wait_for(
                        cdp_session.cdp_client.send.Page.captureScreenshot(params=params,
                                                                           session_id=cdp_session.session_id),
                        timeout=3.0
                    )
                    return result

                except Exception as ex:
                    # In Text Mode especially, we don't want to die on screenshot
                    logger.warning(f"DEBUG: Screenshot failed optimized, returning placeholder: {ex}")
                    import base64
                    # 1x1 transparent pixel
                    placeholder = base64.b64decode(
                        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
                    return {'data': placeholder}
            except Exception as e:
                logger.error(f"DEBUG: Screenshot unexpected error: {e}")
                import base64
                placeholder = base64.b64decode(
                    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
                return {'data': placeholder}


        on_ScreenshotEvent._is_patched_global = True
        ScreenshotWatchdog.on_ScreenshotEvent = on_ScreenshotEvent
        logger.info("✅ Applied Global ScreenshotWatchdog Patch")

    # Patch DOMWatchdog
    from browser_use.browser.watchdogs.dom_watchdog import DOMWatchdog

    _original_capture_clean_screenshot = DOMWatchdog._capture_clean_screenshot

    if not getattr(_original_capture_clean_screenshot, '_is_patched_global', False):
        async def _capture_clean_screenshot(self):
            try:
                # Very short timeout for DOM clean screenshot checks
                return await asyncio.wait_for(_original_capture_clean_screenshot(self), timeout=3.0)
            except Exception as e:
                logger.warning(f"DEBUG: Clean screenshot failed/timed out: {e}, continuing...")
                return None


        _capture_clean_screenshot._is_patched_global = True
        DOMWatchdog._capture_clean_screenshot = _capture_clean_screenshot
        logger.info("✅ Applied Global DOMWatchdog Patch")

except Exception as e:
    logger.error(f"❌ Failed to apply Global Watchdog patches: {e}")

# Patch Agent verdict
try:
    from browser_use.agent.service import Agent
    from browser_use.agent.message_manager.service import AgentOutput

    _original_judge_and_log = Agent._judge_and_log


    def _agent_output_getattr(self, name):
        if name == 'verdict':
            if hasattr(self, 'next_goal') and self.next_goal:
                if any(
                    w in str(self.next_goal).lower() for w in ['complete', 'done', 'finished', 'success']): return True
            if hasattr(self, 'evaluation_previous_goal') and self.evaluation_previous_goal:
                if any(w in str(self.evaluation_previous_goal).lower() for w in ['success', 'complete']): return True
            return False
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


    if not hasattr(AgentOutput, '__getattr__'):
        AgentOutput.__getattr__ = _agent_output_getattr


    async def _patched_judge_and_log(self):
        try:
            return await _original_judge_and_log(self)
        except AttributeError as e:
            if 'verdict' in str(e):
                return None
            raise


    Agent._judge_and_log = _patched_judge_and_log
except Exception:
    pass

# Patch LocalBrowserWatchdog._find_free_port to force port 9222 on Linux
try:
    from browser_use.browser.watchdogs.local_browser_watchdog import LocalBrowserWatchdog
    import platform

    _original_find_free_port = LocalBrowserWatchdog._find_free_port

    # 创建补丁函数 - 始终作为实例方法（接受 self）
    def _patched_find_free_port(self):
        if platform.system() == 'Linux':
            logger.info("🔧 Force using port 9222 for Linux environment")
            return 9222
        # 尝试调用原始方法，兼容不同签名
        try:
            return _original_find_free_port(self)
        except TypeError:
            # 如果原始方法不接受 self，尝试不带参数调用
            return _original_find_free_port()

    LocalBrowserWatchdog._find_free_port = _patched_find_free_port
    logger.info("✅ Successfully patched LocalBrowserWatchdog._find_free_port")
except Exception as e:
    logger.error(f"❌ Failed to patch LocalBrowserWatchdog._find_free_port: {e}")

# ============================================================================
# PART 2: Helper Classes
# ============================================================================

from langchain_core.callbacks import BaseCallbackHandler
from typing import Any


class RawResponseLogger(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs: Any) -> Any:
        pass

    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        try:
            generation = response.generations[0][0]
            logger.info(f"DEBUG: Raw LLM Response: {generation.text}")
        except:
            pass


# ============================================================================
# PART 3: Base Browser Agent
# ============================================================================

from browser_use import Agent, Controller
from browser_use.browser.events import CloseTabEvent, SwitchTabEvent
from browser_use.browser.profile import BrowserProfile


class BaseBrowserAgent:
    def __init__(self, execution_mode='text', enable_gif=True, case_name=None, headless=None):
        self.execution_mode = execution_mode
        self.enable_gif = enable_gif  # GIF录制开关
        self.case_name = case_name or "Adhoc Task"  # 用例名称
        # headless: True=无头后台运行, False=有头显示, None=自动(Windows/Mac有头,Linux无头)
        self.headless = headless

        # Load browser automation model from the unified AI config center.
        from apps.requirement_analysis.models import AIModelService

        preferred_roles = ['browser_use_vision', 'browser_use_text'] if execution_mode == 'vision' else ['browser_use_text', 'browser_use_vision']
        config_obj, candidates = AIModelService.select_local_usable_config(preferred_roles)

        model_config = {}
        if config_obj:
            model_config = {
                'api_key': config_obj.api_key,
                'base_url': config_obj.base_url,
                'model_name': config_obj.model_name,
                'provider': config_obj.model_type,
                'temperature': config_obj.temperature  # 读取配置的temperature
            }

        self.api_key = model_config.get('api_key') or os.getenv('AUTH_TOKEN')
        self.base_url = model_config.get('base_url') or os.getenv('BASE_URL')
        self.model_name = model_config.get('model_name') or os.getenv('MODEL_NAME')
        self.provider = model_config.get('provider', 'openai')

        if not self.api_key:
            # 尝试最后回退到环境变量
            self.api_key = self.api_key or os.getenv('AUTH_TOKEN', '').strip()
            self.base_url = self.base_url or os.getenv('BASE_URL', '').strip()
            self.model_name = self.model_name or os.getenv('MODEL_NAME', '').strip()
        
        if not self.api_key:
            error_detail = (
                f"无法获取AI模型配置用于网页自动化（模式: {execution_mode}）."
                f"请在「配置中心 → AI模型配置」中配置 browser_use_text 或 browser_use_vision 角色，"
                f"或设置环境变量 AUTH_TOKEN/BASE_URL/MODEL_NAME."
            )
            if candidates:
                error_detail += f" 已发现 {len(candidates)} 个配置但均不可用（缺少API Key或配置不完整）."
            raise ValueError(error_detail)
        if not config_obj and candidates:
            invalid_summary = '; '.join(
                f"{item.get('role')}:{item.get('model_name')}({','.join(item.get('errors') or [])})"
                for item in candidates[:5]
            )
            raise ValueError(
                f"No usable AI model config for browser automation mode: {execution_mode}. "
                f"Invalid configs: {invalid_summary}"
            )
        if not self.base_url:
            self.base_url = AIModelService.default_base_url(self.provider)
        self.base_url = self.base_url.rstrip('/')
        self.selected_ai_role = execution_mode

        # 智能temperature处理：特殊模型强制使用特定temperature值
        # 格式: {'模型名称关键字': temperature值}
        special_model_temperature_map = {
            'kimi-2.5': 1.0,  # Moonshot AI Kimi 2.5 只支持 temperature=1
            'kimi-k2.5': 1.0,  # Moonshot AI Kimi K2.5 只支持 temperature=1
            'kimi': 1.0,  # 通用Kimi模型匹配（兜底）
            # 未来可以在这里添加其他特殊模型，例如：
            # 'claude-3.5-sonnet': 0.7,
            # 'gpt-4-turbo': 0.0,
        }

        # 确定最终使用的temperature值
        final_temperature = 0.0  # 默认值
        model_name_lower = self.model_name.lower()

        # 1. 优先检查是否是特殊模型
        for model_keyword, temp in special_model_temperature_map.items():
            if model_keyword in model_name_lower:
                final_temperature = temp
                logger.info(f"✅ 检测到特殊模型 '{self.model_name}'，使用强制 temperature={temp}")
                break
        else:
            # 2. 如果不是特殊模型，使用配置中的值
            if 'temperature' in model_config:
                final_temperature = model_config['temperature']
                logger.info(f"📋 使用配置的 temperature={final_temperature}")
            else:
                # 3. 如果配置中没有，使用默认值
                final_temperature = 0.0
                logger.info(f"⚙️ 使用默认 temperature={final_temperature}")

        model_name_lower = self.model_name.lower()
        if '8k' in model_name_lower or '8192' in model_name_lower:
            max_tokens_value = 7000
        elif '16k' in model_name_lower or '16384' in model_name_lower:
            max_tokens_value = 14000
        else:
            max_tokens_value = 4000

        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=final_temperature,
            max_tokens=max_tokens_value,
            callbacks=[RawResponseLogger()]
        )

        # browser-use requirement
        try:
            object.__setattr__(self.llm, 'provider', self.provider)
            object.__setattr__(self.llm, 'model', self.model_name)
        except:
            if not hasattr(self.llm, '__pydantic_extra__') or self.llm.__pydantic_extra__ is None:
                self.llm.__pydantic_extra__ = {}
            self.llm.__pydantic_extra__['provider'] = self.provider
            self.llm.__pydantic_extra__['model'] = self.model_name

    def _format_action(self, action):
        try:
            action_dict = {}
            if hasattr(action, 'model_dump'):
                action_dict = action.model_dump()
            elif hasattr(action, '_action_dict'):
                action_dict = action._action_dict
            elif hasattr(action, '_dict'):
                action_dict = action._dict
            elif isinstance(action, dict):
                action_dict = action
            else:
                return str(action)

            if not action_dict: return "待机"

            descriptions = []
            for name, params in action_dict.items():
                if not params and name not in ['scroll_down', 'scroll_up', 'done']: continue

                if name in ['go_to_url', 'navigate']:
                    url = params.get('url') if isinstance(params, dict) else params
                    descriptions.append(f"访问: {url}")
                elif name in ['click_element', 'click']:
                    index = params.get('index') if isinstance(params, dict) else params
                    descriptions.append(f"点击[{index}]")
                elif name in ['input_text', 'input']:
                    text = params.get('text') if isinstance(params, dict) else None
                    descriptions.append(f"输入: '{text}'")
                elif name == 'switch_tab':
                    index = params.get('index', params)
                    descriptions.append(f"切换标签 {index}")
                elif name == 'open_new_tab':
                    url = params.get('url', params)
                    descriptions.append(f"新标签打开: {url}")
                elif name == 'close_tab':
                    descriptions.append("关闭当前标签页")
                elif name == 'done':
                    descriptions.append("任务完成")
                else:
                    descriptions.append(f"{name}")
            return " | ".join(descriptions)
        except:
            return "执行操作"

    async def _verify_execution_llm(self):
        """在真正启动执行前做一次轻量连通性检查，避免浏览器启动后反复空转失败。"""
        try:
            await asyncio.wait_for(
                self.llm.ainvoke("Reply with OK."),
                timeout=20.0
            )
        except Exception as e:
            raise RuntimeError(f"Execution LLM unavailable: {e}") from e

    def _extract_structured_steps(self, text: str):
        """从原始任务文本中稳定提取步骤，作为 LLM 拆分失败时的兜底。"""
        if not text:
            return []

        normalized_text = str(text).replace('\r\n', '\n').replace('\r', '\n').strip()
        if not normalized_text:
            return []

        # 优先按行解析显式编号步骤
        numbered_line_pattern = re.compile(r'^\s*(\d+(?:\.\d+)*)[\.\s、:：-]+(.*)$')
        extracted_steps = []
        plain_lines = []

        for raw_line in normalized_text.split('\n'):
            line = raw_line.strip()
            if not line:
                continue
            match = numbered_line_pattern.match(line)
            if match:
                desc = match.group(2).strip()
                if desc:
                    extracted_steps.append(desc)
            else:
                plain_lines.append(line)

        if extracted_steps:
            if len(extracted_steps) == 1 and '\n' not in normalized_text:
                split_inline_text = re.sub(
                    r'\s+(?=\d+(?:\.\d+)*[\.\s、:：-]+)',
                    '\n',
                    normalized_text
                )
                if split_inline_text != normalized_text:
                    inline_steps = self._extract_structured_steps(split_inline_text)
                    if len(inline_steps) > 1:
                        return inline_steps
            return extracted_steps

        # 其次解析单行内多个编号步骤，例如：
        # "1.访问xx 2.搜索xx 3.点击xx"
        split_inline_text = re.sub(
            r'\s+(?=\d+(?:\.\d+)*[\.\s、:：-]+)',
            '\n',
            normalized_text
        )
        if split_inline_text != normalized_text:
            inline_steps = self._extract_structured_steps(split_inline_text)
            if inline_steps:
                return inline_steps

        # 最后退化为逐行文本
        return plain_lines or [normalized_text]

    def _normalize_steps(self, raw_steps, fallback_text: str):
        """清洗并展开步骤列表，避免多步被合并成一条。"""
        steps = raw_steps if isinstance(raw_steps, list) else []
        normalized_steps = []

        for step in steps:
            if step is None:
                continue
            desc = str(step).strip()
            if not desc:
                continue

            # 如果单个 step 里仍然包含多行/多编号步骤，继续拆开
            nested_steps = self._extract_structured_steps(desc)
            if nested_steps and not (len(nested_steps) == 1 and nested_steps[0] == desc):
                normalized_steps.extend(nested_steps)
            else:
                normalized_steps.append(desc)

        if not normalized_steps:
            normalized_steps = self._extract_structured_steps(fallback_text)

        cleaned_steps = []
        for desc in normalized_steps:
            current = str(desc).strip()
            while True:
                match = re.match(r'^\s*\d+(?:\.\d+)*[\.\s、:：-]+(.*)', current, re.S)
                if not match:
                    break
                current = match.group(1).strip()
            if current:
                cleaned_steps.append(current)

        return cleaned_steps or [fallback_text.strip()]

    def _compact_steps(self, steps):
        """合并过细的动作级步骤，收敛为核心业务子任务。"""
        if not steps:
            return []

        compacted = []
        i = 0
        total = len(steps)

        while i < total:
            current = str(steps[i]).strip()
            current_lower = current.lower()

            # 合并“打开浏览器 / 输入URL / 回车访问”这一类导航碎步
            if (
                ('浏览器' in current or 'browser' in current_lower or '地址栏' in current)
                and i + 1 < total
            ):
                window = " ".join(str(s).strip() for s in steps[i:i + 3])
                url_match = re.search(r'https?://[^\s]+', window)
                if url_match:
                    compacted.append(f"访问{url_match.group(0)}")
                    i += min(3, total - i)
                    continue

            # 合并“点击搜索框 / 输入关键词 / 点击搜索 / 等待结果”
            search_window = " ".join(str(s).strip() for s in steps[i:i + 4])
            if any(keyword in search_window for keyword in ['搜索框', '关键词', '百度一下', '搜索结果', 'search']):
                query_match = re.search(r"(?:输入搜索关键词[:：]?\s*|搜索)\s*['\"]?([^'\"\n]+?)['\"]?(?:\s|$)", search_window)
                if query_match:
                    query = query_match.group(1).strip()
                    query = re.sub(r'(并执行搜索|按钮或按下回车键|结果列表加载完成)$', '', query).strip()
                    compacted.append(f"搜索{query}")
                    i += min(4, total - i)
                    continue

            # 合并“点击第N条结果 + 新标签查看详情”
            if any(keyword in current for keyword in ['搜索结果', '结果', '标题链接', '查看详情']):
                if any(keyword in current for keyword in ['第二条', '第2条', '详情', '链接']):
                    compacted.append("点击第2条搜索结果查看详情")
                    i += 1
                    continue

            # 合并关闭标签页相关步骤
            if any(keyword in current for keyword in ['关闭', '标签页', '新标签页', 'close tab']):
                compacted.append("关闭该标签页")
                i += 1
                continue

            compacted.append(current)
            i += 1

        # 去重并保持顺序
        deduped = []
        for step in compacted:
            if not deduped or deduped[-1] != step:
                deduped.append(step)
        return deduped

    def _step_complexity_score(self, step: str) -> int:
        """粗略评估单个步骤是否包含多个动作。"""
        text = str(step).strip()
        if not text:
            return 0

        score = 0
        if len(text) >= 24:
            score += 1
        if len(text) >= 48:
            score += 1
        if any(token in text for token in ['并', '然后', '之后', '再', '并且', '同时', '且']):
            score += 1
        if any(token in text for token in ['点击', '输入', '搜索', '选择', '打开', '关闭', '提交', '保存', '查看', '切换']):
            action_hits = sum(text.count(token) for token in ['点击', '输入', '搜索', '选择', '打开', '关闭', '提交', '保存', '查看', '切换'])
            if action_hits >= 2:
                score += 1
        return score

    def _step_has_specific_requirements(self, step: str) -> bool:
        """判断步骤是否包含必须保留的字面值、断言或字段约束。"""
        text = str(step).strip()
        if not text:
            return False

        signals = 0
        if re.search(r'https?://', text):
            signals += 1
        if any(token in text for token in ['「', '」', '"', "'"]):
            signals += 1
        if re.search(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', text):
            signals += 1
        if re.search(r'\([^)]{2,}\)', text):
            signals += 1
        if any(token in text for token in ['标题为', '返回', '确认页面', '确认', '验证', '校验']):
            signals += 1
        if any(token in text for token in ['输入框', '按钮', '下拉', '单选', '日期', 'Password', 'Text input', 'Dropdown']):
            signals += 1
        return signals >= 2

    def _should_redecompose_explicit_steps(self, steps):
        """判断已编号任务是否复杂到需要模型二次整合。"""
        if not steps:
            return False

        detail_rich_count = sum(1 for step in steps if self._step_has_specific_requirements(step))
        if detail_rich_count >= max(2, len(steps) // 2):
            return False

        if len(steps) >= 10:
            return True

        complex_count = sum(1 for step in steps if self._step_complexity_score(step) >= 2)
        if complex_count >= max(2, len(steps) // 2):
            return True

        very_long_count = sum(1 for step in steps if len(str(step).strip()) >= 40)
        if very_long_count >= max(2, len(steps) // 2):
            return True

        return False

    async def _model_break_down_task(self, task_description: str, mode: str = 'break_down'):
        """调用模型拆分或重整任务步骤。"""
        if mode == 'recompose':
            prompt = (
                "You are given a task that already has numbered steps, but some steps may be too granular or redundant. "
                "Rewrite them into core business steps only. "
                "Rules: keep the original intent and order, merge mechanical browser operations into the surrounding business step, "
                "do not invent new goals, do not split into micro-actions like clicking an input box or waiting for page load. "
                "Preserve every concrete literal requirement from the original steps, including URLs, field labels, option values, dates, expected titles, "
                "expected result text, and quoted content. Do not replace them with vague phrases like '输入文本信息' or '验证成功'. "
                "Return JSON list of concise Chinese strings only.\n\n"
                f"Task:\n{task_description}"
            )
        else:
            prompt = (
                "Break down this task into core business steps only. "
                "Avoid micro-actions like opening the browser, clicking into an input box, or waiting for results unless they are the user's explicit goal. "
                "Preserve every concrete literal requirement from the original task, including URLs, field labels, option values, dates, expected titles, "
                "expected result text, and quoted content. Do not replace them with vague summaries like '输入文本信息' or '验证成功'. "
                "Keep the order and return JSON list of concise Chinese strings only.\n\n"
                f"Task:\n{task_description}"
            )

        response = await self.llm.ainvoke(prompt)
        content = response.content.strip() if hasattr(response, 'content') else str(response)

        # 检查空内容
        if not content or not content.strip():
            logger.warning("AI返回空内容，无法拆分任务步骤")
            return []
        
        steps = []
        try:
            import json
            match = re.search(r'(\[.*\])', content, re.DOTALL)
            if match:
                steps = json.loads(match.group(1))
        except json.JSONDecodeError as je:
            logger.warning(f"JSON解析失败，无法拆分任务步骤: {je}")
        except Exception:
            logger.warning("拆分任务步骤时发生未知错误")

        return steps

    def _finalize_steps(self, steps, fallback_text: str):
        """统一收口步骤列表，保证输出可执行且尽量精简。"""
        return self._compact_steps(self._normalize_steps(steps, fallback_text))

    async def analyze_task(self, task_description: str):
        try:
            explicit_steps = self._extract_structured_steps(task_description)
            if len(explicit_steps) >= 2:
                if self._should_redecompose_explicit_steps(explicit_steps):
                    steps = await self._model_break_down_task(task_description, mode='recompose')
                    cleaned_steps = self._finalize_steps(steps, task_description)
                else:
                    cleaned_steps = self._normalize_steps(explicit_steps, task_description)
                return [{'id': i + 1, 'description': s, 'status': 'pending'} for i, s in enumerate(cleaned_steps)]

            steps = await self._model_break_down_task(task_description, mode='break_down')
            cleaned_steps = self._finalize_steps(steps, task_description)

            return [{'id': i + 1, 'description': s, 'status': 'pending'} for i, s in enumerate(cleaned_steps)]
        except Exception as e:
            logger.warning(f"⚠️ analyze_task fallback triggered: {e}")
            cleaned_steps = self._finalize_steps([], task_description)
            return [{'id': i + 1, 'description': s, 'status': 'pending'} for i, s in enumerate(cleaned_steps)]

    @staticmethod
    def _find_available_port(start_port: int = 9222, max_attempts: int = 50) -> int:
        """从 start_port 开始找到一个可用的 TCP 端口。"""
        import socket
        for offset in range(max_attempts):
            port = start_port + offset
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                if result != 0:
                    if offset > 0:
                        logger.info(f"端口 {start_port} 被占用，使用端口 {port}")
                    return port
            except Exception:
                pass
        logger.warning(f"无法找到可用端口（{start_port}-{start_port + max_attempts}），使用 {start_port}")
        return start_port

    def _cleanup_zombie_chrome(self):
        """清理占用端口 9222 的僵尸 Chrome 进程（跨平台）。"""
        import platform
        import psutil

        system = platform.system()
        logger.info("🧹 Cleaning up zombie Chrome processes...")
        cleaned_count = 0

        chrome_names = {'chrome', 'chromium', 'chrome.exe', 'chromium.exe',
                        'google chrome', 'msedge', 'msedge.exe'}
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    name = (proc.info['name'] or '').lower()
                    if not any(cn in name for cn in chrome_names):
                        continue
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('9222' in str(arg) for arg in cmdline):
                        logger.info(f"Killing zombie chrome pid={proc.pid} ({name})")
                        try:
                            proc.kill()
                            cleaned_count += 1
                        except psutil.AccessDenied:
                            logger.warning(f"Cannot kill pid={proc.pid} (access denied), trying terminate")
                            try:
                                proc.terminate()
                                proc.wait(timeout=3)
                                cleaned_count += 1
                            except Exception:
                                pass
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup zombie chrome: {e}")

        if cleaned_count > 0:
            logger.info(f"✅ Cleaned up {cleaned_count} zombie Chrome processes")
            # 等待端口释放
            import time
            time.sleep(1.5)

    def _preflight_browser_check(self):
        """
        浏览器预检：在执行前确认浏览器可用 + 端口可用。
        发现问题时抛出明确的 RuntimeError，避免启动后误导性报错。
        """
        import platform
        import socket
        import os

        system = platform.system()
        errors = []

        # 1. 检查浏览器可执行文件是否存在
        chrome_path = None
        if system == 'Windows':
            candidate_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            ]
            for p in candidate_paths:
                if os.path.isfile(p):
                    chrome_path = p
                    break
            
            if not chrome_path:
                huanjing_chromium = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                    'huanjing', 'chrome-win', 'chrome.exe'
                )
                if os.path.isfile(huanjing_chromium):
                    chrome_path = huanjing_chromium
        elif system == 'Linux':
            import glob
            candidate_paths = [
                '/usr/bin/chromium-browser', '/usr/bin/chromium',
                '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable',
                '/opt/google/chrome/chrome', '/snap/bin/chromium',
            ]
            for p in candidate_paths:
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    chrome_path = p
                    break
            if not chrome_path:
                playwright_matches = glob.glob('/ms-playwright/**/chrome*', recursive=True)
                playwright_matches += glob.glob('/root/.cache/ms-playwright/**/chrome*', recursive=True)
                playwright_matches += glob.glob('/ms-playwright/**/chromium', recursive=True)
                for p in playwright_matches:
                    if os.path.isfile(p) and os.access(p, os.X_OK):
                        chrome_path = p
                        break

        if chrome_path:
            logger.info(f"✅ 浏览器预检通过: {chrome_path}")
        else:
            logger.warning("⚠️ 未找到预装浏览器，尝试自动下载Chromium...")
            chrome_path = self._download_chromium()
            if chrome_path:
                logger.info(f"✅ 自动下载Chromium成功: {chrome_path}")
            else:
                if system == 'Windows':
                    errors.append(
                        "未找到 Chrome/Edge 浏览器，且自动下载失败。请安装 Google Chrome："
                        "https://www.google.com/chrome/"
                    )
                else:
                    errors.append(
                        "未找到 Chromium/Chrome 浏览器，且自动下载失败。请在服务器上运行："
                        "playwright install chromium"
                    )

        # 2. 检查端口 9222 是否可用
        port = 9222
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                errors.append(
                    f"端口 {port} 已被占用，可能有残留的 Chrome 进程。"
                    f"请手动清理：taskkill /F /IM chrome.exe（Windows）"
                    f"或 pkill -f chrome（Linux）"
                )
            else:
                logger.info(f"✅ 端口 {port} 可用")
        except Exception as e:
            logger.warning(f"端口检查异常（非致命）: {e}")

        if errors:
            raise RuntimeError(
                "浏览器预检失败，无法启动自动化执行：\n" +
                "\n".join(f"  - {e}" for e in errors)
            )

        return chrome_path

    def _download_chromium(self):
        """自动下载Chromium到backend/huanjing/目录"""
        import zipfile
        import shutil
        
        huanjing_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'huanjing')
        os.makedirs(huanjing_dir, exist_ok=True)
        
        system = self._get_system()
        download_url = None
        extract_name = None
        
        if system == 'Windows':
            download_url = 'https://storage.googleapis.com/chromium-browser-snapshots/Win/1429927/chrome-win.zip'
            extract_name = 'chrome-win'
            executable_name = 'chrome.exe'
        elif system == 'Linux':
            download_url = 'https://storage.googleapis.com/chromium-browser-snapshots/Linux_x64/1429927/chrome-linux.zip'
            extract_name = 'chrome-linux'
            executable_name = 'chrome'
        else:
            logger.error("❌ 不支持的操作系统，无法自动下载Chromium")
            return None
        
        extract_path = os.path.join(huanjing_dir, extract_name)
        executable_path = os.path.join(extract_path, executable_name)
        
        if os.path.exists(executable_path):
            logger.info(f"✅ Chromium已存在: {executable_path}")
            return executable_path
        
        zip_path = os.path.join(huanjing_dir, f'{extract_name}.zip')
        
        try:
            logger.info(f"📥 开始下载Chromium: {download_url}")
            
            import requests
            response = requests.get(download_url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            if progress % 20 == 0:
                                logger.info(f"📥 下载进度: {progress:.1f}%")
            
            logger.info(f"✅ 下载完成: {zip_path}")
            logger.info(f"📦 开始解压...")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(huanjing_dir)
            
            os.remove(zip_path)
            
            if os.path.exists(executable_path):
                os.chmod(executable_path, 0o755)
                logger.info(f"✅ Chromium安装完成: {executable_path}")
                return executable_path
            else:
                logger.error(f"❌ 解压后未找到可执行文件: {executable_path}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 自动下载Chromium失败: {e}")
            if os.path.exists(zip_path):
                os.remove(zip_path)
            return None

    def _create_browser_profile(self):
        """创建浏览器运行配置（预检已通过后调用）。"""
        # Default implementation, can be overridden
        chrome_path = None
        import platform
        import socket

        system = platform.system()

        # 动态选择可用的调试端口
        debug_port = self._find_available_port(9222)

        if system == 'Windows':
            paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
            for p in paths:
                if os.path.exists(p):
                    chrome_path = p
                    break
        elif system == 'Linux':
            # Linux 系统常见的 Chrome 路径 - 优先使用我们预装的浏览器
            paths = [
                # 优先使用Docker容器中预装的Chromium
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
                '/usr/bin/google-chrome',
                # 检查Playwright安装的浏览器
                '/ms-playwright/chromium-*/chromium-linux/chromium',
                '/root/.cache/ms-playwright/chromium-*/chromium-linux/chromium',
                # 备用路径
                '/usr/bin/google-chrome-stable',
                '/opt/google/chrome/chrome',
                '/snap/bin/chromium',
            ]
            for p in paths:
                # 支持通配符路径
                if '*' in p:
                    import glob
                    matches = glob.glob(p)
                    if matches:
                        for match in matches:
                            if os.path.exists(match) and os.access(match, os.X_OK):
                                chrome_path = match
                                logger.info(f"找到浏览器: {chrome_path}")
                                break
                        if chrome_path:
                            break
                elif os.path.exists(p) and os.access(p, os.X_OK):
                    chrome_path = p
                    logger.info(f"找到浏览器: {chrome_path}")
                    break

            # 如果还是没找到，尝试查找Playwright的默认路径或让browser-use自行安装
            if not chrome_path:
                import glob
                playwright_paths = glob.glob('/ms-playwright/**/chromium', recursive=True)
                playwright_paths.extend(glob.glob('/root/.cache/ms-playwright/**/chromium', recursive=True))
                playwright_paths.extend(glob.glob('/ms-playwright/**/chromium-linux/chromium', recursive=True))
                playwright_paths.extend(glob.glob('/root/.cache/ms-playwright/**/chromium-linux/chromium', recursive=True))
                for p in playwright_paths:
                    if os.path.exists(p) and os.access(p, os.X_OK):
                        chrome_path = p
                        logger.info(f"通过Playwright找到浏览器: {chrome_path}")
                        break

                # 最后的备用方案：让browser-use自行处理浏览器安装
                if not chrome_path:
                    logger.info("未找到预装浏览器，将让browser-use自动安装")
                    chrome_path = None  # 让browser-use处理

        # headless 模式：优先使用显式配置，否则自动判断
        if self.headless is None:
            use_headless = (system == 'Linux')
        else:
            use_headless = self.headless

        # 基础性能优化参数
        extra_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars', '--disable-notifications',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-extensions',
            '--disable-web-security',  # 允许跨域请求
        ]

        # 根据操作系统添加特定参数
        if system == 'Linux':
            # Linux 服务器环境（特别是无头环境）必需的参数
            extra_args.extend([
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--headless=new',
                '--disable-software-rasterizer',
                f'--remote-debugging-port={debug_port}',
                '--remote-debugging-address=0.0.0.0',
                '--no-zygote',
                '--single-process',
            ])
        else:
            # macOS 和 Windows
            extra_args.extend([
                '--no-sandbox',
                '--disable-gpu',
                f'--remote-debugging-port={debug_port}',
            ])
            # Windows 无头模式需要额外参数保证稳定性
            if system == 'Windows' and use_headless:
                extra_args.extend([
                    '--headless=new',
                    '--disable-software-rasterizer',
                ])

        return BrowserProfile(
            headless=use_headless,
            disable_security=True,
            executable_path=chrome_path,
            args=extra_args,
            wait_for_network_idle_page_load_time=0.2,
            minimum_wait_page_load_time=0.05,
            wait_between_actions=0.1,
            enable_default_extensions=False
        )

    async def run_task(self, task_description: str, planned_tasks=None, callback=None, should_stop=None):
        await self._verify_execution_llm()

        # 初始化步骤录制器（每步截图 + AI描述 + Word/视频导出）
        step_recorder = None
        try:
            from .step_recorder import StepRecorder
            step_recorder = StepRecorder(case_name=self.case_name)
            step_recorder.enable_video(True)
            logger.info(f"StepRecorder 初始化成功: {step_recorder.output_dir}")
        except Exception as rec_error:
            logger.warning(f"StepRecorder 初始化失败（截图/录制功能将不可用）: {rec_error}")
            step_recorder = None

        # Cleanup potential zombie processes before starting
        self._cleanup_zombie_chrome()

        # 浏览器预检：确保浏览器可用、端口可用，失败则提前报错
        chrome_path = self._preflight_browser_check()

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        controller = Controller()
        _task_was_done = False
        active_task_statuses = {'pending', 'in_progress'}

        async def emit_callback(payload):
            if not callback:
                return

            if asyncio.iscoroutinefunction(callback):
                await callback(payload)
            else:
                callback(payload)

        def is_placeholder_url(url: str) -> bool:
            normalized = (url or '').strip().lower()
            return (
                not normalized
                or normalized == 'about:blank'
                or normalized.startswith('chrome://newtab')
                or normalized.startswith('edge://newtab')
            )

        def is_close_step(description: str) -> bool:
            text = str(description or '').strip()
            return any(keyword in text for keyword in ['关闭', '关闭该标签页', '关闭标签页'])

        def get_next_active_task():
            if not planned_tasks:
                return None

            for task in planned_tasks:
                if task.get('status', 'pending') in active_task_statuses:
                    return task
            return None

        async def find_preferred_fallback_tab(browser_session, exclude_target_id=None):
            tabs = await browser_session.get_tabs()
            candidate_tabs = [tab for tab in tabs if tab.target_id != exclude_target_id]
            if not candidate_tabs:
                return None

            non_placeholder_tabs = [tab for tab in candidate_tabs if not is_placeholder_url(getattr(tab, 'url', ''))]
            return (non_placeholder_tabs or candidate_tabs)[-1]

        @controller.action('Done')
        async def done(success: bool = True, text: str = ""):
            nonlocal _task_was_done
            _task_was_done = True
            return f"Finished: {text}"

        @controller.action('close_tab')
        async def close_tab(browser_session=None):
            if browser_session is None or browser_session.agent_focus_target_id is None:
                raise ValueError("No active tab to close")
            target_id = browser_session.agent_focus_target_id
            fallback_tab = None
            try:
                fallback_tab = await find_preferred_fallback_tab(browser_session, exclude_target_id=target_id)
            except Exception as e:
                logger.warning(f"Failed to determine fallback tab before closing {target_id[-4:]}: {e}")

            event = browser_session.event_bus.dispatch(CloseTabEvent(target_id=target_id))
            await event

            if fallback_tab is not None:
                try:
                    await asyncio.sleep(0.15)
                    if browser_session.agent_focus_target_id != fallback_tab.target_id:
                        await browser_session.event_bus.dispatch(
                            SwitchTabEvent(target_id=fallback_tab.target_id)
                        )
                        logger.info(
                            f"↩️ Switched back to existing tab {fallback_tab.target_id[-4:]} "
                            f"({fallback_tab.url}) after closing {target_id[-4:]}"
                        )
                        await emit_callback({
                            'type': 'log',
                            'content': (
                                f"\n[System]\n关闭标签页后，已切回来源页 {fallback_tab.target_id[-4:]}\n"
                            )
                        })
                except Exception as e:
                    logger.warning(f"Failed to switch back to preferred tab after closing {target_id[-4:]}: {e}")

            next_active_task = get_next_active_task()
            if next_active_task and is_close_step(next_active_task.get('description')):
                logger.info(f"✅ Auto-marking close step task {next_active_task['id']} as completed after close_tab")
                await emit_callback({'task_id': int(next_active_task['id']), 'status': 'completed'})

            return f"Closed tab {target_id[-4:]}"

        @controller.action('mark_task_complete')
        async def mark_task_complete(task_id: int):
            logger.info(f"✅ Explicitly marking task {task_id} as completed")
            try:
                await emit_callback({'task_id': int(task_id), 'status': 'completed'})
            except Exception as e:
                logger.warning(f"Failed to execute mark_task_complete callback: {e}")
            return f"Task {task_id} marked completed"

        @controller.action('mark_task_failed')
        async def mark_task_failed(task_id: int):
            logger.info(f"❌ Explicitly marking task {task_id} as failed")
            try:
                await emit_callback({'task_id': int(task_id), 'status': 'failed'})
            except Exception as e:
                logger.warning(f"Failed to execute mark_task_failed callback: {e}")
            return f"Task {task_id} marked failed"

        @controller.action('mark_task_skipped')
        async def mark_task_skipped(task_id: int):
            logger.info(f"⏭️ Explicitly marking task {task_id} as skipped")
            try:
                await emit_callback({'task_id': int(task_id), 'status': 'skipped'})
            except Exception as e:
                logger.warning(f"Failed to execute mark_task_skipped callback: {e}")
            return f"Task {task_id} marked skipped"

        @controller.action('update_task_status')
        async def update_task_status(task_id: int, status: str):
            normalized_status = str(status).strip().lower()
            if normalized_status not in {'completed', 'failed', 'skipped', 'in_progress'}:
                raise ValueError(f"Unsupported task status: {status}")
            logger.info(f"🔄 Explicitly updating task {task_id} to {normalized_status}")
            try:
                await emit_callback({'task_id': int(task_id), 'status': normalized_status})
            except Exception as e:
                logger.warning(f"Failed to execute update_task_status callback: {e}")
            return f"Task {task_id} marked {normalized_status}"

        @controller.action('diagnose_page_issue')
        async def diagnose_page_issue_action(reason: str = "", browser_session=None):
            from .ai_diagnostics import diagnose_page_issue

            url = ''
            title = ''
            page_text = ''
            page_html = ''
            try:
                if browser_session is not None:
                    try:
                        url = await browser_session.get_current_page_url()
                    except Exception:
                        url = ''
                    try:
                        title = await browser_session.get_current_page_title()
                    except Exception:
                        title = ''
                    try:
                        page_text = await browser_session.get_state_as_text()
                    except Exception:
                        page_text = ''
                    try:
                        page = await browser_session.get_current_page()
                        if page is not None and hasattr(page, 'content'):
                            page_html = await page.content()
                            # 同时收集 iframe 内的 HTML（验证码常在 iframe 中）
                            try:
                                from .captcha_handler import _get_all_captcha_frames
                                captcha_frames = await _get_all_captcha_frames(page)
                                for fi in captcha_frames:
                                    if fi['name'] == 'main':
                                        continue
                                    try:
                                        page_html += '\n<!-- iframe: ' + fi['url'][:80] + ' -->\n'
                                        page_html += await fi['frame'].content()
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    except Exception:
                        page_html = ''
            except Exception as collect_error:
                logger.debug(f"AI diagnosis page-state collection skipped: {collect_error}")

            next_task = get_next_active_task() or {}
            action_context = json.dumps({
                'reason': reason,
                'next_task': next_task,
                'case_name': self.case_name,
                'execution_mode': self.execution_mode,
            }, ensure_ascii=False, default=str)
            diagnosis_log, diagnosis = await diagnose_page_issue(
                reason=reason,
                url=url,
                title=title,
                page_html=page_html,
                page_text=page_text,
                action_context=action_context,
                planned_tasks=planned_tasks,
            )
            await emit_callback({'type': 'log', 'content': diagnosis_log})
            return diagnosis_log

        @controller.action('handle_verification_barrier')
        async def handle_verification_barrier(reason: str = "", browser_session=None):
            from .captcha_handler import CaptchaHandler, detect_captcha, captcha_block_reason, captcha_block_reason as _reason
            from .ai_diagnostics import diagnose_page_issue

            url = ''
            title = ''
            page_text = ''
            page_html = ''
            page = None
            try:
                if browser_session is not None:
                    try:
                        url = await browser_session.get_current_page_url()
                    except Exception:
                        url = ''
                    try:
                        title = await browser_session.get_current_page_title()
                    except Exception:
                        title = ''
                    try:
                        page_text = await browser_session.get_state_as_text()
                    except Exception:
                        page_text = ''
                    try:
                        page = await browser_session.get_current_page()
                        if page is not None and hasattr(page, 'content'):
                            page_html = await page.content()
                            # 同时收集 iframe 内的 HTML（验证码常在 iframe 中）
                            try:
                                from .captcha_handler import _get_all_captcha_frames
                                captcha_frames = await _get_all_captcha_frames(page)
                                for fi in captcha_frames:
                                    if fi['name'] == 'main':
                                        continue
                                    try:
                                        page_html += '\n<!-- iframe: ' + fi['url'][:80] + ' -->\n'
                                        page_html += await fi['frame'].content()
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    except Exception:
                        page_html = ''
            except Exception as collect_error:
                logger.debug(f"Verification barrier page-state collection skipped: {collect_error}")

            has_captcha, captcha_type = detect_captcha(page_html or page_text or reason)
            action_lines = ["\n[VERIFICATION_HANDLER]", f"- reason: {reason or 'automation blocked'}",
                          f"- detected_type: {captcha_type or 'none'}"]
            handled = False
            captcha_solved = False

            if page is not None:
                # Step 1: Dismiss overlays/cookie popups first
                try:
                    overlay_closed = await CaptchaHandler.dismiss_common_overlays(page)
                    if overlay_closed:
                        handled = True
                        action_lines.append('- overlay_action: dismissed consent/privacy overlay')
                        try:
                            await asyncio.sleep(0.5)
                            page_html = await page.content()
                            has_captcha, captcha_type = detect_captcha(page_html)
                        except Exception:
                            pass
                except Exception as overlay_error:
                    action_lines.append(f"- overlay_error: {overlay_error}")

                # Step 2: Auto-solve captcha based on type
                if has_captcha and captcha_type not in ('third_party_captcha', 'sms_verify'):
                    try:
                        solved, detail = await CaptchaHandler.auto_handle_captcha(page, captcha_type)
                        captcha_solved = solved
                        action_lines.append(f"- auto_solve_action: {detail}")
                        action_lines.append(f"- auto_solve_result: {'solved' if solved else 'failed'}")

                        if solved:
                            handled = True
                            try:
                                await asyncio.sleep(1.0)
                                page_html = await page.content()
                                has_captcha, captcha_type = detect_captcha(page_html)
                            except Exception:
                                pass
                    except Exception as auto_error:
                        action_lines.append(f"- auto_solve_error: {auto_error}")

            if has_captcha and not captcha_solved:
                action_lines.append(f"- result: blocked_by_{captcha_type}")
                action_lines.append(f"- policy: {captcha_block_reason(captcha_type)}")

                # 尝试逆向分析验证码 API（诊断用）
                if page is not None and captcha_type in ('slider_captcha', 'general_captcha'):
                    try:
                        from .captcha_reverse import analyze_and_capture_captcha_api
                        api_info = await analyze_and_capture_captcha_api(page)
                        if api_info.get('widget_type') != 'unknown':
                            action_lines.append(f"- reverse_widget: {api_info['widget_type']}")
                        if api_info.get('api_endpoints'):
                            action_lines.append(f"- reverse_endpoints: {api_info['api_endpoints'][:3]}")
                        if api_info.get('token_fields'):
                            action_lines.append(f"- reverse_token_fields: {api_info['token_fields']}")
                    except Exception as rev_err:
                        logger.debug(f"Captcha reverse analysis skipped: {rev_err}")
            elif captcha_solved:
                action_lines.append(f"- result: captcha_automatically_solved")
                action_lines.append(f"- policy: 验证码已被自动化引擎解决，请继续执行当前任务")
            else:
                action_lines.append(f"- result: {'barrier_handled' if handled else 'no_verification_barrier_detected'}")

            # Only run AI diagnosis if captcha was NOT solved
            if captcha_solved:
                final_log = '\n'.join(action_lines) + (
                    "\n[AI_DIAGNOSIS]\n"
                    "- issue_type: resolved\n"
                    "- evidence: 自动化引擎已成功解决验证码\n"
                    "- cause: n/a\n"
                    "- recommended_action: CONTINUE with current task - captcha has been solved\n"
                    "- requires_human: no\n"
                    "- status_suggestion: in_progress\n"
                    "- source: automation_engine"
                )
            else:
                diagnosis_log, diagnosis = await diagnose_page_issue(
                    reason=reason or 'verification_barrier_handling',
                    url=url,
                    title=title,
                    page_html=page_html,
                    page_text=page_text,
                    action_context='\n'.join(action_lines),
                    planned_tasks=planned_tasks,
                    max_tokens=700,
                )
                final_log = '\n'.join(action_lines) + diagnosis_log

            await emit_callback({'type': 'log', 'content': final_log})
            return final_log

        # 构建强化版 Prompt
        final_task = task_description
        if planned_tasks:
            final_task += "\n\nIMPORTANT INSTRUCTION:\n"
            final_task += "You have a list of sub-tasks. Execute strictly in order.\n"
            final_task += "CRITICAL: MUST call one of 'mark_task_complete', 'mark_task_failed', 'mark_task_skipped', or 'update_task_status(task_id=..., status=...)' IMMEDIATELY after determining each sub-task result. NEVER skip this step.\n"
            final_task += "IMPORTANT: If a sub-task (like opening a URL) is already fulfilled by the initial state, YOU MUST mark it complete in your VERY FIRST STEP.\n"
            final_task += "Sub-tasks (Execute in order):\n"
            cleaned_tasks = []
            for t in planned_tasks:
                desc = t['description']
                # 递归去除所有层级的重复序号，例如 "1. 1. xxx" -> "xxx"
                while True:
                    match = re.match(r'^\s*\d+[\.\s、:]+(.*)', desc)
                    if not match: break
                    desc = match.group(1).strip()
                cleaned_tasks.append(f"{t['id']}. {desc}")
            final_task += "\n".join(cleaned_tasks)

        # 极限效率版标记指令
        from datetime import datetime
        final_task += f"\n\nCURRENT TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        final_task += "\nCRITICAL PERFORMANCE & SYNC RULES:\n"
        final_task += "1. TASK COMPLETION MARKING RULES:\n"
        final_task += "   a) MARK AFTER COMPLETION: Call 'mark_task_complete(task_id=N)' ONLY AFTER you have SUCCESSFULLY COMPLETED task N.\n"
        final_task += "   b) MARK CURRENT TASK: Always mark the task you just completed, NOT the next task or previous tasks.\n"
        final_task += "   c) CHECK TASK ID: Before marking, verify: 'I just completed task N' - if N is already marked, check which task you actually completed.\n"
        final_task += "   d) DO NOT SKIP: Every sub-task must end with an explicit terminal status update: completed, failed, or skipped.\n"
        final_task += "   e) EXAMPLE SUCCESS: [{click: {...}}, {mark_task_complete: {task_id: 4}}]\n"
        final_task += "   f) EXAMPLE FAILURE: if task 4 cannot be completed after verification, call {mark_task_failed: {task_id: 4}}.\n"
        final_task += "   g) EXAMPLE SKIP: if task 4 is intentionally unnecessary, call {mark_task_skipped: {task_id: 4}}.\n"
        final_task += "   h) NO PRE-MARKING: Never mark a task before completing it. Never mark a task twice.\n"
        final_task += "   i) SINGLE-TASK STEP: If you mark task N in the current step, STOP there. Do NOT start task N+1 in the same step.\n"
        final_task += "   j) FORM EXAMPLE: Good: [{input: {...}}, {mark_task_complete: {task_id: 2}}] then next step handles task 3. Bad: [{mark_task_complete: {task_id: 1}}, {input: {...task 2...}}].\n"
        final_task += "2. NO JAVASCRIPT IN INPUT: When a task asks for a timestamp, YOU MUST compute the final string yourself (e.g., 'V8.01734892400').\n"
        final_task += "   - DO NOT output 'Date.now()' or '{{...}}' strings. Use the CURRENT TIME provided above to estimate a timestamp.\n"
        final_task += "3. DROPDOWN & MODAL ISOLATION: If an action (clicking a button/dropdown) triggers a UI change (modal opens/dropdown expands), YOU MUST STOP and WAIT for the next step to see the new elements. DO NOT attempt to interact with newly appeared elements (like dropdown options) in the same step as the click that opened them.\n"
        final_task += "4. TAB HANDLING: If clicking a link/result opens a new tab, DO NOT click the same result again. Immediately switch to the newest tab, verify the detail page there, then mark the current sub-task complete.\n"
        final_task += "5. ULTRALIGHT THINKING: Keep 'thinking' under 10 words. Just list next actions. Merge multiple INPUTS if they are on the same form, but NEVER merge a UI-opening click with its subsequent interaction. SPEED IS CRITICAL - respond as quickly as possible.\n"
        final_task += "6. FORM VALIDATION & ERROR DETECTION: When filling forms, you MUST:\n"
        final_task += "   a) Check for RED TEXT messages (validation errors) before clicking save/submit\n"
        final_task += "   b) If validation errors exist, COMPLETE ALL MISSING FIELDS first, then retry save\n"
        final_task += "   c) NEVER close a dialog/modal if there are validation errors - complete the form instead\n"
        final_task += "   d) Verify all required fields are filled before attempting to save\n"
        final_task += "   e) Common validation errors: missing required fields (red asterisk or red text), invalid format, etc.\n"
        final_task += "7. RETRY LOGIC: If a previous 'save' or 'submit' failed (e.g., error toast or validation error):\n"
        final_task += "   a) STOP and examine the page for validation errors (red text, error messages)\n"
        final_task += "   b) RE-VERIFY all fields - check dropdowns are actually selected, not just clicked\n"
        final_task += "   c) Re-select dropdowns and re-input text to ensure the form is complete\n"
        final_task += "   d) DO NOT close the dialog - stay and complete all missing fields\n"
        final_task += "   e) Often errors are caused by: missing project selection, unfilled required fields, incorrect format\n"
        final_task += "8. DO NOT REPEAT: If a task is complete, mark it and MOVE ON. Never click the same search result or link twice unless you verified the first click failed.\n"
        final_task += "9. VERIFICATION: Task 15/16 usually require checking the list. Ensure you are on the correct page and the new data is visible before marking complete.\n"
        final_task += "10. ELEMENT IDENTIFICATION: Carefully identify elements before clicking. AVOID clicking 'close' or 'cancel' buttons when filling forms. Check button labels, aria-labels, and icons to ensure you're clicking the correct element.\n"
        final_task += "11. ACTION PARAM FORMAT: For browser actions, always use browser-use native parameter names. Use 'index' for click/input/select actions, use 'text' for typed content, and never use aliases like 'element_id'.\n"
        final_task += "12. CREDENTIALS RULE: NEVER invent, replace, or guess credentials. Only use the username/password explicitly provided in the task. If login keeps failing with an explicit error like '登录失败' or '用户名或密码错误', stop retrying after a small number of attempts and mark the current login task as failed.\n"

        if 'qwen' in self.model_name.lower() or 'deepseek' in self.model_name.lower():
            final_task += "13. EXTREMELY MINIMIZE output tokens for speed. Keep responses as short as possible while maintaining accuracy.\n"

        # CAPTCHA / 验证码处理指令（自动化优先）
        final_task += "\n13. AI PAGE ISSUE DIAGNOSIS (MANDATORY):\n"
        final_task += "    a) When progress is blocked by captcha, slider verification, SMS/email verification, page timeout, blank page, unexpected redirect, element not found, validation error, login failure, server error, or repeated failed action, FIRST call handle_verification_barrier(reason='brief reason'). This will trigger automated captcha solving. Do NOT skip the task before calling this.\n"
        final_task += "    b) After handle_verification_barrier returns, WAIT for the automation engine's result. The engine will attempt to auto-solve captchas (slider, text, etc.). Only if the result says 'blocked' or 'failed', then call diagnose_page_issue.\n"
        final_task += "    c) Read the diagnosis result and use it to decide whether to retry, refresh, switch tab, complete missing form fields, mark_task_failed, or mark_task_skipped. Do not silently fail.\n"
        final_task += "    d) CRITICAL: The automation engine handles slider and text captchas automatically. Do NOT call mark_task_skipped until the automation engine has confirmed failure. Let the engine try first.\n"

        final_task += "\n14. CAPTCHA & VERIFICATION HANDLING:\n"
        final_task += "    a) IMAGE/TEXT CAPTCHA (图形验证码): The automation engine will attempt OCR recognition. FIRST call handle_verification_barrier and wait. Only call mark_task_skipped(task_id=X) if the engine reports OCR failure.\n"
        final_task += "    b) SLIDER VERIFICATION (滑块验证): The automation engine will attempt up to 3 human-like drag operations. FIRST call handle_verification_barrier and wait. Only call mark_task_skipped(task_id=X) if all attempts fail.\n"
        final_task += "    c) SMS/EMAIL VERIFICATION: This requires human interaction. Call mark_task_skipped(task_id=X).\n"
        final_task += "    d) COOKIE/PRIVACY POPUPS: If a cookie consent or privacy overlay appears, click 'Accept'/'同意'/'Allow' to dismiss it before continuing.\n"
        final_task += "    e) SESSION TIMEOUT: If the page shows 'session expired' or '请重新登录', immediately call mark_task_failed(task_id=X) for the login/auth tasks.\n"
        final_task += "    f) PAGE LOAD TIMEOUT: If a page takes more than 30 seconds to load, stop waiting, try a refresh, and if still failing call mark_task_failed(task_id=X).\n"
        final_task += "    g) UNEXPECTED REDIRECTS: If you are redirected to an unexpected page (e.g., error page, maintenance page), report this in thinking and call mark_task_failed(task_id=X).\n"
        final_task += "    h) NEVER call mark_task_skipped for slider/text captcha WITHOUT first calling handle_verification_barrier.\n"
        final_task += "    i) If handle_verification_barrier reports 'solved', CONTINUE with the current task normally.\n"

        # 核心修复: 清理 task 长文本中的 URL，防止中文标点紧贴 URL 导致 browser-use 解析错误
        # 例如 "http://localhost:3000，" -> "http://localhost:3000 "
        try:
            # 在中文标点前加空格，避免它们成为 URL 的一部分
            final_task = re.sub(r'(https?://[^\s\u4e00-\u9fa5]+?)(?=[，；。、！])', r'\1 ', final_task)
            logger.info(f"🔧 Optimized task description for URL extraction")
        except:
            pass

        browser_profile = self._create_browser_profile()

        agent = Agent(
            task=final_task,
            llm=self.llm,
            controller=controller,
            browser_profile=browser_profile,
            use_vision=False,
            max_actions_per_step=10,  # 增加步进密度，减少总步骤数，降低超时风险
            max_retries=2,  # 2次重试，平衡速度与成功率
            max_failures=3,  # 3次失败后终止，避免偶发超时导致过早退出
            llm_timeout=60,  # 设置LLM调用超时为60秒（支持硅基流动等大模型API）
            step_timeout=120,  # 每步120秒，适配慢速页面
            generate_gif=self.enable_gif,  # 根据开关决定是否生成GIF
        )
        agent._task_was_done = False
        agent._pending_status_task_id = None
        agent._pending_status_task_description = None
        agent._auth_failure_task_id = None
        agent._auth_failure_count = 0

        # Callback helper - 添加任务标记跟踪
        last_processed_step = 0
        last_marked_task_id = 0  # 跟踪上一次标记的任务ID
        known_tab_ids = set()

        async def on_step_end(agent_instance):
            nonlocal last_processed_step, last_marked_task_id, known_tab_ids

            if should_stop:
                do_stop = await should_stop() if asyncio.iscoroutinefunction(should_stop) else should_stop()
                if do_stop: raise KeyboardInterrupt("User requested stop")

            if _task_was_done:
                raise KeyboardInterrupt("Done")

            history = getattr(agent_instance, 'history', [])
            if hasattr(history, 'history'): history = history.history

            if len(history) > last_processed_step:
                for i in range(last_processed_step, len(history)):
                    step = history[i]
                    # Log logic here
                    try:
                        actions = []
                        if hasattr(step, 'model_output') and hasattr(step.model_output, 'action'):
                            raw = step.model_output.action
                            actions = raw if isinstance(raw, list) else [raw]

                        current_active_task = get_next_active_task()
                        current_active_task_id = current_active_task.get('id') if current_active_task else None
                        current_active_task_desc = str(current_active_task.get('description', '')) if current_active_task else ''
                        if current_active_task_id and any(keyword in current_active_task_desc.lower() for keyword in ['登录', 'login']):
                            signal_text_parts = []
                            model_output = getattr(step, 'model_output', None)
                            for field_name in ['thinking', 'evaluation_previous_goal', 'memory', 'next_goal']:
                                value = getattr(model_output, field_name, None)
                                if value:
                                    signal_text_parts.append(str(value))

                            if _contains_auth_failure_signal(" ".join(signal_text_parts)):
                                if getattr(agent_instance, '_auth_failure_task_id', None) == current_active_task_id:
                                    agent_instance._auth_failure_count += 1
                                else:
                                    agent_instance._auth_failure_task_id = current_active_task_id
                                    agent_instance._auth_failure_count = 1

                                if agent_instance._auth_failure_count >= 3:
                                    logger.warning(
                                        f"⚠️ Login/auth failure threshold reached for task {current_active_task_id}; marking task failed"
                                    )
                                    await emit_callback({
                                        'type': 'log',
                                        'content': (
                                            f"\n[System]\n检测到登录连续失败 3 次，已自动将子任务 {current_active_task_id} 标记为失败并停止执行。\n"
                                        )
                                    })
                                    await emit_callback({
                                        'task_id': int(current_active_task_id),
                                        'status': 'failed'
                                    })
                                    raise KeyboardInterrupt("Repeated authentication failure")
                            elif getattr(agent_instance, '_auth_failure_task_id', None) == current_active_task_id:
                                agent_instance._auth_failure_count = 0

                        # 检查这一步是否调用了任务状态更新动作
                        step_has_task_complete = False
                        step_marked_task_id = None
                        for action in actions:
                            action_dict = action.model_dump() if hasattr(action, 'model_dump') else getattr(action,
                                                                                                            '_action_dict',
                                                                                                            {})
                            if 'mark_task_complete' in action_dict:
                                step_has_task_complete = True
                                step_marked_task_id = action_dict['mark_task_complete'].get('task_id')
                            elif 'mark_task_failed' in action_dict:
                                step_has_task_complete = True
                                step_marked_task_id = action_dict['mark_task_failed'].get('task_id')
                            elif 'mark_task_skipped' in action_dict:
                                step_has_task_complete = True
                                step_marked_task_id = action_dict['mark_task_skipped'].get('task_id')
                            elif 'update_task_status' in action_dict:
                                step_has_task_complete = True
                                payload = action_dict['update_task_status']
                                step_marked_task_id = payload.get('task_id')

                        if step_has_task_complete:
                            # 检查是否重复标记已终态的任务 - 自动跳过并推进到下一个任务
                            task_already_terminal = False
                            if planned_tasks:
                                for task in planned_tasks:
                                    if task['id'] == step_marked_task_id and task.get('status') in ['completed', 'failed', 'skipped']:
                                        next_expected = last_marked_task_id + 1 if last_marked_task_id else step_marked_task_id + 1
                                        logger.warning(
                                            f"⚠️ Task {step_marked_task_id} is already terminal ({task.get('status')})! "
                                            f"Auto-advancing to task {next_expected}.")
                                        # 自动推进 last_marked_task_id，使 Agent 跳过此终态任务
                                        last_marked_task_id = step_marked_task_id
                                        task_already_terminal = True
                                        break
                            if task_already_terminal:
                                # 清除 pending 状态，让 Agent 在下一次 step 中自然推进到下一个任务
                                if getattr(agent_instance, '_pending_status_task_id', None) == step_marked_task_id:
                                    agent_instance._pending_status_task_id = None
                                    agent_instance._pending_status_task_description = None
                                # 标记清除，不重复执行同一终态任务的状态变更
                                agent_instance._last_terminal_skip_info = {
                                    'skipped_task_id': step_marked_task_id,
                                    'next_expected': next_expected if planned_tasks else None
                                }
                                logger.info(f"⏭️ Skipped redundant mark on terminal task {step_marked_task_id}, continuing to next task.")
                                break
                            last_marked_task_id = step_marked_task_id
                            if getattr(agent_instance, '_pending_status_task_id', None) == step_marked_task_id:
                                agent_instance._pending_status_task_id = None
                                agent_instance._pending_status_task_description = None
                            break

                        # 检查这一步是否有实际操作（非mark_task_complete的操作）
                        has_real_action = False
                        has_link_open_action = False
                        for action in actions:
                            action_dict = action.model_dump() if hasattr(action, 'model_dump') else getattr(action,
                                                                                                            '_action_dict',
                                                                                                            {})
                            for key in action_dict.keys():
                                if key not in ['mark_task_complete', 'mark_task_failed', 'mark_task_skipped', 'update_task_status', 'done']:
                                    has_real_action = True
                                if key in ['click', 'open_new_tab', 'navigate', 'go_to_url']:
                                    has_link_open_action = True
                                    break
                            if has_real_action:
                                break

                        action_str = " | ".join([self._format_action(a) for a in actions])
                        log_content = f"\n[Step {i + 1}]\n执行: {action_str}\n"

                        if callback:
                            if asyncio.iscoroutinefunction(callback):
                                await callback({'type': 'log', 'content': log_content})
                            else:
                                callback({'type': 'log', 'content': log_content})

                        browser_session = getattr(agent_instance, 'browser_session', None)
                        if browser_session is not None:
                            try:
                                tabs = await browser_session.get_tabs()
                                current_tab_ids = {tab.target_id for tab in tabs}
                                if not known_tab_ids:
                                    known_tab_ids = current_tab_ids
                                else:
                                    new_tabs = [tab for tab in tabs if tab.target_id not in known_tab_ids]
                                    if new_tabs and has_link_open_action:
                                        newest_tab = new_tabs[-1]
                                        if browser_session.agent_focus_target_id != newest_tab.target_id:
                                            await browser_session.event_bus.dispatch(
                                                SwitchTabEvent(target_id=newest_tab.target_id)
                                            )
                                            logger.info(
                                                f"🔀 Auto-switched to newly opened tab {newest_tab.target_id[-4:]} after link click"
                                            )
                                            if callback:
                                                auto_switch_log = (
                                                    f"\n[System]\n检测到新标签页，已自动切换到 {newest_tab.target_id[-4:]}\n"
                                                )
                                                if asyncio.iscoroutinefunction(callback):
                                                    await callback({'type': 'log', 'content': auto_switch_log})
                                                else:
                                                    callback({'type': 'log', 'content': auto_switch_log})
                                    known_tab_ids = current_tab_ids
                            except Exception as tab_error:
                                logger.warning(f"⚠️ Failed to inspect/switch tabs after step {i + 1}: {tab_error}")

                        # 记录未标记任务的步骤（不自动修复，仅警告）
                        if has_real_action and not step_has_task_complete and planned_tasks:
                            next_expected_task_id = last_marked_task_id + 1
                            if next_expected_task_id <= len(planned_tasks):
                                # 检查这个任务是否还没有被标记
                                task_already_marked = False
                                for task in planned_tasks:
                                    if task['id'] == next_expected_task_id and task.get('status') in ['completed', 'failed', 'skipped']:
                                        task_already_marked = True
                                        last_marked_task_id = next_expected_task_id
                                        break

                                if not task_already_marked:
                                    # 记录警告，提示 AI 标记当前任务
                                    agent_instance._pending_status_task_id = next_expected_task_id
                                    pending_task_description = None
                                    if planned_tasks:
                                        for task in planned_tasks:
                                            if task.get('id') == next_expected_task_id:
                                                pending_task_description = task.get('description')
                                                break
                                    agent_instance._pending_status_task_description = pending_task_description
                                    logger.warning(
                                        f"⚠️ Step {i + 1} had actions but no task status update. "
                                        f"Please mark task {next_expected_task_id} as completed, failed, or skipped.")

                    except Exception as e:
                        logger.warning(f"⚠️ Error in on_step_end processing: {e}")

                    # ====== 每步截图 + 验证码自动检测与求解 ======
                    try:
                        screenshot_b64 = None
                        if hasattr(step, 'state'):
                            state = step.state
                            if hasattr(state, 'screenshot'):
                                screenshot_b64 = state.screenshot

                        if not screenshot_b64:
                            current_state = getattr(step, 'current_state', None)
                            if current_state and hasattr(current_state, 'screenshot'):
                                screenshot_b64 = current_state.screenshot

                        # 发送截图到回调（每步一张）
                        if screenshot_b64 and callback:
                            cb_data = {'type': 'screenshot', 'step': i + 1, 'data': screenshot_b64}
                            if asyncio.iscoroutinefunction(callback):
                                await callback(cb_data)
                            else:
                                callback(cb_data)

                        # StepRecorder：录制步骤截图 + AI描述 + 视频帧
                        try:
                            step_page = None
                            browser_session_val2 = getattr(agent_instance, 'browser_session', None)
                            if browser_session_val2 is not None:
                                try:
                                    step_page = await browser_session_val2.get_current_page()
                                except Exception:
                                    step_page = None
                            if step_page is not None:
                                step_action_desc = action_str if action_str else f"Step {i + 1}"
                                # 判断步骤状态
                                step_status = "executed"
                                if step_has_task_complete:
                                    # 检查是completed/failed/skipped
                                    for a in actions:
                                        ad = a.model_dump() if hasattr(a, 'model_dump') else getattr(a, '_action_dict', {})
                                        if 'mark_task_failed' in ad:
                                            step_status = "failed"
                                            break
                                        elif 'mark_task_skipped' in ad:
                                            step_status = "skipped"
                                            break
                                        elif 'mark_task_complete' in ad:
                                            step_status = "passed"
                                            break
                                if step_recorder:
                                    await step_recorder.capture_step(
                                        page=step_page,
                                        step_description=step_action_desc,
                                        step_status=step_status,
                                        action_type=', '.join(list(next(iter(
                                            (a.model_dump() if hasattr(a, 'model_dump') else getattr(a, '_action_dict', {})).keys()
                                        ) for a in actions)) if actions else ''),
                                    )
                        except Exception as rec_err:
                            logger.debug(f"StepRecorder capture skipped: {rec_err}")

                        # 验证码自动检测
                        captcha_warning = None
                        captcha_type_detected = None

                        # 1. 从 step.state 的 HTML 中检测
                        if hasattr(step, 'state') and hasattr(step.state, 'html_content'):
                            html_content = getattr(step.state, 'html_content', '')
                            if html_content:
                                from .captcha_handler import detect_captcha, get_captcha_handling_prompt
                                has_captcha, captcha_type_detected = detect_captcha(str(html_content))
                                if has_captcha:
                                    captcha_warning = get_captcha_handling_prompt(captcha_type_detected)

                        # 1.5. 也搜索 iframe 内的 HTML（验证码经常在 iframe 中）
                        if not captcha_warning and hasattr(step, 'state'):
                            try:
                                if browser_session_val := getattr(agent_instance, 'browser_session', None):
                                    page = await browser_session_val.get_current_page()
                                    if page:
                                        from .captcha_handler import _get_all_captcha_frames, detect_captcha, get_captcha_handling_prompt
                                        captcha_frames = await _get_all_captcha_frames(page)
                                        for fi in captcha_frames:
                                            if fi['name'] == 'main':
                                                continue
                                            try:
                                                frame_html = await fi['frame'].content()
                                                has_captcha, captcha_type_detected = detect_captcha(frame_html)
                                                if has_captcha:
                                                    captcha_warning = get_captcha_handling_prompt(captcha_type_detected)
                                                    break
                                            except Exception:
                                                pass
                            except Exception as frame_err:
                                logger.debug(f"iframe captcha detection skipped: {frame_err}")

                        # 2. 从 model_output 的 thinking 中检测
                        if not captcha_warning and hasattr(step, 'model_output'):
                            mo = step.model_output
                            thinking = getattr(mo, 'thinking', '') or str(mo)
                            captcha_signals = ['验证码', 'captcha', 'verify', '滑块', '人机验证',
                                             'recaptcha', '图形验证', '请输入验证']
                            if any(s in str(thinking).lower() for s in captcha_signals):
                                captcha_warning = (
                                    "\n⚠️ 当前页面可能包含验证码，自动化引擎正在尝试自动解决..."
                                    "\n  - 请等待自动化引擎处理结果，不要立即调用 mark_task_skipped"
                                    "\n  - 如果持续被阻塞，调用 handle_verification_barrier 获取帮助"
                                    "\n  - Cookie弹窗：点击同意后继续"
                                )

                        if captcha_warning and callback:
                            try:
                                from .ai_diagnostics import diagnose_page_issue
                                from .captcha_handler import CaptchaHandler, detect_captcha, captcha_block_reason
                                html_for_diagnosis = ''
                                if hasattr(step, 'state') and hasattr(step.state, 'html_content'):
                                    html_for_diagnosis = str(getattr(step.state, 'html_content', '') or '')
                                thinking_for_diagnosis = ''
                                if hasattr(step, 'model_output'):
                                    mo = step.model_output
                                    thinking_for_diagnosis = str(getattr(mo, 'thinking', '') or mo)

                                action_lines = ['\n[VERIFICATION_HANDLER]', '- reason: captcha_or_verification_detected']
                                browser_session_val = getattr(agent_instance, 'browser_session', None)
                                page = None
                                page_html_after = html_for_diagnosis
                                captcha_solved = False

                                if browser_session_val is not None:
                                    try:
                                        page = await browser_session_val.get_current_page()
                                    except Exception:
                                        page = None

                                if page is not None:
                                    # Step 1: Dismiss overlays
                                    try:
                                        overlay_closed = await CaptchaHandler.dismiss_common_overlays(page)
                                        action_lines.append(f'- overlay_dismiss_attempted: {overlay_closed}')
                                        if overlay_closed:
                                            await asyncio.sleep(0.5)
                                            try:
                                                page_html_after = await page.content()
                                            except Exception:
                                                pass
                                    except Exception as overlay_error:
                                        action_lines.append(f'- overlay_error: {overlay_error}')

                                    # Step 2: Re-detect captcha type after overlay dismiss
                                    has_cap, cap_type = detect_captcha(page_html_after or html_for_diagnosis or thinking_for_diagnosis)
                                    action_lines.append(f'- detected_type: {cap_type or "none"}')

                                    # Step 3: Auto-solve based on type
                                    if has_cap and cap_type not in ('third_party_captcha', 'sms_verify'):
                                        try:
                                            solved, detail = await CaptchaHandler.auto_handle_captcha(page, cap_type)
                                            captcha_solved = solved
                                            action_lines.append(f'- auto_solve_action: {detail}')
                                            if solved:
                                                action_lines.append(f'- auto_solve_result: solved')
                                                try:
                                                    await asyncio.sleep(1.0)
                                                    page_html_after = await page.content()
                                                    has_cap, cap_type = detect_captcha(page_html_after)
                                                except Exception:
                                                    pass
                                            else:
                                                action_lines.append(f'- auto_solve_result: failed')
                                        except Exception as auto_error:
                                            action_lines.append(f'- auto_solve_error: {auto_error}')

                                    if captcha_solved:
                                        action_lines.append('- result: captcha_automatically_solved')
                                        action_lines.append('- policy: 验证码已被自动化引擎解决，请继续执行')
                                    elif has_cap:
                                        action_lines.append(f'- result: blocked_by_{cap_type}')
                                        action_lines.append(f'- policy: {captcha_block_reason(cap_type)}')
                                        # 逆向分析验证码 API
                                        if page is not None and cap_type in ('slider_captcha', 'general_captcha'):
                                            try:
                                                from .captcha_reverse import analyze_and_capture_captcha_api
                                                api_info = await analyze_and_capture_captcha_api(page)
                                                if api_info.get('widget_type') != 'unknown':
                                                    action_lines.append(f'- reverse_widget: {api_info["widget_type"]}')
                                                if api_info.get('api_endpoints'):
                                                    action_lines.append(f'- reverse_endpoints: {api_info["api_endpoints"][:3]}')
                                            except Exception:
                                                pass
                                    else:
                                        action_lines.append('- result: verification_barrier_cleared_or_not_present')

                                if captcha_solved:
                                    diagnosis_log = '\n'.join(action_lines) + (
                                        "\n[AI_DIAGNOSIS]\n"
                                        f"- issue_type: resolved\n"
                                        f"- evidence: 自动化引擎已成功解决{captcha_type_detected or '未知'}验证码\n"
                                        f"- cause: n/a\n"
                                        f"- recommended_action: CONTINUE with current task - captcha has been solved\n"
                                        f"- requires_human: no\n"
                                        f"- status_suggestion: in_progress\n"
                                        f"- source: automation_engine"
                                    )
                                else:
                                    diagnosis_log, _diagnosis = await diagnose_page_issue(
                                        reason='captcha_or_verification_detected',
                                        page_html=page_html_after or html_for_diagnosis,
                                        action_context='\n'.join(action_lines + [thinking_for_diagnosis]),
                                        planned_tasks=planned_tasks,
                                        max_tokens=700,
                                    )
                                    diagnosis_log = '\n'.join(action_lines) + diagnosis_log
                            except Exception as diagnosis_error:
                                logger.debug(f"AI captcha handling/diagnosis skipped: {diagnosis_error}")
                                diagnosis_log = captcha_warning
                            if asyncio.iscoroutinefunction(callback):
                                await callback({'type': 'log', 'content': diagnosis_log})
                            else:
                                callback({'type': 'log', 'content': diagnosis_log})

                    except Exception as cap_err:
                        logger.debug(f"截图/验证码检测跳过（非致命）: {cap_err}")
                    # ====== 截图+验证码检测结束 ======

                last_processed_step = len(history)

        agent_run_error = None
        try:
            # Try to pass callback
            import inspect
            sig = inspect.signature(agent.run)
            if 'on_step_end' in sig.parameters:
                await agent.run(max_steps=100, on_step_end=on_step_end)
            else:
                await agent.run(max_steps=100)
        except KeyboardInterrupt:
            logger.info("⏸️ Agent execution interrupted by user (KeyboardInterrupt)")
            pass
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            agent_run_error = e
        finally:
            # ================================================================
            # 【关键修复】StepRecorder 保底导出：无论任务正常结束、中断还是异常，
            # 都确保已有的步骤截图和录屏文件生成并推送。
            # ================================================================
            history = getattr(agent, 'history', [])
            if history:
                logger.info("🔍 Performing final task status consistency check")
                executed_tasks_info = self._find_executed_tasks(history)
                if (
                    executed_tasks_info
                    and executed_tasks_info.get('executed_actions', 0) > len(executed_tasks_info.get('marked_tasks', []))
                    and executed_tasks_info.get('unmarked_actions')
                ):
                    logger.warning(
                        f"⚠️ Found {executed_tasks_info['executed_actions']} executed actions, but only {len(executed_tasks_info['marked_tasks'])} tasks were explicitly marked complete")
                    logger.warning(f"⚠️ Unmarked actions: {executed_tasks_info['unmarked_actions']}")
                    logger.warning("⚠️ This indicates the AI agent did not follow the 'mark_task_complete' rule properly.")

            # StepRecorder 导出报告（Word文档 + MP4视频）
            # 即使在异常中断时，仍导出已捕获的步骤截图和录屏
            if step_recorder:
                step_summary = step_recorder.get_summary()
                logger.info(f"📊 StepRecorder 摘要: 共 {step_summary.get('total_steps', 0)} 步, 通过率 {step_summary.get('pass_rate', 0)}%")

                if step_summary.get('total_steps', 0) > 0:
                    try:
                        word_path = step_recorder.export_word_docx()
                        if word_path:
                            logger.info(f"📄 Word 报告已导出: {word_path}")
                    except Exception as e:
                        logger.warning(f"Word 报告导出失败: {e}")

                    try:
                        video_path = step_recorder.export_video_mp4(fps=8)
                        if video_path:
                            logger.info(f"🎬 MP4 视频已导出: {video_path}")
                    except Exception as e:
                        logger.warning(f"MP4 视频导出失败: {e}")

                    # 将 StepRecorder 数据附加到 history 上供调用方使用
                    try:
                        from types import SimpleNamespace
                        if not isinstance(history, SimpleNamespace):
                            history._step_recorder = step_recorder.to_dict()
                    except Exception:
                        pass
            else:
                step_summary = None

        # 如果有执行错误，在确保 StepRecorder 导出后再抛出
        if agent_run_error:
            raise agent_run_error

        return history

    def _find_executed_tasks(self, history):
        """
        通过分析执行历史找出已执行但未标记完成的任务
        """
        if not history or not hasattr(history, 'steps'):
            return []

        executed_actions = {}  # 已执行的操作类型和索引，以及对应的步骤
        marked_tasks = set()  # 已标记完成的任务ID

        # 分析执行历史
        for step_idx, step in enumerate(getattr(history, 'steps', [])):
            # 检查每一步中的actions
            actions = getattr(step, 'actions', [])
            for action in actions:
                # 记录已执行的操作
                if hasattr(action, 'input'):
                    action_key = f"input_{action.input.index}"
                    executed_actions[action_key] = {
                        'step': step_idx,
                        'action': 'input',
                        'index': action.input.index
                    }
                elif hasattr(action, 'click'):
                    action_key = f"click_{action.click.index}"
                    executed_actions[action_key] = {
                        'step': step_idx,
                        'action': 'click',
                        'index': action.click.index
                    }
                elif hasattr(action, 'switch_tab'):
                    action_key = f"switch_tab_{action.switch_tab.tab_id}"
                    executed_actions[action_key] = {
                        'step': step_idx,
                        'action': 'switch_tab',
                        'tab_id': action.switch_tab.tab_id
                    }

                # 记录已标记完成的任务
                if hasattr(action, 'mark_task_complete'):
                    marked_tasks.add(action.mark_task_complete.task_id)

        # 理想情况下应该有一个映射机制来关联操作和任务，但由于我们没有这个映射，
        # 我们只能记录未标记完成的执行操作作为调试信息
        unmarked_actions = []
        for action_key, action_info in executed_actions.items():
            unmarked_actions.append({
                'action': action_info['action'],
                'step': action_info['step'],
                'details': action_key
            })

        return {
            'marked_tasks': list(marked_tasks),
            'executed_actions': len(executed_actions),
            'unmarked_actions': unmarked_actions
        }

    async def run_full_process(self, task_description: str, analysis_callback=None, step_callback=None,
                               should_stop=None, url: str = None, custom_headers: list = None,
                               testcase_callback=None):
        """
        增强版全流程执行：
        1. 如果提供了 URL，先爬取网站 + AI 生成测试用例
        2. 否则使用原有的 analyze_task 拆解任务
        3. 按测试用例执行

        Args:
            url: 目标网站 URL
            custom_headers: 自定义测试用例表头
            testcase_callback: 测试用例生成完成后的回调
        """
        # 如果有 URL 且非纯步骤描述，使用 TestPlanGenerator 生成结构化测试用例
        if url and task_description and not self._is_pure_step_description(task_description):
            try:
                from .test_plan_generator import TestPlanGenerator

                logger.info(f"🔍 开始分析网站 {url} 并生成测试用例...")
                generator = TestPlanGenerator(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model_name=self.model_name,
                )

                test_cases = await generator.generate_test_cases(
                    url=url,
                    requirement_description=task_description,
                    custom_headers=custom_headers,
                )

                if test_cases and len(test_cases) >= 2:
                    logger.info(f"✅ 成功生成 {len(test_cases)} 条结构化测试用例")

                    # 通知前端测试用例已生成
                    if testcase_callback:
                        if asyncio.iscoroutinefunction(testcase_callback):
                            await testcase_callback(test_cases)
                        else:
                            testcase_callback(test_cases)

                    # 将测试用例转换为执行步骤
                    planned_tasks = self._testcases_to_planned_tasks(test_cases)

                    if analysis_callback:
                        if asyncio.iscoroutinefunction(analysis_callback):
                            await analysis_callback(planned_tasks)
                        else:
                            analysis_callback(planned_tasks)

                    # 构建执行描述
                    markdown_tc = generator.format_as_markdown(test_cases, custom_headers)
                    enhanced_task = (
                        f"请严格按照以下测试用例执行自动化测试：\n\n"
                        f"目标网址: {url}\n\n"
                        f"【测试用例列表】\n{markdown_tc}\n\n"
                        f"用户需求: {task_description}\n\n"
                        f"执行规则:\n"
                        f"1. 按用例顺序依次执行，每完成一条用例后立即调用 mark_task_complete\n"
                        f"2. 如遇到验证码/图形验证等无法自动处理的验证，调用 mark_task_skipped\n"
                        f"3. 如遇到登录失败（如用户名密码错误），调用 mark_task_failed 并停止重试\n"
                        f"4. 注意页面加载超时、弹窗遮挡等异常情况"
                    )

                    return await self.run_task(enhanced_task, planned_tasks, step_callback, should_stop)
                else:
                    logger.warning("⚠️ 生成的测试用例不足，降级为原始分析模式")

            except Exception as e:
                logger.warning(f"⚠️ 测试用例生成失败: {e}，降级为原始分析模式")

        # 降级：使用原有的任务拆解方式
        planned_tasks = await self.analyze_task(task_description)
        if analysis_callback:
            if asyncio.iscoroutinefunction(analysis_callback):
                await analysis_callback(planned_tasks)
            else:
                analysis_callback(planned_tasks)

        return await self.run_task(task_description, planned_tasks, step_callback, should_stop)

    @staticmethod
    def _is_pure_step_description(text: str) -> bool:
        """判断输入是否已经是纯步骤描述（无需生成测试用例）"""
        if not text:
            return True
        # 如果文本中已经有很多数字编号步骤，说明用户直接提供了步骤
        numbered_count = len(re.findall(r'^\s*\d+[\.\s、:：-]', text, re.MULTILINE))
        return numbered_count >= 3

    def _testcases_to_planned_tasks(self, test_cases: list) -> list:
        """将测试用例列表转换为执行计划步骤（兼容新旧字段名及自定义表头）"""
        tasks = []
        for tc in test_cases:
            # 兼容多种字段名格式（包括用户自定义表头）
            tc_id = (
                tc.get("ID") or tc.get("id") or tc.get("序号") or tc.get("用例ID")
                or tc.get("用例编号") or f"TC_{len(tasks) + 1}"
            )
            title = (
                tc.get("测试目标") or tc.get("用例标题") or tc.get("测试模块")
                or tc.get("模块") or tc.get("目标") or ""
            )
            scenario = (
                tc.get("测试类型") or tc.get("用例类型") or tc.get("关联模块")
                or tc.get("测试场景") or tc.get("模块") or ""
            )
            precondition = (
                tc.get("前置条件") or tc.get("前置") or tc.get("前置要求") or ""
            )
            steps = (
                tc.get("执行步骤") or tc.get("操作步骤") or tc.get("测试步骤")
                or tc.get("步骤") or ""
            )
            expected = (
                tc.get("预期结果") or tc.get("预期") or tc.get("期望结果") or ""
            )
            priority = (
                tc.get("优先级") or tc.get("级别") or tc.get("紧急度") or "P1"
            )

            if isinstance(steps, list):
                steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
            if isinstance(expected, list):
                expected = "\n".join(f"{i+1}. {e}" for i, e in enumerate(expected))

            desc = (
                f"#{tc_id} {title} [{priority}]\n"
                f"场景: {scenario}\n"
                f"前置: {precondition}\n"
                f"步骤:\n{steps}\n"
                f"预期: {expected}"
            )
            tasks.append({
                'id': int(tc_id) if str(tc_id).isdigit() else len(tasks) + 1,
                'description': desc,
                'status': 'pending'
            })
        return tasks
