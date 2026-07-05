"""
全程自动化 - 测试计划生成器（增强版，仿软测分析流程）
功能：
  1. 深度爬取目标网站（多页面、表单元素、交互元素）
  2. 使用 tester.md 风格 prompt 生成高覆盖测试用例
  3. 深度遍历策略 + 场景扩展库
  4. 生成结构化 Markdown 表格格式的测试用例
  5. 支持自定义模板头 / 默认模板头
"""
import logging
import json
import re
import asyncio
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger('django')



def C(points):
    return ''.join(chr(p) for p in points)


ZH = {
    'case_id': C([0x7528, 0x4f8b, 0x49, 0x44]),
    'case_no': C([0x7528, 0x4f8b, 0x7f16, 0x53f7]),
    'number': C([0x7f16, 0x53f7]),
    'seq': C([0x5e8f, 0x53f7]),
    'precondition': C([0x524d, 0x7f6e, 0x6761, 0x4ef6]),
    'pre': C([0x524d, 0x7f6e]),
    'module': C([0x6a21, 0x5757]),
    'test_module': C([0x6d4b, 0x8bd5, 0x6a21, 0x5757]),
    'action_module': C([0x64cd, 0x4f5c, 0x6a21, 0x5757]),
    'function_module': C([0x529f, 0x80fd, 0x6a21, 0x5757]),
    'target': C([0x6d4b, 0x8bd5, 0x76ee, 0x6807]),
    'steps': C([0x6267, 0x884c, 0x6b65, 0x9aa4]),
    'action_steps': C([0x64cd, 0x4f5c, 0x6b65, 0x9aa4]),
    'test_steps': C([0x6d4b, 0x8bd5, 0x6b65, 0x9aa4]),
    'step': C([0x6b65, 0x9aa4]),
    'expected': C([0x9884, 0x671f]),
    'expected_result': C([0x9884, 0x671f, 0x7ed3, 0x679c]),
    'actual': C([0x5b9e, 0x9645]),
    'actual_result': C([0x5b9e, 0x9645, 0x7ed3, 0x679c]),
    'exec_result': C([0x6267, 0x884c, 0x7ed3, 0x679c]),
    'test_result': C([0x6d4b, 0x8bd5, 0x7ed3, 0x679c]),
    'priority': C([0x4f18, 0x5148, 0x7ea7]),
}

HEADER_ALIAS_GROUPS = {
    'id': ['id', 'ID', 'case_id', 'test_case_id', ZH['case_id'], ZH['case_no'], ZH['number'], ZH['seq']],
    'precondition': ['precondition', 'preconditions', ZH['precondition'], ZH['pre']],
    'module': ['module', 'target', ZH['module'], ZH['test_module'], ZH['action_module'], ZH['function_module'], ZH['target']],
    'steps': ['step', 'steps', ZH['steps'], ZH['action_steps'], ZH['test_steps'], ZH['step']],
    'expected': ['expected', 'expected_result', ZH['expected'], ZH['expected_result']],
    'actual': ['actual', 'actual_result', ZH['actual'], ZH['actual_result'], ZH['exec_result'], ZH['test_result']],
    'priority': ['priority', ZH['priority']],
}


def _header_group(header: str) -> Optional[str]:
    normalized = str(header or '').strip().lower()
    for group, aliases in HEADER_ALIAS_GROUPS.items():
        if normalized in {str(a).lower() for a in aliases}:
            return group
    return None


def normalize_headers(headers: Optional[List[str]]) -> List[str]:
    if headers and len(headers) >= 3:
        cleaned = []
        for header in headers:
            value = str(header or '').strip().strip('|').strip()
            if value and value not in cleaned:
                cleaned.append(value)
        if len(cleaned) >= 3:
            return cleaned
    return DEFAULT_HEADERS


