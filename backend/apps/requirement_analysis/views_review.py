"""
需求评审与测试用例生成 - 优化版
- 支持SSE流式输出，实时显示思考过程
- 思考过程：AI推理步骤、需求拆解、覆盖度思考等
- 内置本地降级方案（AI不可用时仍可工作）
- 解决了之前 review_requirement hang 住的问题
"""
import asyncio
import json
import logging
import re
import time
from typing import AsyncIterator, Dict, Any, List, Optional

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


# ============================================================
# 思考过程生成器
# ============================================================
class ThinkingProcessGenerator:
    """
    生成AI评审的"思考过程"
    模拟 Chain of Thought：让用户看到 AI 是如何一步步分析需求的
    """

    @staticmethod
    def generate_thinking_steps(requirement_text: str, title: str, target_url: str = "") -> List[Dict[str, str]]:
        """
        生成结构化的思考步骤
        返回: [{'phase': '阶段名', 'thought': '思考内容', 'detail': '细节'}, ...]
        """
        steps = []
        text_len = len(requirement_text or '')
        word_count = text_len  # 中文按字符计

        # 1. 需求分析
        steps.append({
            'phase': '1️⃣ 需求接收',
            'thought': '已接收到用户提交的需求文档',
            'detail': f'标题：{title or "(未提供)"}\n内容长度：{text_len} 字符',
        })

        # 2. 关键词提取
        keywords = ThinkingProcessGenerator._extract_keywords(requirement_text or '')
        steps.append({
            'phase': '2️⃣ 关键词提取',
            'thought': '正在从需求中提取核心功能关键词',
            'detail': f'识别到关键词：{", ".join(keywords[:10]) if keywords else "（未能识别到具体关键词）"}',
        })

        # 3. 模块识别
        modules = ThinkingProcessGenerator._extract_modules(requirement_text or '')
        steps.append({
            'phase': '3️⃣ 功能模块识别',
            'thought': '正在识别需求涉及的功能模块',
            'detail': f'涉及模块：{", ".join(modules) if modules else "未明确指定模块"}',
        })

        # 4. 测试维度
        steps.append({
            'phase': '4️⃣ 测试维度规划',
            'thought': '规划测试覆盖维度，确保不遗漏关键场景',
            'detail': '将覆盖：\n  ✓ 功能正向流程\n  ✓ 异常输入处理\n  ✓ 边界值与极值\n  ✓ 权限与安全\n  ✓ UI交互体验\n  ✓ 性能与并发',
        })

        # 5. 目标站点
        if target_url:
            steps.append({
                'phase': '5️⃣ 目标站点分析',
                'thought': '已检测到目标URL，将基于实际网页元素生成用例',
                'detail': f'目标URL：{target_url}',
            })
        else:
            steps.append({
                'phase': '5️⃣ 目标站点分析',
                'thought': '未指定目标URL，将基于需求文本生成通用测试用例',
                'detail': '建议：在需求中补充目标URL以获得更精准的用例',
            })

        # 6. 评审思路
        steps.append({
            'phase': '6️⃣ 评审思路',
            'thought': '开始进入深度评审，从完整性、可测试性、风险、建议四个维度展开',
            'detail': '评审方法：资深QA专家多角度审视 + AI 交叉验证',
        })

        return steps

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """从文本中提取关键词（简单实现）"""
        if not text:
            return []
        # 常见测试关键词
        keyword_patterns = [
            r'登录|注册|登出|注销',
            r'查询|搜索|筛选|过滤',
            r'新增|添加|创建|删除|编辑|修改|更新',
            r'提交|保存|确认|取消',
            r'支付|付款|结算|退款|订单',
            r'上传|下载|导入|导出',
            r'权限|角色|用户|管理员',
            r'表单|输入|输出|按钮',
            r'消息|通知|提醒|推送',
            r'验证码|密码|加密|解密',
        ]
        found = []
        for p in keyword_patterns:
            m = re.search(p, text)
            if m:
                found.append(m.group())
        return list(dict.fromkeys(found))  # 去重保序

    @staticmethod
    def _extract_modules(text: str) -> List[str]:
        """识别功能模块"""
        module_keywords = ['登录', '注册', '用户', '订单', '支付', '商品', '购物车', '个人中心',
                          '管理', '权限', '角色', '消息', '通知', '首页', '列表', '详情',
                          '搜索', '设置', '数据', '报表', '统计', '文件', '图片', '视频']
        found = []
        for mk in module_keywords:
            if mk in (text or ''):
                found.append(f'{mk}模块')
        return list(dict.fromkeys(found))


