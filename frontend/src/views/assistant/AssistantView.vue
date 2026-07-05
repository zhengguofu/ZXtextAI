<template>
  <div class="chat-container">
    <!-- Token 消耗提示 -->
    <transition name="toast">
      <div v-if="showTokenToast" class="token-toast">
        <el-icon class="token-icon"><Coin /></el-icon>
        <span class="token-text">消耗 Token: {{ tokenUsage }}</span>
      </div>
    </transition>

    <!-- 侧边栏 -->
    <div class="sidebar" :class="{ collapsed }">
      <div class="sidebar-header">
        <button class="new-chat-btn" @click="startNewChat">
          <el-icon><Plus /></el-icon>
          <span v-if="!collapsed">新建对话</span>
        </button>
        <button class="toggle-btn" @click="collapsed = !collapsed" v-if="!collapsed">
          <el-icon><Fold /></el-icon>
        </button>
      </div>

      <div class="history-list" v-if="!collapsed">
        <div class="history-title">历史对话</div>
        <div class="history-items">
          <div
            v-for="s in sortedSessions"
            :key="s.id"
            class="history-item"
            :class="{ active: currentSession?.id === s.id }"
            @click="switchSession(s)"
          >
            <el-icon class="item-icon"><ChatDotRound /></el-icon>
            <span class="item-title">{{ s.title || '新对话' }}</span>
            <el-popconfirm title="确定删除该对话？" @confirm="removeSession(s)">
              <template #reference>
                <el-icon class="item-delete" @click.stop><Delete /></el-icon>
              </template>
            </el-popconfirm>
          </div>
        </div>
        <div v-if="!sortedSessions.length" class="no-history">暂无历史对话</div>
      </div>

      <div class="sidebar-footer" v-if="!collapsed">
        <div class="user-info">
          <el-avatar :size="32" class="user-avatar">
            <el-icon><UserFilled /></el-icon>
          </el-avatar>
          <div class="user-details">
            <div class="user-name">{{ userStore.user?.username || '用户' }}</div>
            <div class="user-role">ZX 自动化测试平台</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 主聊天区域 -->
    <div class="main-area">
      <!-- 顶部栏 -->
      <div class="top-bar">
        <button class="back-button" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </button>
        <div class="chat-title">
          <h2>{{ currentSession?.title || 'ZX AI 助手' }}</h2>
        </div>
        <div class="model-selector">
          <el-select v-model="selectedModel" size="default" placeholder="选择模型">
            <el-option label="智能选择 (Auto)" value="auto" />
            <el-option v-for="m in availableModels" :key="m.id" :label="m.name" :value="String(m.id)" />
          </el-select>
        </div>
      </div>

      <!-- 消息区域 -->
      <div class="messages-area" ref="scrollRef" @click="handleMessageClick">
        <!-- 欢迎界面 -->
        <div v-if="!messages.length" class="welcome-screen">
          <div class="welcome-icon">
            <el-icon><MagicStick /></el-icon>
          </div>
          <h1 class="welcome-title">我是 ZX AI 助手</h1>
          <p class="welcome-subtitle">有什么可以帮你的吗？</p>
          <div class="suggestions">
            <button
              v-for="s in suggestions"
              :key="s.title"
              class="suggestion-card"
              @click="quickAsk(s.q)"
            >
              <div class="suggestion-icon">
                <el-icon><component :is="s.icon" /></el-icon>
              </div>
              <div class="suggestion-content">
                <div class="suggestion-title">{{ s.title }}</div>
                <div class="suggestion-desc">{{ s.desc }}</div>
              </div>
            </button>
          </div>
        </div>

        <!-- 消息列表 -->
        <transition-group v-else name="msg" tag="div" class="messages-list">
          <div
            v-for="(msg, idx) in messages"
            :key="msg.id || idx"
            class="message-row"
            :class="{ 'user-message': msg.role === 'user', 'ai-message': msg.role === 'assistant' }"
          >
            <div class="message-wrapper">
              <!-- 头像 -->
              <div class="message-avatar">
                <div v-if="msg.role === 'user'" class="avatar user-avatar">
                  <el-icon><UserFilled /></el-icon>
                </div>
                <div v-else class="avatar ai-avatar">
                  <el-icon><MagicStick /></el-icon>
                </div>
              </div>

              <!-- 消息内容 -->
                <div class="message-content">
                  <div class="message-header">
                    <span class="sender-name">{{ msg.role === 'user' ? '你' : 'ZX 助手' }}</span>
                    <span v-if="msg.model" class="model-tag">{{ msg.model }}</span>
                  </div>

                  <!-- 思考过程 -->
                  <div v-if="msg.thinking" class="thinking-box" @click="toggleThinking(msg.id)">
                    <div class="thinking-header">
                      <el-icon class="thinking-icon"><StarFilled /></el-icon>
                      <span class="thinking-title">思考过程</span>
                      <el-icon class="thinking-toggle" :class="{ expanded: msg.thinkingExpanded }"><ArrowDown /></el-icon>
                    </div>
                    <div class="thinking-content" v-show="msg.thinkingExpanded !== false">
                      <span class="thinking-text">{{ msg.thinking }}</span>
                    </div>
                  </div>

                  <!-- 加载状态 -->
                  <div v-if="msg.pending" class="message-bubble bubble-loading">
                    <span class="loading-dot"></span>
                    <span class="loading-dot"></span>
                    <span class="loading-dot"></span>
                  </div>

                  <!-- 错误状态 -->
                  <div v-else-if="msg.error" class="message-bubble bubble-error">
                    <el-icon class="error-icon"><WarningFilled /></el-icon>
                    <span class="error-text">{{ msg.content }}</span>
                    <el-button size="small" type="primary" plain @click="retryLast">重试</el-button>
                  </div>

                  <!-- 正常内容 -->
                  <div v-else class="message-bubble" :class="{ 'user-bubble': msg.role === 'user' }">
                    <div class="message-text" v-html="renderMarkdown(msg.content)"></div>

                    <!-- 消息操作按钮 -->
                    <div class="message-actions" v-if="msg.role === 'assistant' && msg.content">
                      <button class="action-btn" @click="copyText(msg.content)" title="复制全部">
                        <el-icon><CopyDocument /></el-icon>
                      </button>
                      <button
                        class="action-btn"
                        @click="downloadMessage(msg)"
                        title="下载文档"
                      >
                        <el-icon><Download /></el-icon>
                      </button>
                      <button
                        class="action-btn auto-test-btn"
                        v-if="containsTestCases(msg.content)"
                        @click="goToAutoTest(msg)"
                        title="自动测试"
                      >
                        <el-icon><VideoPlay /></el-icon>
                      </button>
                      <button
                        class="action-btn"
                        v-if="idx === messages.length - 1"
                        @click="retryLast"
                        title="重新生成"
                      >
                        <el-icon><Refresh /></el-icon>
                      </button>
                    </div>
                  </div>
                </div>
            </div>
          </div>
        </transition-group>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <div class="input-wrapper">
          <textarea
            ref="inputRef"
            v-model="draft"
            class="chat-input"
            placeholder="发送消息..."
            :disabled="sending"
            rows="1"
            @focus="inputFocused = true"
            @blur="inputFocused = false"
            @input="autoGrow"
            @keydown.enter.exact.prevent="onEnter"
          ></textarea>
          <button
            v-if="!sending"
            class="send-button"
            :disabled="!draft.trim()"
            @click="send()"
          >
            <el-icon><Promotion /></el-icon>
          </button>
          <button v-else class="stop-button" @click="stopGenerate">
            <span class="stop-icon"></span>
          </button>
        </div>
        <div class="input-footer">
          <span class="model-info">
            <el-icon><Cpu /></el-icon>
            {{ currentModelName }}
          </span>
          <span class="disclaimer">内容由 AI 生成</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import {
  Plus,
  Delete,
  UserFilled,
  Refresh,
  Cpu,
  Fold,
  MagicStick,
  ChatDotRound,
  Promotion,
  CopyDocument,
  WarningFilled,
  Document,
  Connection,
  Edit,
  View,
  ArrowLeft,
  Coin,
  StarFilled,
  ArrowDown,
  Download,
  VideoPlay,
} from '@element-plus/icons-vue'
import api from '@/utils/api'