def _case_value_for_header(case: Dict, header: str, index: int) -> str:
    if not isinstance(case, dict):
        return ''

    group = _header_group(header)
    candidates = [header]
    if group:
        candidates.extend(HEADER_ALIAS_GROUPS.get(group, []))

    lower_map = {str(k).strip().lower(): v for k, v in case.items()}
    for key in candidates:
        if key in case and case.get(key) not in (None, ''):
            return case.get(key, '')
        value = lower_map.get(str(key).strip().lower())
        if value not in (None, ''):
            return value

    if index == 0:
        for key in HEADER_ALIAS_GROUPS['id']:
            if key in case and case.get(key) not in (None, ''):
                return case.get(key)
            value = lower_map.get(str(key).strip().lower())
            if value not in (None, ''):
                return value
    return ''

def _extract_sort_key_from_id(id_value: str) -> int:
    """从用例ID中提取排序用的数值，支持 TC_001 / LOGIN_001 / 001 等格式。"""
    if not id_value:
        return 99999
    # 尝试提取末尾的数字（支持 TC_001、LOGIN_001、001 等格式）
    match = re.search(r'(\d+)$', str(id_value).strip())
    if match:
        return int(match.group(1))
    # 如果完全没有数字，使用哈希确保稳定排序
    return 99998 - (hash(str(id_value)) % 100)


def _sort_test_cases_by_id(test_cases: List[Dict]) -> List[Dict]:
    """按用例ID字段排序，确保AI生成用例的顺序可预期。"""
    if len(test_cases) <= 1:
        return test_cases
    # 获取ID字段名（可能是"用例ID"、"ID"、"序号"等各种别名）
    id_keys = ['用例ID', 'ID', 'id', '序号', '用例编号']
    id_key = None
    if test_cases:
        for k in id_keys:
            if k in test_cases[0]:
                id_key = k
                break
    if not id_key:
        return test_cases  # 没有找到已知ID字段，保持原序
    try:
        test_cases.sort(key=lambda tc: _extract_sort_key_from_id(str(tc.get(id_key, ''))))
    except Exception as e:
        logger.warning(f"用例排序失败（保持原序）: {e}")
    return test_cases


def normalize_test_cases_to_headers(test_cases: List[Dict], headers: Optional[List[str]]) -> List[Dict]:
    normalized_headers = normalize_headers(headers)
    normalized_cases = []
    for idx, case in enumerate(test_cases or [], start=1):
        row = {}
        for col_index, header in enumerate(normalized_headers):
            row[header] = _case_value_for_header(case, header, col_index)
        first_header = normalized_headers[0]
        if not row.get(first_header):
            row[first_header] = f"TC_{idx:03d}"
        normalized_cases.append(row)
    # 按用例ID排序，确保顺序稳定可预期
    return _sort_test_cases_by_id(normalized_cases)

# 默认测试用例模板头（与需求分析生成用例使用的表头一致）
DEFAULT_HEADERS = [
    "ID",
    "测试模块",
    "前置条件",
    "执行步骤",
    "预期结果",
    "实际结果",
    "优先级",
    "用例类型",
    "自动化类型",
    "是否通过",
]

# ---------- 深度爬取 ----------