# ============================================================
# 流式响应辅助
# ============================================================
async def sse_event(event_type: str, data: Any) -> str:
    """生成SSE事件"""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


async def run_review_with_thinking(title: str, requirement_text: str, target_url: str) -> AsyncIterator[str]:
    """
    流式执行需求评审，输出思考过程
    """
    try:
        # === 阶段1：思考过程展示 ===
        thinking_steps = ThinkingProcessGenerator.generate_thinking_steps(requirement_text, title, target_url)

        for step in thinking_steps:
            # 每个思考步骤作为独立事件推送
            yield await sse_event('thinking', {
                'phase': step['phase'],
                'thought': step['thought'],
                'detail': step['detail'],
                'timestamp': time.time(),
            })
            # 让前端有动画展示的时间
            await asyncio.sleep(0.3)

        # === 阶段2：调用 AI 进行实际评审 ===
        yield await sse_event('status', {'stage': 'ai_review', 'message': '正在调用AI专家进行深度评审...'})

        from .models import AIModelService

        review_prompt = f"""你是一位资深测试需求评审专家。请对以下需求进行专业评审，分析其完整性、清晰度和可测试性。

{('需求标题: ' + title) if title else ''}
需求内容:
{requirement_text}

{'目标站点: ' + target_url if target_url else ''}

请从以下维度进行评审并提供建议：
1. **需求完整性**：是否覆盖了所有必要的功能描述、用户场景和边界条件？
2. **可测试性**：需求是否足够具体、可量化，能否据此设计测试用例？
3. **潜在风险**：是否存在描述不清、逻辑矛盾或遗漏的异常场景？
4. **测试建议**：针对该需求，推荐哪些测试策略和重点测试区域？

请以结构化的 Markdown 格式输出评审结果，并在最后给出一个综合评分（1-10分）及是否建议进入用例生成阶段。"""

        ai_result = None
        ai_error = None

        # 尝试调用AI
        try:
            yield await sse_event('status', {'stage': 'ai_calling', 'message': 'AI正在分析（最长等待25秒，超时自动降级）...'})

            # 使用 asyncio.wait_for 强制超时
            # 说明：由于用户反馈"长时间无反应"，将超时从 120s 降到 25s
            #      AI 不可用时快速降级到本地规则化评审，用户体验优先
            ai_result, _ = await asyncio.wait_for(
                AIModelService.call_with_auto_model_from_roles(
                    roles=['reviewer', 'writer'],
                    messages=[{'role': 'user', 'content': review_prompt}],
                    overall_timeout=22.0,   # 累计尝试 22 秒
                    per_config_timeout=18.0,  # 单个配置 18 秒
                ),
                timeout=25.0
            )
        except asyncio.TimeoutError:
            ai_error = "AI评审超时（超过25秒），已切换到本地降级方案"
            logger.warning(f"AI评审超时: {title}")
        except Exception as e:
            ai_error = f"AI评审失败: {str(e)[:200]}"
            logger.warning(f"AI评审失败: {e}")

        # === 阶段3：输出结果 ===
        requirement_review = ''
        if ai_result and isinstance(ai_result, dict):
            choices = ai_result.get('choices', [])
            if choices:
                requirement_review = choices[0].get('message', {}).get('content', '')

        if not requirement_review:
            # 降级方案：本地规则化评审（不依赖AI也能工作）
            requirement_review = generate_local_review(title, requirement_text, target_url, ai_error)

        # 流式推送最终评审内容（模拟打字机效果）
        yield await sse_event('status', {'stage': 'ai_complete', 'message': '评审完成'})

        # 将评审内容分片推送
        chunk_size = 50
        for i in range(0, len(requirement_review), chunk_size):
            chunk = requirement_review[i:i+chunk_size]
            yield await sse_event('review_chunk', {'content': chunk})
            await asyncio.sleep(0.02)  # 50ms每片

        # 推送最终结果
        yield await sse_event('done', {
            'requirement_review': requirement_review,
            'target_url': target_url,
            'used_fallback': bool(ai_error),
            'fallback_reason': ai_error or '',
        })

    except Exception as e:
        logger.error(f"流式评审失败: {e}", exc_info=True)
        # 推送错误
        yield await sse_event('error', {
            'message': f'评审过程异常: {str(e)}',
            'requirement_review': f'❌ 评审异常: {str(e)}\n\n请稍后重试或联系管理员。',
        })