const userStore = useUserStore()
const router = useRouter()

// 判断消息是否包含测试用例内容
const containsTestCases = (content) => {
  if (!content) return false
  const testCaseKeywords = [
    '测试用例', '测试场景', '用例编号', '用例名称', '前置条件',
    '测试步骤', '预期结果', '测试流程', '测试点', 'test case',
    'TestCase', '测试数据', '优先级', '测试步骤', '执行步骤'
  ]
  const contentLower = content.toLowerCase()
  return testCaseKeywords.some(keyword => contentLower.includes(keyword.toLowerCase()))
}

// 跳转到自动化测试页面
const goToAutoTest = (msg) => {
  const testCaseContent = msg.content || ''
  localStorage.setItem('ai_test_cases_content', testCaseContent)
  router.push({
    name: 'UiFullAuto',
    query: { fromAssistant: 'true' }
  })
}

// 状态
const collapsed = ref(false)
const sessions = ref([])
const currentSession = ref(null)
const messages = ref([])
const draft = ref('')
const sending = ref(false)
const inputFocused = ref(false)
const scrollRef = ref(null)
const inputRef = ref(null)
const selectedModel = ref('auto')
const availableModels = ref([])
let abortController = null

// Token 提示
const showTokenToast = ref(false)
const tokenUsage = ref(0)
let toastTimer = null

// 建议问题
const suggestions = ref([
  { icon: Connection, title: '接口测试', desc: '设计 RESTful API 测试用例', q: '请帮我设计一套 RESTful API 接口测试用例，覆盖正常、异常和边界场景。' },
  { icon: Edit, title: '自动化脚本', desc: '编写 Python 自动化测试脚本', q: '请帮我编写一个基于 pytest 的接口自动化测试脚本示例。' },
  { icon: View, title: 'Bug 定位', desc: '分析难以复现的缺陷', q: '一个偶现的线上 Bug 很难复现，请给我一套系统的排查和定位思路。' },
  { icon: Document, title: '测试报告', desc: '生成规范的测试报告', q: '请告诉我一份专业的软件测试报告应该包含哪些内容和结构。' }
])

// 计算属性
const sortedSessions = computed(() =>
  [...sessions.value].sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
)

const currentModelName = computed(() => {
  if (selectedModel.value === 'auto') return '智能选择'
  const m = availableModels.value.find(x => String(x.id) === selectedModel.value)
  return m ? m.name : '智能选择'
})

// 工具方法
const escapeHtml = (str) =>
  String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')