async def _fetch_url_text(url: str, timeout: float = 15.0, max_retries: int = 3) -> Optional[str]:
    """获取单页 HTML 文本，支持重试和指数退避"""
    import asyncio
    last_error = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
                resp = await client.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0'
                })
                resp.raise_for_status()
                text = resp.text
                if not text or not text.strip():
                    logger.warning(f"目标网站 {url} 返回空内容 (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return None
                return text
        except Exception as e:
            last_error = e
            logger.warning(f"获取 {url} 失败 (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
    logger.error(f"获取 {url} 最终失败: {last_error}")
    return None


def _parse_html(html: str) -> Dict:
    """解析 HTML 提取结构化信息"""
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'nav', 'footer', 'svg', 'noscript']):
        tag.decompose()

    title = soup.title.string.strip() if soup.title else ""

    # 1. 表单元素深度提取
    forms = []
    for form in soup.find_all('form'):
        form_info = {"action": form.get('action', ''), "method": form.get('method', 'get'), "fields": []}
        for inp in form.find_all(['input', 'textarea', 'select']):
            field = {
                'name': inp.get('name', ''),
                'type': inp.get('type', inp.name),
                'placeholder': inp.get('placeholder', ''),
                'required': '必填' if inp.get('required') else '可选',
                'label': '',
            }
            # 尝试找关联的 label
            label = inp.find_previous('label')
            if label:
                field['label'] = label.get_text(strip=True)
            form_info["fields"].append(field)
        forms.append(form_info)

    # 也提取不在 form 内的 input 元素
    standalone_inputs = []
    for inp in soup.find_all(['input', 'textarea', 'select']):
        if not inp.find_parent('form'):
            standalone_inputs.append({
                'name': inp.get('name', ''), 'type': inp.get('type', inp.name),
                'placeholder': inp.get('placeholder', ''),
            })

    # 2. 按钮
    buttons = list(dict.fromkeys(
        b.get_text(strip=True) or b.get('value', '') or b.get('aria-label', '')
        for b in soup.find_all('button') if b.get_text(strip=True) or b.get('value', '')
    ))

    # 3. 链接（导航链接，含 href）
    links = []
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a.get('href', '')
        if text and not href.startswith('#'):
            links.append(f"{text} ({href})")

    # 4. 页面标题标签
    headings = []
    for h in soup.find_all(['h1', 'h2', 'h3']):
        text = h.get_text(strip=True)
        if text:
            headings.append(f"[{h.name}] {text}")

    # 5. 正文（截断）
    body_text = soup.get_text(separator='\n', strip=True)
    if len(body_text) > 6000:
        body_text = body_text[:6000] + "\n...[内容已截断]"

    return {
        "title": title,
        "headings": headings[:30],
        "buttons": buttons[:30],
        "links": links[:40],
        "forms": forms,
        "standalone_inputs": standalone_inputs,
        "body_text": body_text,
    }


def _build_website_section(info: Dict, url: str) -> str:
    """构建网站信息描述文本（仿软测分析的格式）"""
    if not info or not info.get("title"):
        return ""

    sections = [
        f"【目标网页内容】\n以下是从实际测试目标网页爬取到的真实页面内容，请基于这些内容设计测试用例：\n"
        f"网页标题: {info.get('title', '')}\n"
        f"网页地址: {url}\n"
    ]

    if info.get("headings"):
        sections.append(f"\n=== 页面结构（标题层级） ===\n" + "\n".join(info["headings"]))

    if info.get("forms"):
        sections.append(f"\n=== 页面表单（共计 {len(info['forms'])} 个） ===")
        for idx, form in enumerate(info["forms"], 1):
            sections.append(f"\n表单 {idx}: action={form['action']}, method={form['method']}")
            for f in form["fields"]:
                label = f" ({f['label']})" if f['label'] else ""
                sections.append(f"  - {f['name']}({f['type']}, {f['required']}, placeholder={f['placeholder']}){label}")

    if info.get("standalone_inputs"):
        sections.append(f"\n=== 独立输入元素 ===\n" + "\n".join(
            f"  - {s['name']}({s['type']}, placeholder={s['placeholder']})"
            for s in info["standalone_inputs"]
        ))

    if info.get("buttons"):
        sections.append(f"\n=== 页面按钮 ===\n" + ", ".join(info["buttons"]))

    if info.get("links"):
        sections.append(f"\n=== 页面导航链接 ===\n" + "\n".join(f"  - {link}" for link in info["links"]))

    error_info = info.get("error", "")
    if error_info:
        sections.append(f"\n=== 注意事项 ===\n爬取时遇到问题: {error_info}\n请特别关注登录/认证相关的测试场景")

    sections.append(f"\n=== 页面正文 ===\n{info.get('body_text', '(无)')}")

    return "\n".join(sections)


# ---------- 测试用例生成 ----------