def generate_local_review(title: str, requirement_text: str, target_url: str, error_msg: Optional[str] = None) -> str:
    """
    本地降级评审 - 不依赖 AI
    基于规则生成结构化评审报告
    """
    lines = []
    lines.append('# 📋 需求评审报告（本地规则化生成）')
    lines.append('')
    if error_msg:
        lines.append(f'> ⚠️ **AI评审服务暂不可用**：`{error_msg}`  \n> 已自动切换到本地规则化评审')
        lines.append('')

    if title:
        lines.append(f'**评审对象**：{title}')
    if target_url:
        lines.append(f'**目标站点**：{target_url}')
    lines.append(f'**评审时间**：{time.strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append(f'**需求文本长度**：{len(requirement_text or "")} 字符')
    lines.append('')
    lines.append('---')
    lines.append('')

    # 1. 需求完整性
    lines.append('## 1. 需求完整性评估')
    text = requirement_text or ""
    has_login = '登录' in text or '注册' in text
    has_query = '查询' in text or '搜索' in text or '列表' in text
    has_form = '表单' in text or '输入' in text or '提交' in text
    has_pagination = '分页' in text or '页码' in text
    has_exception = '异常' in text or '错误' in text or '失败' in text or '边界' in text

    completeness = []
    if has_login:
        completeness.append('✅ 已覆盖用户认证场景')
    else:
        completeness.append('⚠️ 未提及用户登录/注册场景')
    if has_query:
        completeness.append('✅ 已覆盖数据查询场景')
    else:
        completeness.append('⚠️ 未提及查询/搜索场景')
    if has_form:
        completeness.append('✅ 已覆盖表单交互场景')
    else:
        completeness.append('⚠️ 未提及表单输入场景')
    if has_pagination:
        completeness.append('✅ 已覆盖分页场景')
    else:
        completeness.append('⚠️ 未提及分页场景（建议补充）')
    if has_exception:
        completeness.append('✅ 已关注异常/边界场景')
    else:
        completeness.append('⚠️ 未明确异常/边界场景（强烈建议补充）')

    for c in completeness:
        lines.append(f'- {c}')
    lines.append('')

    # 2. 可测试性
    lines.append('## 2. 可测试性评估')
    testability = []
    testability.append('✅ 需求文本结构清晰，可据此设计测试用例')
    testability.append('✅ 可拆解为多个独立的功能测试点')
    if target_url:
        testability.append(f'✅ 已提供目标URL，可结合实际页面元素设计用例')
    else:
        testability.append('⚠️ 未提供目标URL，建议补充以便基于真实页面生成用例')
    if len(text) < 100:
        testability.append('⚠️ 需求描述偏短，可能存在遗漏，建议补充更多细节')
    else:
        testability.append('✅ 需求描述较为详细')
    for t in testability:
        lines.append(f'- {t}')
    lines.append('')

    # 3. 潜在风险
    lines.append('## 3. 潜在风险分析')
    risks = [
        '⚠️ 数据一致性风险：新增/修改/删除操作需注意数据完整性',
        '⚠️ 权限控制风险：不同角色用户看到的内容应不同',
        '⚠️ 并发操作风险：多用户同时操作可能导致状态错乱',
        '⚠️ 网络异常风险：断网、超时、错误响应需有友好提示',
        '⚠️ 输入校验风险：特殊字符、超长输入、SQL注入等需校验',
        '⚠️ 性能风险：大数据量查询、复杂计算可能存在性能问题',
    ]
    for r in risks:
        lines.append(f'- {r}')
    lines.append('')

    # 4. 测试建议
    lines.append('## 4. 测试策略建议')
    strategies = [
        '🎯 **功能测试**：覆盖所有正常业务流程，每一步都要可独立验证',
        '🎯 **异常测试**：所有输入框都要测试空值、超长、特殊字符、SQL注入',
        '🎯 **边界测试**：最小值、最大值、临界值、首尾值',
        '🎯 **UI测试**：检查提示文案、按钮可点击性、页面跳转、返回逻辑',
        '🎯 **权限测试**：未登录、低权限、高权限用户访问同一接口的差异',
        '🎯 **兼容测试**：不同浏览器、分辨率、设备类型（如果适用）',
        '🎯 **性能测试**：首屏加载、大数据量列表、并发请求',
    ]
    for s in strategies:
        lines.append(f'- {s}')
    lines.append('')

    # 5. 评分
    score = 7
    if not target_url:
        score -= 1
    if len(text) < 100:
        score -= 1
    if has_exception:
        score += 1

    lines.append('## 5. 综合评分')
    lines.append(f'**评分：{score}/10**  \n建议：**可进入测试用例生成阶段**')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('💡 点击"采纳评审，开始生成用例"按钮继续。')

    return '\n'.join(lines)


# ============================================================
# 视图
# ============================================================
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # SSE接口允许跨域访问
def review_requirement_stream(request):
    """
    流式需求评审（SSE）
    实时推送思考过程 + 评审内容
    """
    if request.method == 'GET':
        # GET 用于 EventSource（无法自定义header）
        data = request.query_params
    else:
        data = request.data

    title = data.get('title', '')
    requirement_text = data.get('requirement_text', '')
    target_url = data.get('target_url', '')

    if not (requirement_text or '').strip():
        async def err_gen():
            yield await sse_event('error', {'message': '需求文本不能为空'})
        return StreamingHttpResponse(err_gen(), content_type='text/event-stream')

    # 自动提取URL
    if not target_url:
        url_match = re.search(r'https?://[^\s，,。\n]+', requirement_text or '')
        if url_match:
            target_url = url_match.group()

    async def event_stream():
        # 使用 heartbeat 保证前端不会因为 AI 慢导致断开
        # 做法：用一个 asyncio.Queue 收集事件，同时后台每 3 秒推一次心跳
        queue: asyncio.Queue = asyncio.Queue()

        async def producer():
            try:
                async for chunk in run_review_with_thinking(title, requirement_text, target_url):
                    await queue.put(chunk)
            except Exception as e:
                logger.error(f"评审 producer 异常: {e}", exc_info=True)
                try:
                    err = await sse_event('error', {'message': f'评审异常: {str(e)}'})
                    await queue.put(err)
                except Exception:
                    pass
            finally:
                await queue.put(None)  # 结束信号

        task = asyncio.create_task(producer())
        try:
            while True:
                try:
                    # 3秒未收到消息就发一个 SSE 注释作为心跳
                    chunk = await asyncio.wait_for(queue.get(), timeout=3.0)
                except asyncio.TimeoutError:
                    # SSE 注释格式：以冒号开头的行会被前端 EventSource 忽略，但保持连接活跃
                    yield ": heartbeat\n\n"
                    continue
                if chunk is None:
                    break
                yield chunk
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except Exception:
                    pass

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def review_requirement_sync(request):
    """
    同步版本的需求评审（兼容老接口）
    内部使用流式生成，但一次性返回最终结果
    """
    import asyncio
    title = request.data.get('title', '')
    requirement_text = request.data.get('requirement_text', '')
    target_url = request.data.get('target_url', '')

    if not (requirement_text or '').strip():
        return Response({'error': '需求文本不能为空'}, status=status.HTTP_400_BAD_REQUEST)

    if not target_url:
        url_match = re.search(r'https?://[^\s，,。\n]+', requirement_text or '')
        if url_match:
            target_url = url_match.group()

    # 收集所有SSE事件为最终结果
    thinking_steps = []
    requirement_review = ''
    used_fallback = False
    fallback_reason = ''

    async def collect():
        nonlocal requirement_review, used_fallback, fallback_reason
        async for chunk in run_review_with_thinking(title, requirement_text, target_url):
            if 'event: thinking' in chunk:
                m = re.search(r'data: ({.*})', chunk)
                if m:
                    thinking_steps.append(json.loads(m.group(1)))
            elif 'event: done' in chunk:
                m = re.search(r'data: ({.*})', chunk)
                if m:
                    data = json.loads(m.group(1))
                    requirement_review = data.get('requirement_review', '')
                    used_fallback = data.get('used_fallback', False)
                    fallback_reason = data.get('fallback_reason', '')

    # 在新线程中运行async
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(collect())
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()
    except Exception as e:
        logger.error(f"同步评审失败: {e}", exc_info=True)
        return Response({
            'error': f'评审失败: {str(e)}',
            'requirement_review': f'❌ 评审异常: {str(e)}',
            'thinking_process': thinking_steps,
            'used_fallback': True,
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({
        'requirement_review': requirement_review,
        'target_url': target_url,
        'thinking_process': thinking_steps,
        'used_fallback': used_fallback,
        'fallback_reason': fallback_reason,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """健康检查 - 用于前端判断后端是否在线"""
    return Response({
        'status': 'ok',
        'service': 'requirement_review',
        'timestamp': time.time(),
    })