const renderMarkdown = (raw) => {
  if (!raw) return ''
  const codeBlocks = []
  const images = []
  const links = []
  let text = String(raw).replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length
    const langClass = lang ? ` data-lang="${escapeHtml(lang)}"` : ''
    codeBlocks.push(
      `<div class="code-block-wrapper"><div class="code-block-header"><span class="code-lang">${escapeHtml(lang || 'code')}</span><span class="code-copy" data-idx="${idx}">复制</span></div><pre class="code-block"${langClass}><code>${escapeHtml(code.replace(/\n$/, ''))}</code></pre></div>`
    )
    return ` CODE${idx} `
  })
  text = text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_, alt, src) => {
    const idx = images.length
    images.push(`<img class="md-image" src="${src}" alt="${escapeHtml(alt)}" />`)
    return ` IMG${idx} `
  })
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, textContent, href) => {
    const idx = links.length
    links.push(`<a class="md-link" href="${href}" target="_blank" rel="noopener">${escapeHtml(textContent)}</a>`)
    return ` LINK${idx} `
  })
  text = escapeHtml(text)
  // 行内代码
  text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
  // 加粗
  text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  // 斜体
  text = text.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
  // 标题
  text = text.replace(/^####\s+(.*)$/gm, '<h5>$1</h5>')
  text = text.replace(/^###\s+(.*)$/gm, '<h4>$1</h4>')
  text = text.replace(/^##\s+(.*)$/gm, '<h3>$1</h3>')
  text = text.replace(/^#\s+(.*)$/gm, '<h2>$1</h2>')
  // 引用
  text = text.replace(/^>\s+(.*)$/gm, '<blockquote>$1</blockquote>')
  // 水平线
  text = text.replace(/^---+$/gm, '<hr>')
  // 表格
  text = text.replace(/((?:^\|.*\|\n)+)/gm, (block) => {
    const rows = block.trim().split('\n')
    if (rows.length < 2) return block
    const header = rows[0]
    const sep = rows[1]
    if (!/^\|[\s\-:|]+\|$/.test(sep.trim())) return block
    const headCells = header.split('|').slice(1, -1).map(c => `<th>${c.trim()}</th>`).join('')
    const bodyRows = rows.slice(2).map(r => {
      const cells = r.split('|').slice(1, -1).map(c => `<td>${c.trim()}</td>`).join('')
      return `<tr>${cells}</tr>`
    }).join('')
    return `<table class="md-table"><thead><tr>${headCells}</tr></thead><tbody>${bodyRows}</tbody></table>`
  })
  // 列表
  text = text.replace(/(?:^|\n)((?:\s*[-*]\s+.*(?:\n|$))+)/g, (m) => {
    const items = m.trim().split(/\n/).map(l => l.replace(/^\s*[-*]\s+/, '')).map(l => `<li>${l}</li>`).join('')
    return `\n<ul>${items}</ul>`
  })
  // 有序列表
  text = text.replace(/(?:^|\n)((?:\s*\d+\.\s+.*(?:\n|$))+)/g, (m) => {
    const items = m.trim().split(/\n/).map(l => l.replace(/^\s*\d+\.\s+/, '')).map(l => `<li>${l}</li>`).join('')
    return `\n<ol>${items}</ol>`
  })
  // 连续段落换行
  text = text.replace(/\n{2,}/g, '</p><p>')
  text = text.replace(/\n/g, '<br>')
  text = text.replace(/<p>/g, '<p class="md-p">')
  text = text.replace(/<br><\/p>/g, '</p>')
  text = text.replace(/<p>\s*<\/p>/g, '')
  // 还原代码块
  text = text.replace(/ CODE(\d+) /g, (_, i) => codeBlocks[Number(i)])
  // 还原图片
  text = text.replace(/ IMG(\d+) /g, (_, i) => images[Number(i)])
  // 还原链接
  text = text.replace(/ LINK(\d+) /g, (_, i) => links[Number(i)])
  return text
}

const scrollToBottom = () => {
  nextTick(() => {
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  })
}

const autoGrow = () => {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}

const copyText = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败')
  }
}

const handleMessageClick = (e) => {
  const target = e.target
  if (target && target.classList && target.classList.contains('code-copy')) {
    const wrapper = target.closest('.code-block-wrapper')
    if (wrapper) {
      const codeEl = wrapper.querySelector('code')
      if (codeEl) {
        copyText(codeEl.innerText)
        target.textContent = '已复制'
        setTimeout(() => { target.textContent = '复制' }, 1500)
      }
    }
  }
}

const showTokenUsage = (usage) => {
  if (toastTimer) clearTimeout(toastTimer)
  tokenUsage.value = usage
  showTokenToast.value = true
  toastTimer = setTimeout(() => {
    showTokenToast.value = false
  }, 3000)
}

const goBack = () => {
  router.push('/home')
}

// 数据加载
const loadModels = async () => {
  try {
    const res = await api.get('/requirement-analysis/ai-models/', { params: { page_size: 100 } })
    const items = res.data?.results || res.data || []
    availableModels.value = Array.isArray(items) ? items.filter(m => m.is_active) : []
  } catch {
    availableModels.value = []
  }
}

const loadSessions = async () => {
  try {
    const res = await api.get('/assistant/sessions/')
    sessions.value = res.data?.results || res.data || []
  } catch (e) {
    console.error('加载历史失败:', e)
  }
}

// 会话操作
const startNewChat = () => {
  if (sending.value) stopGenerate()
  currentSession.value = null
  messages.value = []
  draft.value = ''
  nextTick(() => inputRef.value?.focus())
}

const switchSession = async (s) => {
  if (currentSession.value?.id === s.id) return
  if (sending.value) stopGenerate()
  try {
    currentSession.value = { ...s }
    const res = await api.get(`/assistant/sessions/${s.id}/messages/`)
    messages.value = (res.data || []).map(m => ({ ...m }))
    scrollToBottom()
  } catch (e) {
    console.error('加载消息失败:', e)
    ElMessage.error('加载消息失败')
  }
}

const removeSession = async (s) => {
  try {
    await api.delete(`/assistant/sessions/${s.id}/`)
    sessions.value = sessions.value.filter(x => x.id !== s.id)
    if (currentSession.value?.id === s.id) startNewChat()
    ElMessage.success('对话已删除')
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

// 发送消息
const quickAsk = (q) => {
  draft.value = q
  send()
}

const onEnter = () => {
  if (!sending.value) send()
}

const send = async (overrideText) => {
  const text = (overrideText ?? draft.value).trim()
  if (!text || sending.value) return

  draft.value = ''
  nextTick(autoGrow)
  sending.value = true

  abortController = new AbortController()

  try {
    let sessionId = currentSession.value?.session_id
    if (!sessionId) {
      messages.value = []
      const newId = `session_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
      const title = text.length > 25 ? text.slice(0, 25) + '…' : text
      const sres = await api.post('/assistant/sessions/', { session_id: newId, title })
      currentSession.value = sres.data
      sessionId = sres.data.session_id
      sessions.value.unshift(sres.data)
    }

    messages.value.push({ role: 'user', content: text, created_at: new Date().toISOString() })
    const aiMsg = { role: 'assistant', content: '', pending: true, thinking: '', thinkingExpanded: true }
    messages.value.push(aiMsg)
    scrollToBottom()

    const payload = { session_id: sessionId, message: text }
    if (selectedModel.value !== 'auto') payload.model_id = parseInt(selectedModel.value)

    await sendStream(payload, aiMsg, text)
  } catch (err) {
    handleSendError(err, aiMsg, text)
  } finally {
    sending.value = false
    abortController = null
    scrollToBottom()
  }
}

const sendStream = async (payload, aiMsg, originalText) => {
  const token = localStorage.getItem('access_token')
  const url = '/api/assistant/chat/send_message_stream/'

  let fullContent = ''
  const aiIdx = messages.value.indexOf(aiMsg)
  const currentSessionId = currentSession.value?.session_id

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify(payload),
      signal: abortController?.signal
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      if (abortController?.signal.aborted) {
        break
      }

      if (currentSession.value?.session_id !== currentSessionId) {
        break
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6)
          if (dataStr === '[DONE]') {
            return
          }

          try {
            const data = JSON.parse(dataStr)

            if (data.type === 'content') {
              fullContent += data.content

              if (aiIdx !== -1 && aiIdx < messages.value.length) {
                const thinkingMatch = fullContent.match(/\[思考\]([\s\S]*?)\[\/思考\]/)
                const thinking = thinkingMatch ? thinkingMatch[1].trim() : ''
                const cleanContent = thinking ? fullContent.replace(/\[思考\][\s\S]*?\[\/思考\]/, '').trim() : fullContent

                messages.value[aiIdx] = {
                  ...messages.value[aiIdx],
                  content: cleanContent,
                  thinking: thinking,
                  pending: false
                }
              }
              scrollToBottom()
            } else if (data.type === 'complete') {
              if (aiIdx !== -1 && aiIdx < messages.value.length) {
                messages.value[aiIdx] = {
                  ...messages.value[aiIdx],
                  ...data.assistant_message,
                  model: data.model
                }
              }
              if (data.usage) {
                showTokenUsage(data.usage.total_tokens || data.usage)
              }
              return
            }
          } catch (e) {
            console.error('解析SSE消息失败:', e)
          }
        }
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      handleSendError(err, aiMsg, originalText)
    }
  }
}

const handleSendError = (err, aiMsg, originText) => {
  const aiIdx = messages.value.indexOf(aiMsg)
  if (aiIdx === -1) return
  let msg = '回复失败，请稍后重试'
  if (err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError') {
    messages.value.splice(aiIdx, 1)
    return
  }
  const status = err?.response?.status
  const serverErr = err?.response?.data?.error
  if (err?.code === 'ECONNABORTED') {
    msg = '请求超时，请重试'
  } else if (status === 400) {
    msg = serverErr || '请配置 AI 模型'
  } else if (status === 502) {
    msg = serverErr || 'AI 模型调用失败'
  } else if (serverErr) {
    msg = serverErr
  }
  messages.value.splice(aiIdx, 1, { role: 'assistant', error: true, content: msg, _retry: originText })
  console.error('发送失败:', err)
}

const retryLast = () => {
  if (sending.value) return
  let lastUserText = ''
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') {
      lastUserText = messages.value[i].content
      break
    }
  }
  if (!lastUserText) return
  while (messages.value.length && messages.value[messages.value.length - 1].role === 'assistant') {
    messages.value.pop()
  }
  if (messages.value.length && messages.value[messages.value.length - 1].role === 'user') {
    messages.value.pop()
  }
  send(lastUserText)
}

const stopGenerate = () => {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
  sending.value = false
}

const toggleThinking = (msgId) => {
  const msg = messages.value.find(m => m.id === msgId)
  if (msg) {
    msg.thinkingExpanded = !msg.thinkingExpanded
  }
}

const downloadMessage = async (msg) => {
  if (!msg.id || !currentSession.value?.session_id) {
    ElMessage.warning('消息尚未保存，请稍后再试')
    return
  }

  ElMessage.info('正在生成文档，请稍候...')
  
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch('/api/assistant/chat/download_document/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify({
        session_id: currentSession.value.session_id,
        message_id: msg.id,
        format: 'word'
      })
    })

    if (!response.ok) {
      throw new Error('下载失败')
    }

    const blob = await response.blob()
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = `zx_ai_response_${Date.now()}.docx`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="(.+)"/)
      if (match) filename = match[1]
    }

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('文档已下载')
  } catch (err) {
    console.error('下载失败:', err)
    ElMessage.error('下载失败，请重试')
  }
}

const downloadAsTxt = (content) => {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `zx_ai_response_${Date.now()}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('文档已下载')
}

const downloadAsExcel = (content) => {
  const lines = content.split('\n').filter(l => l.trim())
  const csvLines = []
  
  for (const line of lines) {
    if (line.includes('|')) {
      const cells = line.split('|').map(c => {
        const trimmed = c.trim()
        if (trimmed.includes(',') || trimmed.includes('"') || trimmed.includes('\n')) {
          return `"${trimmed.replace(/"/g, '""')}"`
        }
        return trimmed
      })
      csvLines.push(cells.join(','))
    } else {
      csvLines.push(`"${line}"`)
    }
  }
  
  const csvContent = '\uFEFF' + csvLines.join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `zx_ai_testcases_${Date.now()}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('测试用例已下载为CSV文件')
}

onMounted(async () => {
  await loadSessions()
  loadModels()
  if (sessions.value.length > 0) {
    const lastSession = sessions.value[0]
    await switchSession(lastSession)
  } else {
    startNewChat()
  }
})

onBeforeUnmount(() => {
  if (toastTimer) clearTimeout(toastTimer)
  if (abortController) abortController.abort()
})
</script>

<style scoped lang="scss">
.chat-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  background: linear-gradient(135deg, #f0fdf4 0%, #faf5ff 30%, #f0f9ff 60%, #fff7ed 100%);
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  color: #1f2328;
}

.chat-container ::-webkit-scrollbar { width: 8px; height: 8px; }
.chat-container ::-webkit-scrollbar-track { background: transparent; }
.chat-container ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.15); border-radius: 4px; }
.chat-container ::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.25); }

.msg-enter-active { transition: all 0.32s cubic-bezier(0.4, 0, 0.2, 1); }
.msg-leave-active { transition: all 0.2s ease; position: absolute; }
.msg-enter-from { opacity: 0; transform: translateY(8px); }
.msg-leave-to { opacity: 0; transform: translateY(-4px); }
.msg-move { transition: transform 0.32s cubic-bezier(0.4, 0, 0.2, 1); }

/* Toast 动画 */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.32s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px) scale(0.95);
}

.token-toast {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #10a37f 0%, #0e8b6a 100%);
  color: white;
  padding: 12px 22px;
  border-radius: 999px;
  box-shadow: 0 10px 30px rgba(16, 163, 127, 0.35), 0 4px 12px rgba(16, 163, 127, 0.2);
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 9999;
  font-weight: 500;
  font-size: 14px;
  letter-spacing: 0.2px;

  .token-icon {
    font-size: 18px;
  }
}

/* 侧边栏 */
.sidebar {
  width: 280px;
  flex-shrink: 0;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 50%, #1e1b4b 100%);
  display: flex;
  flex-direction: column;
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  border-right: 1px solid rgba(255,255,255,0.08);
  box-shadow: 4px 0 24px rgba(0,0,0,0.15);

  &.collapsed {
    width: 68px;
  }

  .sidebar-header {
    padding: 14px 14px 10px;
    display: flex;
    gap: 10px;
    border-bottom: 1px solid rgba(255,255,255,0.08);

    .new-chat-btn {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 12px 14px;
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 50%, #1d4ed8 100%);
      border: 1px solid rgba(59, 130, 246, 0.4);
      border-radius: 12px;
      color: white;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      box-shadow: 0 2px 8px rgba(16, 163, 127, 0.25);

      &:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
        filter: brightness(1.05);
      }
      &:active { transform: translateY(0); }
    }

    .toggle-btn {
      width: 42px;
      height: 42px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(255,255,255,0.06);
      color: rgba(255,255,255,0.65);
      border-radius: 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;

      &:hover {
        background: rgba(255,255,255,0.12);
        color: white;
      }
    }
  }

  .history-list {
    flex: 1;
    overflow-y: auto;
    padding: 12px;

    .history-title {
      font-size: 11px;
      color: rgba(255,255,255,0.35);
      padding: 12px 14px 8px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.8px;
    }

    .history-items {
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .history-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 11px 14px;
      border-radius: 12px;
      cursor: pointer;
      color: rgba(255,255,255,0.7);
      transition: all 0.2s;
      position: relative;
      font-size: 13.5px;
      background: rgba(255,255,255,0.02);

      &:hover {
        background: rgba(255,255,255,0.08);
        color: white;
        transform: translateX(2px);
        .item-delete { opacity: 1; }
      }

      &.active {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.25) 0%, rgba(139, 92, 246, 0.15) 100%);
        color: white;
        box-shadow: inset 3px 0 0 #3b82f6;
      }

      .item-icon {
        font-size: 16px;
        flex-shrink: 0;
        color: rgba(255,255,255,0.45);
      }
      &.active .item-icon { color: #3b82f6; }

      .item-title {
        flex: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .item-delete {
        opacity: 0;
        font-size: 15px;
        color: rgba(255,255,255,0.5);
        transition: all 0.2s;
        flex-shrink: 0;

        &:hover { color: #ff6b6b; }
      }
    }

    .no-history {
      text-align: center;
      color: rgba(255,255,255,0.35);
      font-size: 13px;
      padding: 24px 16px;
    }
  }

  .sidebar-footer {
    padding: 14px;
    border-top: 1px solid rgba(255,255,255,0.08);

    .user-info {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 11px 14px;
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.2s;
      background: rgba(255,255,255,0.03);

      &:hover {
        background: rgba(255,255,255,0.08);
      }

      .user-avatar {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 50%, #b45309 100%);
        color: white;
        flex-shrink: 0;
      }

      .user-details {
        flex: 1;
        min-width: 0;

        .user-name {
          font-size: 14px;
          font-weight: 600;
          color: white;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .user-role {
          font-size: 12px;
          color: rgba(255,255,255,0.4);
          margin-top: 2px;
        }
      }
    }
  }
}

/* 主区域 */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  min-width: 0;
  border-radius: 24px 0 0 24px;
  margin: 16px 0 16px 0;
  box-shadow: -8px 0 32px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04);
}

/* 顶部栏 */
.top-bar {
  height: 70px;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 24px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
  background: rgba(255,255,255,0.7);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  z-index: 5;

  .back-button {
    width: 40px;
    height: 40px;
    border: 1px solid rgba(0,0,0,0.08);
    background: rgba(255,255,255,0.9);
    border-radius: 12px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #64748b;
    transition: all 0.2s;
    font-size: 18px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);

    &:hover {
      background: #f1f5f9;
      color: #1e293b;
      border-color: #cbd5e1;
      transform: translateY(-1px);
    }
    &:active { transform: translateY(0); }
  }

  .chat-title {
    flex: 1;
    text-align: center;
    min-width: 0;

    h2 {
      margin: 0;
      font-size: 16px;
      font-weight: 700;
      color: #1e293b;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }

  .model-selector {
    min-width: 180px;
  }
}

:deep(.model-selector .el-select) { width: 100%; }
:deep(.model-selector .el-select__wrapper) {
  background: rgba(255,255,255,0.9);
  border: 1px solid rgba(0,0,0,0.08);
  box-shadow: none !important;
  border-radius: 10px;
  min-height: 38px;
}
:deep(.model-selector .el-select__wrapper.is-hovering) {
  background: #f8fafc;
  border-color: #94a3b8;
}
:deep(.model-selector .el-select__placeholder) { color: #64748b; }

/* 消息区域 */
.messages-area {
  flex: 1;
  overflow-y: auto;
  background: rgba(255,255,255,0.5);
  position: relative;
}

/* 欢迎界面 */
.welcome-screen {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  background: radial-gradient(ellipse at top, rgba(59, 130, 246, 0.08) 0%, rgba(139, 92, 246, 0.04) 40%, transparent 70%);

  .welcome-icon {
    width: 80px;
    height: 80px;
    border-radius: 24px;
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 40px;
    margin-bottom: 24px;
    box-shadow: 0 16px 40px rgba(59, 130, 246, 0.3), 0 8px 16px rgba(139, 92, 246, 0.2);
    animation: floatY 3s ease-in-out infinite;
    position: relative;

    &::before {
      content: '';
      position: absolute;
      inset: -2px;
      background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
      border-radius: 26px;
      z-index: -1;
      opacity: 0.6;
      filter: blur(12px);
    }
  }

  .welcome-title {
    margin: 0 0 10px;
    font-size: 34px;
    font-weight: 700;
    color: #1e293b;
    background: linear-gradient(135deg, #1e293b 0%, #334155 50%, #475569 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.5px;
  }

  .welcome-subtitle {
    margin: 0 0 40px;
    font-size: 16px;
    color: #64748b;
    max-width: 400px;
    text-align: center;
    line-height: 1.6;
  }

  .suggestions {
    display: grid;
    grid-template-columns: repeat(2, minmax(260px, 1fr));
    gap: 16px;
    max-width: 700px;
    width: 100%;
  }

  .suggestion-card {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    padding: 18px 20px;
    background: rgba(255,255,255,0.95);
    border: 1px solid rgba(0,0,0,0.06);
    border-radius: 16px;
    cursor: pointer;
    text-align: left;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 2px 8px rgba(0,0,0,0.03);

    &:hover {
      border-color: #3b82f6;
      box-shadow: 0 12px 32px rgba(59, 130, 246, 0.15), 0 4px 12px rgba(139, 92, 246, 0.1);
      transform: translateY(-3px);

      .suggestion-icon {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        color: white;
        transform: scale(1.08);
      }
    }

    .suggestion-icon {
      width: 44px;
      height: 44px;
      flex-shrink: 0;
      border-radius: 12px;
      background: linear-gradient(135deg, #dbeafe 0%, #ede9fe 100%);
      color: #3b82f6;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      transition: all 0.25s;
    }

    .suggestion-content { flex: 1; min-width: 0; }

    .suggestion-title {
      font-size: 15px;
      font-weight: 600;
      color: #1e293b;
      margin-bottom: 5px;
    }
    .suggestion-desc {
      font-size: 13px;
      color: #64748b;
      line-height: 1.6;
    }
  }
}

@keyframes floatY {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

/* 消息列表 */
.messages-list {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 20px 32px;
  position: relative;
}

.message-row {
  display: flex;
  margin-bottom: 32px;

  &.user-message { justify-content: flex-end; }
  &.ai-message { justify-content: flex-start; }

  .message-wrapper {
    display: flex;
    gap: 16px;
    max-width: 100%;
  }

  &.user-message .message-wrapper { flex-direction: row-reverse; }

  .message-avatar {
    flex-shrink: 0;
    margin-top: 4px;
  }

  .avatar {
    width: 36px;
    height: 36px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    color: white;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    transition: all 0.2s;
  }

  .user-avatar {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 50%, #4338ca 100%);
  }

  .ai-avatar {
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
    box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3);
  }

  .message-content {
    flex: 1;
    min-width: 0;
    max-width: calc(100% - 52px);
  }

  &.user-message .message-content {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
  }

  .message-header {
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  &.user-message .message-header { flex-direction: row-reverse; }

  .sender-name {
    font-size: 13.5px;
    font-weight: 600;
    color: #1e293b;
  }

  .model-tag {
    font-size: 11px;
    color: #3b82f6;
    background: rgba(59, 130, 246, 0.1);
    padding: 3px 10px;
    border-radius: 999px;
    font-weight: 500;
    margin-left: 6px;
  }

  .thinking-box {
    padding: 0;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.06) 0%, rgba(139, 92, 246, 0.06) 100%);
    border: 1px dashed rgba(59, 130, 246, 0.3);
    border-radius: 12px;
    margin-bottom: 10px;
    animation: fadeIn 0.3s ease;
    overflow: hidden;
    cursor: pointer;
    transition: all 0.25s;

    &:hover {
      border-color: rgba(59, 130, 246, 0.5);
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%);
    }

    .thinking-header {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 16px;
      background: rgba(59, 130, 246, 0.06);
    }

    .thinking-icon {
      font-size: 15px;
      color: #3b82f6;
      flex-shrink: 0;
    }

    .thinking-title {
      font-size: 12.5px;
      color: #3b82f6;
      font-weight: 600;
      flex: 1;
    }

    .thinking-toggle {
      font-size: 13px;
      color: #94a3b8;
      transition: transform 0.25s;

      &.expanded {
        transform: rotate(180deg);
      }
    }

    .thinking-content {
      padding: 10px 16px 12px;
      border-top: 1px dashed rgba(59, 130, 246, 0.2);

      .thinking-text {
        font-size: 13.5px;
        color: #64748b;
        font-style: italic;
        line-height: 1.7;
      }
    }
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .message-bubble { padding: 0; max-width: 100%; min-width: 0; }

  .message-text {
    font-size: 15.5px;
    line-height: 1.75;
    color: #1e293b;
    word-wrap: break-word;
    overflow-wrap: break-word;
    max-width: 100%;
    overflow: hidden;
    background: rgba(255,255,255,0.95);
    padding: 14px 18px;
    border-radius: 18px 18px 18px 6px;
    border: 1px solid rgba(0,0,0,0.06);
    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
  }

  .user-message .message-text {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 50%, #4338ca 100%);
    color: white;
    padding: 14px 18px;
    border-radius: 18px 18px 6px 18px;
    display: inline-block;
    max-width: 100%;
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.25);
    border: none;
  }

  .message-actions {
    display: flex;
    gap: 6px;
    margin-top: 8px;
    opacity: 0;
    transition: opacity 0.2s;
  }
  &:hover .message-actions { opacity: 1; }

  .action-btn {
    width: 30px;
    height: 30px;
    border: 1px solid transparent;
    background: transparent;
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #8e8ea0;
    transition: all 0.18s;
    font-size: 14px;

    &:hover {
      background: #f0f0f3;
      color: #1f2328;
      border-color: #ececf1;
    }

    &.auto-test-btn {
      &:hover {
        background: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
        border-color: rgba(59, 130, 246, 0.2);
      }
    }
  }

  .bubble-loading {
    display: inline-flex;
    gap: 6px;
    padding: 16px 20px;
    background: #f7f7f8;
    border-radius: 16px 16px 16px 4px;
    border: 1px solid #ececf1;

    .loading-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: linear-gradient(135deg, #10a37f 0%, #0e8b6a 100%);
      animation: loading 1.4s infinite ease-in-out;

      &:nth-child(2) { animation-delay: 0.2s; }
      &:nth-child(3) { animation-delay: 0.4s; }
    }
  }

  .bubble-error {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 18px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 14px;
    color: #b91c1c;

    .error-icon { font-size: 20px; flex-shrink: 0; }
    .error-text { flex: 1; font-size: 14px; line-height: 1.5; }
  }

  .md-image {
    max-width: 450px;
    max-height: 450px;
    width: auto;
    height: auto;
    object-fit: contain;
    border-radius: 8px;
    display: block;
    margin: 8px 0;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  :deep(.message-text img) {
    max-width: 450px;
    max-height: 450px;
    width: auto;
    height: auto;
    object-fit: contain;
    border-radius: 8px;
    display: block;
    margin: 8px 0;
  }
}

@keyframes loading {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

/* Markdown 样式 */
.message-text {
  :deep(.md-p) {
    margin: 0 0 10px;
    &:last-child { margin-bottom: 0; }
  }
  :deep(h2), :deep(h3), :deep(h4), :deep(h5) {
    margin: 16px 0 8px;
    color: #1f2328;
    line-height: 1.4;
    font-weight: 700;
  }
  :deep(h2) { font-size: 19px; }
  :deep(h3) { font-size: 17px; }
  :deep(h4) { font-size: 15.5px; }
  :deep(h5) { font-size: 14.5px; color: #4b5563; }
  :deep(ul), :deep(ol) {
    margin: 10px 0;
    padding-left: 24px;
    line-height: 1.7;
  }
  :deep(li) { margin: 4px 0; }
  :deep(strong) { font-weight: 700; color: #1f2328; }
  :deep(em) { font-style: italic; color: #4b5563; }
  :deep(blockquote) {
    margin: 10px 0;
    padding: 8px 14px;
    border-left: 3px solid #10a37f;
    background: #f0fdf4;
    color: #4b5563;
    border-radius: 0 8px 8px 0;
  }
  :deep(hr) { border: 0; border-top: 1px solid #ececf1; margin: 14px 0; }
  :deep(.md-link) {
    color: #10a37f;
    text-decoration: none;
    border-bottom: 1px solid rgba(16, 163, 127, 0.3);
    transition: all 0.18s;
    &:hover { border-bottom-color: #10a37f; }
  }
  :deep(.code-block-wrapper) {
    margin: 12px 0;
    border-radius: 12px;
    overflow: hidden;
    background: #1e1e22;
    border: 1px solid #2d2d35;
    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
  }
  :deep(.code-block-header) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 14px;
    background: #2a2a32;
    color: rgba(255,255,255,0.6);
    font-size: 12px;
    border-bottom: 1px solid #2d2d35;
  }
  :deep(.code-lang) {
    font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  :deep(.code-copy) {
    cursor: pointer;
    padding: 2px 10px;
    border-radius: 4px;
    background: rgba(255,255,255,0.06);
    color: rgba(255,255,255,0.8);
    transition: all 0.18s;
    user-select: none;
    font-size: 12px;
    &:hover { background: rgba(16, 163, 127, 0.25); color: white; }
  }
  :deep(.code-block) {
    margin: 0;
    padding: 14px 16px;
    overflow-x: auto;
    color: #e5e7eb;
    font-family: 'SF Mono', 'Consolas', 'Monaco', 'Cascadia Code', 'Courier New', monospace;
    font-size: 13.5px;
    line-height: 1.6;
    background: #1e1e22;

    code {
      color: inherit;
      background: transparent;
      font-family: inherit;
      padding: 0;
    }
  }
  :deep(.inline-code) {
    background: rgba(16, 163, 127, 0.1);
    color: #0e8b6a;
    padding: 1px 6px;
    border-radius: 4px;
    font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
    font-size: 13.5px;
    font-weight: 500;
    border: 1px solid rgba(16, 163, 127, 0.18);
  }
  :deep(.md-table) {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 14px;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 0 0 1px #ececf1;

    th, td {
      padding: 10px 14px;
      text-align: left;
      border-bottom: 1px solid #ececf1;
    }
    th { background: #f7f7f8; font-weight: 600; color: #1f2328; }
    tr:last-child td { border-bottom: 0; }
    tr:hover td { background: #fafafa; }
  }
}

.user-message .message-text {
  :deep(.inline-code) {
    background: rgba(255,255,255,0.18);
    color: white;
    border-color: rgba(255,255,255,0.25);
  }
  :deep(.md-link) {
    color: white;
    border-bottom-color: rgba(255,255,255,0.5);
  }
  :deep(strong) { color: white; }
  :deep(em) { color: rgba(255,255,255,0.85); }
  :deep(blockquote) {
    background: rgba(255,255,255,0.12);
    border-left-color: white;
    color: rgba(255,255,255,0.9);
  }
}

/* 输入区域 */
.input-area {
  flex-shrink: 0;
  padding: 20px 24px 24px;
  background: rgba(255,255,255,0.85);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-top: 1px solid rgba(0,0,0,0.06);
  position: relative;
  z-index: 4;

  &::before {
    content: '';
    position: absolute;
    top: -24px;
    left: 0;
    right: 0;
    height: 24px;
    background: linear-gradient(180deg, transparent 0%, rgba(255,255,255,0.5) 100%);
    pointer-events: none;
  }

  .input-wrapper {
    max-width: 800px;
    margin: 0 auto;
    position: relative;
    display: flex;
    align-items: flex-end;
    background: rgba(255,255,255,0.95);
    border: 2px solid rgba(0,0,0,0.06);
    border-radius: 20px;
    padding: 12px 14px 12px 20px;
    transition: all 0.25s;
    box-shadow: 0 4px 20px rgba(0,0,0,0.05), inset 0 1px 0 rgba(255,255,255,0.8);

    &:focus-within {
      border-color: #3b82f6;
      box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12), 0 8px 24px rgba(59, 130, 246, 0.08);
    }
  }

  .chat-input {
    flex: 1;
    border: none;
    outline: none;
    background: transparent;
    resize: none;
    font-size: 15.5px;
    line-height: 1.65;
    color: #1e293b;
    max-height: 200px;
    min-height: 28px;
    padding: 6px 0;
    font-family: inherit;

    &::placeholder { color: #94a3b8; }
    &:disabled { cursor: not-allowed; opacity: 0.5; }
  }

  .send-button,
  .stop-button {
    width: 42px;
    height: 42px;
    border: none;
    border-radius: 14px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    margin-left: 12px;
    flex-shrink: 0;
    font-size: 20px;
  }

  .send-button {
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
    color: white;
    box-shadow: 0 4px 16px rgba(59, 130, 246, 0.35);

    &:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 6px 24px rgba(59, 130, 246, 0.45);
    }
    &:active { transform: translateY(0); }
    &:disabled {
      background: #cbd5e1;
      cursor: not-allowed;
      box-shadow: none;
    }
  }

  .stop-button {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    color: white;
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);

    .stop-icon {
      width: 14px;
      height: 14px;
      background: white;
      border-radius: 3px;
    }

    &:hover {
      background: #dc2626;
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4);
    }
  }

  .input-footer {
    max-width: 800px;
    margin: 12px auto 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 12.5px;
    color: #64748b;

    .model-info {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #3b82f6;
      font-weight: 600;
    }
    .disclaimer { color: #94a3b8; }
  }
}

/* 响应式 */
@media (max-width: 768px) {
  .sidebar {
    position: absolute;
    z-index: 10;
    height: 100%;
    box-shadow: 4px 0 24px rgba(0,0,0,0.25);
  }
  .main-area {
    border-radius: 0;
    margin: 0;
    box-shadow: none;
  }
  .suggestions { grid-template-columns: 1fr; }
  .messages-list { padding: 16px 14px 24px; }
  .top-bar { padding: 0 12px; height: 64px; }
  .input-area { padding: 12px 14px 20px; }
  .message-wrapper { gap: 10px; }
  .welcome-title { font-size: 26px; }
  .welcome-icon { width: 64px; height: 64px; font-size: 32px; }
  .chat-container {
    background: #ffffff;
  }
}

@media (max-width: 480px) {
  .sidebar {
    width: 240px;
  }
  .sidebar.collapsed {
    width: 56px;
  }
  .messages-list { padding: 12px 10px 20px; }
  .message-text {
    font-size: 14px;
    padding: 10px 14px;
  }
  .user-message .message-text {
    padding: 10px 14px;
  }
  .avatar {
    width: 32px;
    height: 32px;
    font-size: 16px;
  }
  .input-wrapper {
    padding: 10px 12px 10px 16px;
    border-radius: 16px;
  }
  .send-button,
  .stop-button {
    width: 36px;
    height: 36px;
    font-size: 16px;
  }
}
</style>