class TestPlanGenerator:
    """测试计划生成器：对标软测分析，深度分析网站 → 生成高覆盖测试用例"""

    def __init__(self, api_key: str, base_url: str, model_name: str, temperature: float = 0.3):
        self.llm = ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
        )

    async def crawl_website(self, url: str) -> Dict[str, str]:
        """深度爬取目标网站"""
        if not url:
            return {"title": "", "headings": [], "forms": [], "buttons": [], "links": [], "body_text": "", "error": ""}

        try:
            html = await _fetch_url_text(url)
            if not html:
                return {"title": "", "error": "网页无法访问", "forms": [], "headings": [], "buttons": [], "links": [], "body_text": ""}

            info = _parse_html(html)
            # 尝试也爬取常见子页面
            extra_sections = []
            common_paths = ['/login', '/register', '/about', '/contact', '/help']
            for path in common_paths[:3]:
                try:
                    sub_html = await _fetch_url_text(url.rstrip('/') + path, timeout=8.0)
                    if sub_html:
                        sub_info = _parse_html(sub_html)
                        if sub_info.get("title"):
                            extra_sections.append(f"  - {path}: {sub_info['title']}")
                except Exception:
                    pass
            if extra_sections:
                info["extra_pages"] = "\n".join(extra_sections)

            return info

        except Exception as e:
            logger.warning(f"深度爬取网站失败 {url}: {e}")
            return {"title": "", "error": str(e), "forms": [], "headings": [], "buttons": [], "links": [], "body_text": ""}

    async def generate_test_cases(
        self,
        url: str,
        requirement_description: str,
        custom_headers: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        生成结构化测试用例（仿软测分析）

        Args:
            url: 目标网站 URL
            requirement_description: 用户需求描述
            custom_headers: 自定义测试用例表头

        Returns:
            测试用例列表 [{"用例ID": "LOGIN_001", "测试目标": "...", ...}, ...]
        """
        # 1. 深度爬取
        website_info = await self.crawl_website(url) if url else {}

        # 2. 确定表头
        headers = normalize_headers(custom_headers)

        # 3. 构建网站信息段落（仿软测分析格式）
        website_section = _build_website_section(website_info, url) if url and website_info.get("title") else ""

        # 4. 构建 prompt（对标 tester.md + 软测分析的深度遍历策略）
        headers_str = "、".join(h for h in headers)

        system_prompt = """你是一位拥有10年经验的资深测试用例编写专家，能够根据需求精确生成高质量的测试用例。

# 核心目标
生成高覆盖率、颗粒度细致的测试用例，确保不遗漏任何功能逻辑、异常场景和边界条件。

# 角色设定
1. 身份：精通全栈测试（Web/App/API）的高级QA专家
2. 测试风格：破坏性测试思维，善于发现潜在Bug
3. 输出原则：详细、独立、可执行

# 用例设计规范
1. **独立性**：每条用例只验证一个具体的测试点，严禁合并多个场景。
2. **完整性**：包含用例ID、清晰测试目标、准确前置条件、步骤化操作描述、具体预期结果。
3. **覆盖维度**：
   - ✅ 功能正向流程（Happy Path）
   - ⚠️ 异常流程（输入错误、权限不足、网络异常）
   - 🔄 边界值（最大/最小值、空值、特殊字符）
   - 🔒 业务约束（状态机流转、数据依赖）
   - 🔐 安全测试（SQL注入、XSS、越权访问）
   - 📱 UI交互体验（按钮状态、页面跳转、弹窗、响应式）"""

        user_prompt = f"""{system_prompt}

请深入分析以下目标网站和用户需求，设计高覆盖率的测试用例。

【生成指令】
1. **数量原则**：根据网站复杂度自动决定（建议 8-30 条），应写尽写
2. **深度遍历策略**：
   - 逐功能模块分析：首页 → 导航 → 列表 → 表单 → 详情 → 提交
   - 每个功能点 = 1条正常流程 + 2~3条异常/边界用例
   - 每个输入字段 = 正常值 + 空值 + 超长值 + 特殊字符
   - 每个按钮 = 正常点击 + 重复点击 + 快速双击
3. **场景扩展库**（必须覆盖）：
   - 数据完整性：必填字段校验、格式校验、长度限制
   - 业务逻辑约束：状态流转、权限控制、数据依赖
   - 外部接口异常：网络断开、服务超时、API错误
   - UI交互体验：页面跳转、弹窗关闭、Loading状态
   - 安全验证：XSS注入、SQL注入、CSRF
4. **拒绝合并**：严禁在一条用例中合并多个独立验证点
5. **输出顺序要求**：必须按编号从小到大，不跳号、不重复
6. **特殊字符处理**：管道符 | 用 &#124; 代替

{website_section}

【用户需求】
{requirement_description or '请根据网站本身的功能模块进行全面功能测试，覆盖核心业务流程'}

【测试用例格式要求】
1. 每条用例必须包含以下字段: {headers_str}
2. 操作步骤必须可执行：具体到点击哪个按钮、输入什么数据、检查什么元素
3. 预期结果必须可验证：包含页面表现、数据变化、提示信息
4. 优先级分级：
   - P0: 核心业务流程（登录、下单、支付、搜索等主链路）
   - P1: 重要功能验证（表单校验、权限控制、列表操作）
   - P2: 一般功能（UI展示、提示信息、非关键交互）
   - P3: 边缘场景（极端值、并发、兼容性）
5. 测试类型分类：
   - 功能验证：正常功能流程
   - 异常测试：错误输入、异常场景
   - 边界值测试：极值、空值、特殊值
   - 安全测试：注入攻击、越权访问
   - UI交互测试：点击、滚动、弹窗、跳转
   - 性能测试：页面加载、接口响应
6. 模块名从网站的导航/标题中提取，如"登录模块"、"搜索模块"、"用户中心"、"订单模块"等
7. 必须考虑验证码、登录超时、网络异常等异常场景
8. 如果网页上有图片验证码/滑块验证等无法自动处理的验证机制，请设计「标记跳过」相关用例

请以 JSON 数组格式返回，每个元素是一条用例对象，JSON key 使用上述中文表头名称。
只返回 JSON 数组，不要包含其他文字。
```json
[
  {{"用例ID": "MODULE_001", "测试目标": "...", "前置条件": "...", "操作步骤": "...", "预期结果": "...", "优先级": "P0", "测试类型": "功能验证", "关联模块": "登录模块"}},
  ...
]
```"""

        # 5. 调用 AI 生成
        try:
            response = await asyncio.wait_for(
                self.llm.ainvoke(user_prompt),
                timeout=180.0,
            )
            content = response.content.strip() if hasattr(response, 'content') else str(response)

            # === 增强 JSON 解析：兼容截断/未闭合的 JSON ===
            # 1) 优先匹配 ```json ... ``` 代码块（完整闭合）
            json_str = None
            json_match = re.search(r'```json\s*(\[[\s\S]*?\])\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 2) 匹配未闭合的 ```json 代码块（AI 输出被 8k token 截断的常见情况）
                truncated_match = re.search(r'```json\s*(\[[\s\S]*)$', content, re.DOTALL)
                if truncated_match:
                    json_str = truncated_match.group(1)
                    # 剥离末尾未闭合的 ```
                    json_str = re.sub(r'```\s*$', '', json_str).rstrip()
                else:
                    # 3) 兜底匹配任意 [...] JSON 数组片段（贪婪，允许截断）
                    fallback_match = re.search(r'\[[\s\S]*', content)
                    if fallback_match:
                        json_str = fallback_match.group(0)

            if json_str:
                # 尝试自动修复被截断的 JSON：截取到最后一个完整的对象
                fixed_json = self._repair_truncated_json(json_str)
                try:
                    fixed_json = fixed_json.replace('{{', '{').replace('}}', '}')
                    test_cases = json.loads(fixed_json)
                    if isinstance(test_cases, list) and len(test_cases) > 0:
                        logger.info(f"✅ 成功生成 {len(test_cases)} 条测试用例（深度分析）")

                        # 确保每条有用例ID字段
                        for idx, tc in enumerate(test_cases):
                            if "用例ID" not in tc and "序号" in tc:
                                tc["用例ID"] = f"TC_{tc.get('序号', idx+1)}"
                            elif "用例ID" not in tc:
                                tc["用例ID"] = f"TC_{idx+1:03d}"

                        return normalize_test_cases_to_headers(test_cases, headers)
                    else:
                        logger.warning(f"⚠️ AI 返回的 JSON 不是列表或为空")
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ AI 返回内容 JSON 解析失败: {e}")
                    logger.info(f"原始内容: {content[:500]}")

            # 尝试从 Markdown 表格提取
            try:
                table_pattern = re.search(r'\|.*\|[\s\S]*?\|.*\|', content)
                if table_pattern:
                    logger.info("尝试从表格解析测试用例")
                    return self._parse_markdown_table(table_pattern.group(0), headers)
            except Exception as e:
                logger.warning(f"表格解析失败: {e}")

            logger.warning(f"⚠️ AI 返回内容无法解析为 JSON")
            logger.info(f"原始内容: {content[:500]}")
            return []

        except asyncio.TimeoutError:
            logger.error("❌ 测试用例生成超时（180s）")
            return []
        except Exception as e:
            logger.error(f"❌ 测试用例生成失败: {e}")
            return []

    @staticmethod
    def _repair_truncated_json(json_str: str) -> str:
        """修复被 token 上限截断的 JSON 数组

        典型场景：AI 返回 `[{...},{...},{ "字段": "值" `（末尾未闭合）
        策略：找到最后一个完整对象的结束位置，截断并补上 `]`
        """
        s = json_str.strip()
        if not s.startswith('['):
            return s

        # 如果本身就是完整的 JSON 数组，直接返回
        if s.endswith(']'):
            return s

        # 找到最后一个完整对象的结束 `}` 位置
        depth = 0
        in_str = False
        escape = False
        last_valid_end = -1
        for i, ch in enumerate(s):
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == '"' and not escape:
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    last_valid_end = i

        if last_valid_end == -1:
            return s

        # 截取到最后一个完整对象，闭合数组
        return s[:last_valid_end + 1] + ']'

    def format_as_markdown(self, test_cases: List[Dict], headers: Optional[List[str]] = None) -> str:
        """将测试用例格式化为 Markdown 表格"""
        if not test_cases:
            return ""

        headers = headers or DEFAULT_HEADERS
        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        for tc in test_cases:
            row = []
            for h in headers:
                val = str(tc.get(h, ""))
                # 管道符转义
                val = val.replace("|", "&#124;")
                row.append(val)
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    def _parse_markdown_table(self, table_text: str, headers: List[str]) -> List[Dict]:
        """从Markdown表格解析测试用例"""
        test_cases = []
        lines = table_text.strip().split('\n')
        
        if len(lines) < 3:
            return []
        
        # 解析表头
        header_line = lines[0].strip('|').split('|')
        parsed_headers = [h.strip() for h in header_line]
        
        # 跳过分隔线
        data_lines = lines[2:]
        
        for line in data_lines:
            if not line.strip():
                continue
            cells = line.strip('|').split('|')
            tc = {}
            for i, h in enumerate(parsed_headers):
                if i < len(cells):
                    tc[h] = cells[i].strip()
                else:
                    tc[h] = ""
            
            if tc:
                test_cases.append(tc)
        
        logger.info(f"从表格解析出 {len(test_cases)} 条测试用例")
        return normalize_test_cases_to_headers(test_cases, headers)

    async def regenerate_with_actual_results(
        self,
        original_test_cases: List[Dict],
        execution_results: str,
        requirement_description: str = "",
        custom_headers: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        实测后重新生成测试用例（包含实际结果/测试截图等字段）

        Args:
            original_test_cases: 原始测试用例
            execution_results: 执行日志/结果文本
            requirement_description: 用户需求描述
            custom_headers: 自定义表头（若用户指定过的优先使用）

        Returns:
            包含实际结果的完整测试用例列表
        """
        headers = normalize_headers(custom_headers)
        headers_str = "、".join(headers)

        # 如果用户表头中没有"实际结果"，自动追加
        has_actual = any('实际' in h or '测试结果' in h or '执行结果' in h for h in headers)
        output_headers = list(headers)
        if not has_actual:
            output_headers.append("实际结果")

        output_headers_str = "、".join(output_headers)

        # 构建原始用例完整列表（不限制数量，确保AI不丢失用例）
        original_summary = ""
        for tc in (original_test_cases or []):
            tc_id = tc.get("用例ID") or tc.get("ID") or tc.get("id") or tc.get("序号", "")
            tc_title = tc.get("测试目标") or tc.get("用例标题") or tc.get("测试模块") or tc.get("模块", "")
            tc_steps = tc.get("操作步骤") or tc.get("执行步骤") or tc.get("测试步骤") or tc.get("步骤", "")
            tc_expected = tc.get("预期结果") or tc.get("预期", "")
            tc_priority = tc.get("优先级") or ""
            # 截断长步骤，避免上下文过大
            if isinstance(tc_steps, str) and len(tc_steps) > 200:
                tc_steps = tc_steps[:200] + "..."
            original_summary += f"  - {tc_id}: {tc_title} [优先级: {tc_priority}] | 步骤: {tc_steps} | 预期: {tc_expected}\n"

        prompt = f"""你是资深测试专家，请根据实际执行结果，重新整理测试用例。

【任务】
1. 必须保留原始用例的每一条，不得删减任何一条用例
2. 基于实际执行结果，为每条用例填充"实际结果"字段
3. 如果某项测试未执行或跳过，请在"实际结果"中标注原因（如"跳过 - 遇到验证码"）
4. 保留原始用例的所有字段，新增"实际结果"列
5. 用例顺序必须与原始用例保持一致

【原始测试用例】（完整列表，共 {len(original_test_cases or [])} 条）
{original_summary}

【实际执行结果】
{execution_results[:6000]}

【用户原始需求】
{requirement_description or '全面功能测试'}

【输出格式】
以 JSON 数组返回，每条用例必须包含字段: {output_headers_str}
确保每条的"实际结果"字段具体、可验证（如"✅ 登录成功，跳转到首页"或"❌ 登录失败，提示密码错误"）
用例数量必须与原始用例一致（{len(original_test_cases or [])} 条），一条不少

只返回 JSON 数组，不要包含其他文字。
```json
[{{"用例ID":"...","测试目标":"...","前置条件":"...","操作步骤":"...","预期结果":"...","实际结果":"...","优先级":"P1","测试类型":"功能验证","关联模块":"..."}}]
```"""

        try:
            response = await asyncio.wait_for(
                self.llm.ainvoke(prompt),
                timeout=120.0,
            )
            content = response.content.strip() if hasattr(response, 'content') else str(response)

            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                new_cases = json.loads(json_match.group(0))
                logger.info(f"✅ 实测后重新生成 {len(new_cases)} 条测试用例")
                # 如果AI返回的用例数量不足，用原始用例补全
                if len(new_cases) < len(original_test_cases or []):
                    logger.warning(
                        f"⚠️ AI 返回用例数 ({len(new_cases)}) 少于原始 ({len(original_test_cases or [])})，"
                        f"使用原始用例补全"
                    )
                    # 将新用例的"实际结果"合并回原始用例
                    new_case_map = {}
                    for nc in new_cases:
                        nc_id = (
                            nc.get("用例ID") or nc.get("ID") or nc.get("id")
                            or nc.get("序号") or nc.get("用例编号") or ""
                        )
                        actual = nc.get("实际结果", "")
                        if nc_id:
                            new_case_map[str(nc_id)] = actual
                    for tc in (original_test_cases or []):
                        tc_id = (
                            tc.get("用例ID") or tc.get("ID") or tc.get("id")
                            or tc.get("序号") or tc.get("用例编号") or ""
                        )
                        if str(tc_id) in new_case_map and new_case_map[str(tc_id)]:
                            tc["实际结果"] = new_case_map[str(tc_id)]
                        elif "实际结果" not in tc or not tc.get("实际结果"):
                            tc["实际结果"] = "未执行"
                    return normalize_test_cases_to_headers(original_test_cases, headers)
                return normalize_test_cases_to_headers(new_cases, headers)
            logger.warning("⚠️ 实测后测试用例 JSON 解析失败")
            return normalize_test_cases_to_headers(original_test_cases, headers)
        except Exception as e:
            logger.warning(f"⚠️ 实测后重生成失败: {e}")
            return normalize_test_cases_to_headers(original_test_cases, headers)


# ---------- 工具函数 ----------

def parse_headers_from_description(description: str) -> Optional[List[str]]:
    """Extract user-requested testcase headers from free text."""
    if not description:
        return None

    text = str(description).replace('\r', '\n')
    candidates = []

    # Prefer the content after a colon. If it contains a comma-separated list,
    # accept it even when the natural-language keyword was lost by encoding.
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        colon_parts = []
        if ':' in stripped:
            colon_parts.append(stripped.split(':', 1)[1])
        if '?' in stripped:
            colon_parts.append(stripped.split('?', 1)[1])
        for part in colon_parts:
            if len(re.split(r'[,??|/\t]+|\s{2,}', part)) >= 3:
                candidates.append(part)
        if any(token in lower for token in ['header', 'headers', 'columns', 'custom_headers', 'custom header']) or any(
            token in stripped for token in ['??', '??', '??', '??', '??']
        ):
            candidates.extend(colon_parts)
            candidates.append(stripped)

    # Fallback: any compact comma-separated list with at least three items.
    candidates.extend(re.findall(r'([^\n]{3,240})', text))

    stop_words = {'????', '??', '??', '????', '??', '??', '?', '??', '??', '??'}
    for candidate in candidates:
        cleaned = candidate
        for stop_word in stop_words:
            cleaned = cleaned.replace(stop_word, '')
        parts = re.split(r'[,??|/\t]+|\s{2,}', cleaned)
        fields = []
        for part in parts:
            value = part.strip().strip('[]()????"\'')
            value = re.sub(r'^(and|with|use|using)\s+', '', value, flags=re.I).strip()
            if 1 <= len(value) <= 30 and value not in fields:
                fields.append(value)
        if len(fields) >= 3:
            return fields

    return None

def analyze_uploaded_file_content(content: str, filename: str) -> Dict:
    """
    分析用户上传的文件内容，提取需求和/或测试用例

    支持: .txt, .md, .csv, 纯文本

    Returns:
        {
            "type": "requirements" | "testcases" | "mixed",
            "requirements": "...",
            "test_cases": [...],
            "summary": "..."
        }
    """
    result = {
        "type": "unknown",
        "requirements": "",
        "test_cases": [],
        "summary": "",
    }

    if not content or not content.strip():
        return result

    content = content.strip()
    result["requirements"] = content[:5000]

    # 检查是否是 CSV/表格格式（包含表头行）
    lines = content.split('\n')
    is_table = False
    if len(lines) >= 2:
        first_line = lines[0].strip()
        # 检查第一行是否像表头（多个用逗号/制表符分隔的词）
        separator = ',' if ',' in first_line else '\t' if '\t' in first_line else None
        if separator:
            headers_in_line = [h.strip() for h in first_line.split(separator)]
            if len(headers_in_line) >= 3:
                is_table = True
                result["type"] = "testcases"
                result["summary"] = f"文件 {filename} 为表格格式，包含 {len(headers_in_line)} 个字段: {', '.join(headers_in_line[:8])}"

                # 尝试解析测试用例行
                test_cases = []
                for line in lines[1:30]:  # 最多30行
                    line = line.strip()
                    if not line:
                        continue
                    values = [v.strip().strip('"') for v in line.split(separator)]
                    tc = {}
                    for i, h in enumerate(headers_in_line):
                        tc[h] = values[i] if i < len(values) else ""
                    test_cases.append(tc)

                if test_cases:
                    result["test_cases"] = test_cases
                    result["summary"] += f"，共解析 {len(test_cases)} 条用例"

    if not is_table:
        # 纯文本需求
        result["type"] = "requirements"
        result["summary"] = f"文件 {filename} 为需求文档（{len(content)} 字符）"

    return result
