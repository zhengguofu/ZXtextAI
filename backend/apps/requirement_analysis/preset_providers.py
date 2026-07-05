"""
预设AI模型供应商配置
用户选择供应商后，只需输入API Key即可完成配置
"""

PRESET_PROVIDERS = [
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "description": "深度求索 DeepSeek - 高性能中文大模型",
        "icon": "🤖",
        "model_type": "deepseek",
        "base_url": "https://api.deepseek.com",
        "models": [
            {"name": "deepseek-chat", "display_name": "DeepSeek Chat"},
            {"name": "deepseek-v4-pro", "display_name": "DeepSeek V4 Pro"}
        ],
        "default_role": "ai_tester",
        "api_key_help": "在 DeepSeek 控制台获取 API Key"
    },
    {
        "id": "qwen",
        "name": "通义千问",
        "description": "阿里云 通义千问 - 阿里巴巴自研大模型",
        "icon": "🧠",
        "model_type": "qwen",
        "base_url": "https://dashscope.aliyuncs.com/api/text/v1",
        "models": [
            {"name": "qwen-turbo", "display_name": "通义千问 Turbo"},
            {"name": "qwen-max", "display_name": "通义千问 Max"},
            {"name": "qwen-plus", "display_name": "通义千问 Plus"}
        ],
        "default_role": "ai_tester",
        "api_key_help": "在阿里云 DashScope 控制台获取 API Key"
    },
    {
        "id": "zhipu",
        "name": "智谱AI",
        "description": "智谱 AI - GLM 系列大模型",
        "icon": "💡",
        "model_type": "zhipu",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": [
            {"name": "glm-4", "display_name": "GLM-4"},
            {"name": "glm-4-flash", "display_name": "GLM-4 Flash"},
            {"name": "glm-3-turbo", "display_name": "GLM-3 Turbo"}
        ],
        "default_role": "ai_tester",
        "api_key_help": "在智谱开放平台获取 API Key"
    },
    {
        "id": "siliconflow",
        "name": "硅基流动",
        "description": "硅基流动 - 一站式AI模型服务平台",
        "icon": "⚡",
        "model_type": "siliconflow",
        "base_url": "https://api.siliconflow.cn/v1",
        "models": [
            {"name": "Qwen/Qwen2-7B-Instruct", "display_name": "Qwen2-7B"},
            {"name": "Qwen/Qwen2-14B-Instruct", "display_name": "Qwen2-14B"},
            {"name": "meta-llama/Meta-Llama-3-8B-Instruct", "display_name": "Llama-3-8B"}
        ],
        "default_role": "ai_tester",
        "api_key_help": "在硅基流动平台获取 API Key"
    },
    {
        "id": "kimi",
        "name": "Kimi 智能",
        "description": "Moonshot AI Kimi - 长文本理解专家",
        "icon": "🌙",
        "model_type": "other",
        "base_url": "https://api.moonshot.cn/v1",
        "models": [
            {"name": "moonshot-v1-8k", "display_name": "Kimi 8K"},
            {"name": "moonshot-v1-32k", "display_name": "Kimi 32K"},
            {"name": "moonshot-v1-128k", "display_name": "Kimi 128K"}
        ],
        "default_role": "ai_tester",
        "api_key_help": "在 Moonshot AI 控制台获取 API Key"
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "description": "OpenAI - GPT 系列模型",
        "icon": "🔮",
        "model_type": "other",
        "base_url": "https://api.openai.com/v1",
        "models": [
            {"name": "gpt-4o", "display_name": "GPT-4o"},
            {"name": "gpt-4-turbo", "display_name": "GPT-4 Turbo"},
            {"name": "gpt-3.5-turbo", "display_name": "GPT-3.5 Turbo"}
        ],
        "default_role": "ai_tester",
        "api_key_help": "在 OpenAI 平台获取 API Key"
    },
    {
        "id": "claude",
        "name": "Claude",
        "description": "Anthropic Claude - 安全可靠的AI助手",
        "icon": "👤",
        "model_type": "other",
        "base_url": "https://api.anthropic.com/v1",
        "models": [
            {"name": "claude-3-opus-20240229", "display_name": "Claude 3 Opus"},
            {"name": "claude-3-sonnet-20240229", "display_name": "Claude 3 Sonnet"},
            {"name": "claude-3-haiku-20240307", "display_name": "Claude 3 Haiku"}
        ],
        "default_role": "ai_tester",
        "api_key_help": "在 Anthropic 平台获取 API Key"
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "description": "Google Gemini - 多模态大模型",
        "icon": "🌟",
        "model_type": "other",
        "base_url": "https://generativelanguage.googleapis.com/v1",
        "models": [
            {"name": "gemini-1.5-pro", "display_name": "Gemini 1.5 Pro"},
            {"name": "gemini-1.5-flash", "display_name": "Gemini 1.5 Flash"},
            {"name": "gemini-pro", "display_name": "Gemini Pro"}
        ],
        "default_role": "ai_tester",
        "api_key_help": "在 Google AI Studio 获取 API Key"
    },
    {
        "id": "doubao",
        "name": "豆包",
        "description": "字节跳动 豆包 - 智能助手",
        "icon": "🫘",
        "model_type": "other",
        "base_url": "https://api.doubao.com/v1",
        "models": [
            {"name": "Doubao-3", "display_name": "豆包 3.0"},
            {"name": "Doubao-3-Turbo", "display_name": "豆包 3.0 Turbo"}
        ],
        "default_role": "ai_tester",
        "api_key_help": "在豆包开放平台获取 API Key"
    },
    {
        "id": "minimax",
        "name": "MiniMax",
        "description": "MiniMax - 极简高效的AI服务",
        "icon": "🔹",
        "model_type": "other",
        "base_url": "https://api.minimax.chat/v1",
        "models": [
            {"name": "abab6-chat", "display_name": "abab6-chat"},
            {"name": "abab6.5-chat", "display_name": "abab6.5-chat"}
        ],
        "default_role": "ai_tester",
        "api_key_help": "在 MiniMax 平台获取 API Key"
    },
    {
        "id": "baichuan",
        "name": "百川智能",
        "description": "百川智能 - 中文大模型",
        "icon": "🌊",
        "model_type": "other",
        "base_url": "https://api.baichuan-ai.com/v1",
        "models": [
            {"name": "Baichuan3-Turbo", "display_name": "百川3 Turbo"},
            {"name": "Baichuan3-Plus", "display_name": "百川3 Plus"}
        ],
        "default_role": "ai_tester",
        "api_key_help": "在百川智能开放平台获取 API Key"
    },
    {
        "id": "custom",
        "name": "自定义配置",
        "description": "手动配置自定义模型",
        "icon": "⚙️",
        "model_type": "other",
        "base_url": "",
        "models": [],
        "default_role": "ai_tester",
        "api_key_help": "请输入自定义 API Key"
    }
]

def get_provider_by_id(provider_id):
    """根据ID获取供应商配置"""
    return next((p for p in PRESET_PROVIDERS if p["id"] == provider_id), None)

def get_providers():
    """获取所有预设供应商"""
    return PRESET_PROVIDERS
