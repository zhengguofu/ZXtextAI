<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('uiAutomation.ai.title') }}</h1>
    </div>

    <div class="card-container">
      <!-- AI 配置状态提示（仅显示成功提示，不阻塞操作） -->
      <el-alert
        v-if="aiConfig.configured === true && aiConfig.message"
        title="AI 模型已配置"
        type="success"
        :closable="false"
        show-icon
        style="margin-bottom: 20px;"
      >
        <template #default>
          <span>{{ aiConfig.message }}</span>
        </template>
      </el-alert>

      <el-row :gutter="20">
        <el-col :span="12">
          <div class="section-title">{{ $t('uiAutomation.ai.taskInput') }}</div>
          <el-form :model="taskForm" label-position="top">
            <el-form-item label="目标网址（可选）">
              <el-input
                v-model="taskForm.url"
                placeholder="https://example.com 或 http://localhost:8080"
                clearable
              />
            </el-form-item>

            <el-form-item label="上传文件（可选）">
              <el-upload
                v-model:file-list="fileList"
                :auto-upload="false"
                :limit="1"
                accept=".txt,.csv,.md,.xlsx,.xls,.doc,.docx,.json"
                :on-change="handleFileChange"
                :on-remove="handleFileRemove"
                drag
              >
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">
                  将文件拖到此处，或<em>点击上传</em>
                </div>
                <template #tip>
                  <div class="el-upload__tip">支持 .txt/.csv/.md/.xlsx/.json 等格式，用于提供需求文档或参考用例</div>
                </template>
              </el-upload>
            </el-form-item>

            <el-form-item :label="$t('uiAutomation.ai.taskDescription')" required>
              <el-input
                v-model="taskForm.description"
                type="textarea"
                :rows="8"
                :placeholder="$t('uiAutomation.ai.taskPlaceholder')"
                maxlength="5000"
                show-word-limit
              />
              <div class="form-tip">
                提示：可在描述中指定测试用例表头，例如"表头：序号、前置条件、测试流程、预期结果、实际结果、优先级"
              </div>
            </el-form-item>

            <!-- 自定义表头预览 -->
            <el-form-item label="????????????????">
              <el-input
                v-model="taskForm.caseHeaders"
                placeholder="id, ????, ????, ????, ??, ??, ???"
                clearable
              />
              <div class="form-tip">????????????????????</div>
            </el-form-item>

            <el-form-item v-if="parsedHeaders.length > 0" label="已识别表头">
              <div class="headers-tags">
                <el-tag v-for="h in parsedHeaders" :key="h" size="small" type="success" style="margin-right: 4px; margin-bottom: 4px;">{{ h }}</el-tag>
                <el-button link size="small" @click="parsedHeaders = []">清除</el-button>
              </div>
            </el-form-item>

            <el-form-item label="视频录制">
              <el-switch
                v-model="taskForm.enableVideo"
                active-text="开启"
                inactive-text="关闭"
              />
              <span style="margin-left: 10px; color: #909399; font-size: 12px;">
                开启后将录制执行过程并生成MP4视频文件，保存到 ai_agent_history 目录
              </span>
            </el-form-item>

            <el-form-item label="步骤截图与AI讲解">
              <el-switch
                v-model="taskForm.enableScreenshots"
                active-text="开启"
                inactive-text="关闭"
              />
              <span style="margin-left: 10px; color: #909399; font-size: 12px;">
                每一步自动截图并由AI生成文字讲解说明
              </span>
            </el-form-item>

            <el-form-item label="无头模式（后台运行，不弹浏览器窗口）">
              <el-switch
                v-model="taskForm.headless"
                active-text="后台"
                inactive-text="显示"
              />
              <span style="margin-left: 10px; color: #909399; font-size: 12px;">
                无头模式下浏览器在后台运行，不被遮挡干扰
              </span>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                @click="handleRun"
                :loading="running"
                :disabled="!taskForm.description"
              >
                <el-icon><VideoPlay /></el-icon>
                {{ $t('uiAutomation.ai.startExecution') }}
              </el-button>
              <el-button
                type="danger"
                @click="handleStop"
                :disabled="!running || analyzing"
                v-if="running"
              >
                <el-icon><SwitchButton /></el-icon>
                {{ $t('uiAutomation.ai.stopExecution') }}
              </el-button>
              <el-button
                type="success"
                @click="handleSaveAsCase"
                :disabled="!taskForm.description"
              >
                <el-icon><DocumentAdd /></el-icon>
                {{ $t('uiAutomation.ai.saveAsCase') }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            :title="$t('uiAutomation.ai.tip')"
            type="info"
            :closable="false"
            style="margin-top: 20px;"
          >
            <template #default>
              <div>全程自动化优先使用 browser_use_text / browser_use_vision 角色模型，异常时自动降级到 AI 测试/用例编写模型。</div>
              <div>{{ $t('uiAutomation.ai.tipContent2') }}</div>
            </template>
          </el-alert>

          <div class="section-title" style="margin-top: 20px;">{{ $t('uiAutomation.ai.executionLogs') }}</div>
          <div class="log-container" ref="logContainer">
            <div v-if="!logs && !running" class="empty-logs">
              {{ $t('uiAutomation.ai.noLogs') }}
            </div>
            <pre v-else class="log-content">{{ logs }}</pre>
          </div>
        </el-col>

        <el-col :span="12">
          <div class="section-title">{{ $t('uiAutomation.ai.taskDetails') }}</div>
          <div class="task-list-container">
            <div v-if="analyzing" class="analyzing-state">
              <el-icon class="is-loading"><Loading /></el-icon>
            </div>
            <div v-else-if="plannedTasks.length > 0">
              <div
                v-for="task in plannedTasks"
                :key="task.id"
                class="task-item"
                :class="task.status"
              >
                <div class="task-status-icon">
                  <el-icon v-if="task.status === 'completed'" color="#67C23A"><CircleCheckFilled /></el-icon>
                  <el-icon v-else-if="task.status === 'in_progress'" class="is-loading" color="#409EFF"><Loading /></el-icon>
                  <el-icon v-else color="#909399"><CircleCheck /></el-icon>
                </div>
                <div class="task-content">
                  <span class="task-id">{{ task.id }}.</span>
                  <span class="task-desc">{{ task.description }}</span>
                </div>
              </div>
            </div>
            <div v-else class="empty-tasks">
              {{ $t('uiAutomation.ai.noTasks') }}
            </div>
          </div>

          <!-- 生成的测试用例展示 -->
          <div v-if="generatedTestCases.length > 0" class="test-case-section">
            <div class="section-title" style="margin-top: 20px;">
              生成的测试用例（{{ generatedTestCases.length }} 条）
            </div>
            <div class="test-case-table-wrapper">
              <el-table
                :data="generatedTestCases"
                border
                stripe
                size="small"
                max-height="400"
                style="width: 100%;"
              >
                <el-table-column
                  v-for="header in testCaseHeaders"
                  :key="header"
                  :prop="header"
                  :label="header"
                  :min-width="getColumnWidth(header)"
                  show-overflow-tooltip
                />
              </el-table>
            </div>
          </div>

          <!-- 执行结果导出（执行完成后显示） -->
          <div v-if="gifPath || screenshotsSequence.length > 0" class="evidence-section">
            <div class="section-title" style="margin-top: 20px;">Automation Evidence</div>
            <el-card v-if="gifPath" shadow="never" class="recording-card">
              <div class="evidence-heading">Screen recording</div>
              <img :src="getMediaUrl(gifPath)" class="recording-preview" alt="automation recording" />
              <div class="evidence-link">
                <el-link :href="getMediaUrl(gifPath)" target="_blank" type="primary">Open recording</el-link>
              </div>
            </el-card>
            <div v-if="screenshotsSequence.length > 0" class="screenshot-grid">
              <div v-for="item in screenshotsSequence" :key="`${item.step}-${item.path}`" class="screenshot-card">
                <img :src="getMediaUrl(item.path)" class="screenshot-image" alt="automation screenshot" />
                <div class="screenshot-meta">
                  <span>{{ screenshotDescription(item) }}</span>
                  <small>{{ item.time || '' }}</small>
                </div>
              </div>
            </div>
          </div>

          <div v-if="executionFinished && !running" class="result-export">
            <div class="section-title" style="margin-top: 20px;">执行结果导出</div>
            <el-card shadow="never">
              <el-row :gutter="10">
                <el-col :span="8">
                  <el-button type="primary" plain style="width: 100%;" @click="exportReport">
                    <el-icon><Document /></el-icon> 导出测试报告
                  </el-button>
                </el-col>
                <el-col :span="8">
                  <el-button type="success" plain style="width: 100%;" @click="exportExcel">
                    <el-icon><Grid /></el-icon> 导出 Excel 表格
                  </el-button>
                </el-col>
                <el-col :span="8">
                  <el-button type="warning" plain style="width: 100%;" @click="exportDoc">
                    <el-icon><DocumentCopy /></el-icon> 导出 Word 文档
                  </el-button>
                </el-col>
              </el-row>
            </el-card>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 保存为用例对话框 -->
    <el-dialog v-model="showSaveDialog" :title="$t('uiAutomation.ai.saveAsCaseTitle')" width="500px" :close-on-click-modal="false">
      <el-form :model="saveForm" :rules="saveRules" ref="saveFormRef" label-width="80px">
        <el-form-item :label="$t('uiAutomation.ai.caseName')" prop="name">
          <el-input v-model="saveForm.name" :placeholder="$t('uiAutomation.ai.caseNamePlaceholder')" /> 
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.common.description')" prop="description">
          <el-input v-model="saveForm.description" type="textarea" :placeholder="$t('uiAutomation.ai.caseDescPlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showSaveDialog = false">{{ $t('uiAutomation.common.cancel') }}</el-button> 
          <el-button type="primary" @click="confirmSaveCase" :loading="saving">{{ $t('uiAutomation.common.save') }}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
defineOptions({ name: 'AITesting' })
import { ref, reactive, nextTick, computed, watch, onMounted, onUnmounted, onActivated, onDeactivated } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  VideoPlay, DocumentAdd, CircleCheckFilled, CircleCheck, Loading, SwitchButton,
  Document, Grid, DocumentCopy, UploadFilled
} from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import {
  runAdhocAITask,
  createAICase,
  getAIExecutionRecordDetail,
  stopAITask,
  checkAIConfig
} from '@/api/ui_automation'

const { t } = useI18n()
const router = useRouter()

const running = ref(false)
const analyzing = ref(false)
const saving = ref(false)
const logs = ref('')
const plannedTasks = ref([])
const currentExecutionId = ref(null)
const logContainer = ref(null)
const showConfigAlert = ref(false)
const executionFinished = ref(false)
const generatedTestCases = ref([])
const screenshotsSequence = ref([])
const gifPath = ref('')
const aiConfig = reactive({
  configured: null,
  modelName: '',
  provider: '',
  role: '',
  message: ''
})

const taskForm = reactive({
  url: '',
  description: '',
  caseHeaders: '',
  enableVideo: true,
  enableScreenshots: true,
  headless: true  // 默认无头后台运行
})

const fileList = ref([])
const uploadedFile = ref(null)
const parsedHeaders = ref([])

let pollTimeoutId = null
let pollRetryCount = 0
const minPollInterval = 1500
const maxPollInterval = 15000
const maxRetryCount = 5

watch(() => taskForm.description, (val) => {
  if (val && !taskForm.caseHeaders) {
    const h = parseCustomHeaders(val)
    if (h) parsedHeaders.value = h
  }
}, { immediate: false })

watch(() => taskForm.caseHeaders, (val) => {
  const h = parseCustomHeaders(val)
  parsedHeaders.value = h || []
}, { immediate: false })

function handleFileChange(file) {
  fileList.value = [file]
  const reader = new FileReader()
  reader.onload = (e) => {
    const content = e.target.result
    if (typeof content === 'string') {
      const base64content = content.includes('base64,') ? content.split('base64,')[1] : btoa(unescape(encodeURIComponent(content)))
      uploadedFile.value = {
        filename: file.name,
        content: base64content
      }
      ElMessage.success(`已加载文件: ${file.name}`)
    }
  }
  reader.readAsText(file.raw)
}

function handleFileRemove() {
  fileList.value = []
  uploadedFile.value = null
}

const showSaveDialog = ref(false)
const saveForm = reactive({
  name: '',
  description: ''
})
const saveFormRef = ref(null)

const saveRules = computed(() => ({
  name: [{ required: true, message: t('uiAutomation.ai.rules.nameRequired'), trigger: 'blur' }]
}))

const testCaseHeaders = computed(() => {
  if (generatedTestCases.value.length === 0) return []
  const first = generatedTestCases.value[0]
  const defaultOrder = ['ID', '测试模块', '前置条件', '执行步骤', '预期结果', '实际结果', '优先级', '用例类型', '自动化类型', '是否通过']
  const ordered = defaultOrder.filter(h => h in first)
  const remaining = Object.keys(first).filter(h => !ordered.includes(h))
  return [...ordered, ...remaining]
})

const getColumnWidth = (header) => {
  const widthMap = {
    'ID': 60,
    '测试模块': 100,
    '前置条件': 120,
    '执行步骤': 200,
    '预期结果': 200,
    '实际结果': 200,
    '优先级': 70,
    '用例类型': 90,
    '自动化类型': 90,
    '是否通过': 80,
  }
  return widthMap[header] || 100
}

function parseCustomHeaders(description) {
  if (!description) return null
  const colonFull = String.fromCharCode(0xff1a)
  const commaFull = String.fromCharCode(0xff0c)
  const commaIdeographic = String.fromCharCode(0x3001)
  const periodIdeographic = String.fromCharCode(0x3002)
  const semicolonFull = String.fromCharCode(0xff1b)
  const headerWords = [
    'header', 'headers', 'columns', 'custom_headers', 'custom header',
    String.fromCharCode(0x8868, 0x5934),
    String.fromCharCode(0x5b57, 0x6bb5),
    String.fromCharCode(0x5217, 0x540d),
    String.fromCharCode(0x5934, 0x90e8),
    String.fromCharCode(0x6392, 0x5217),
  ]
  const removeWords = [
    String.fromCharCode(0x8fdb, 0x884c, 0x6392, 0x5217),
    String.fromCharCode(0x6392, 0x5217),
    String.fromCharCode(0x751f, 0x6210),
    String.fromCharCode(0x6d4b, 0x8bd5, 0x7528, 0x4f8b),
    String.fromCharCode(0x7528, 0x4f8b),
    String.fromCharCode(0x6309, 0x7167),
    String.fromCharCode(0x8868, 0x5934),
    String.fromCharCode(0x5b57, 0x6bb5),
    String.fromCharCode(0x5217, 0x540d),
  ]
  const separators = new RegExp(`[,${commaFull}${commaIdeographic}|/\\t]+|\\s{2,}`, 'g')
  const trimChars = new RegExp(`^[:${colonFull}]+|[${periodIdeographic}${semicolonFull};,${commaFull}]+$`, 'g')
  const candidates = []

  for (const line of String(description).split(/\r?\n/)) {
    const raw = line.trim()
    if (!raw) continue
    const lower = raw.toLowerCase()
    const looksLikeHeader = headerWords.some(w => lower.includes(String(w).toLowerCase()) || raw.includes(w))
    const colonParts = []
    if (raw.includes(':')) colonParts.push(raw.split(':').slice(1).join(':'))
    if (raw.includes(colonFull)) colonParts.push(raw.split(colonFull).slice(1).join(colonFull))
    for (const part of colonParts) {
      if (part.split(separators).filter(Boolean).length >= 3) candidates.push(part)
    }
    if (looksLikeHeader) candidates.push(...colonParts, raw)
  }

  for (const candidate of candidates) {
    let cleaned = candidate
    removeWords.forEach(word => { cleaned = cleaned.split(word).join('') })
    const headers = cleaned
      .split(separators)
      .map(h => h.trim().replace(trimChars, ''))
      .filter(h => h.length > 0 && h.length <= 30)
    const unique = [...new Set(headers)]
    if (unique.length >= 3) return unique
  }
  return null
}


const getMediaUrl = (path) => {
  if (!path) return ''
  if (/^https?:\/\//.test(path)) return path
  return path.startsWith('/') ? path : `/${path}`
}

const screenshotDescription = (item) => {
  const step = item?.step ? `Step ${item.step}` : 'Step'
  return item?.description || item?.action || item?.title || `${step} screenshot evidence`
}


const handleRun = async () => {
  showConfigAlert.value = false
  executionFinished.value = false
  running.value = true
  analyzing.value = true
  logs.value = t('uiAutomation.ai.messages.initAgent')
  plannedTasks.value = []
  generatedTestCases.value = []
  screenshotsSequence.value = []
  gifPath.value = ''

  // 立即给用户反馈
  ElMessage.info('已提交任务，正在初始化 AI Agent，请稍候...')
  logs.value += '\n[' + new Date().toLocaleTimeString() + '] 提交任务，等待后端确认...'
  // 自动滚动到日志区
  nextTick(() => {
    if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight
  })

  const customHeaders = parseCustomHeaders(taskForm.caseHeaders) || (parsedHeaders.value.length > 0 ? [...parsedHeaders.value] : parseCustomHeaders(taskForm.description))

  const requestData = {
    task_description: taskForm.description,
    execution_mode: 'text',
    enable_video: taskForm.enableVideo,
    enable_screenshots: taskForm.enableScreenshots,
    headless: taskForm.headless
  }
  if (taskForm.url) {
    requestData.target_url = taskForm.url
  }
  if (customHeaders) {
    requestData.custom_headers = customHeaders
  }
  if (uploadedFile.value) {
    requestData.uploaded_file = uploadedFile.value
  }

  // 15秒仍未收到 execution_id 就提示后端可能卡住
  const stuckTimer = setTimeout(() => {
    if (running.value && !currentExecutionId.value) {
      logs.value += '\n[' + new Date().toLocaleTimeString() + '] ⚠️ 后端 15 秒未返回任务 ID，可能 AI 模型/浏览器初始化较慢，请再等等或检查后端日志'
      ElMessage.warning('后端响应较慢，如果超过 2 分钟仍无反应请检查后端日志')
      nextTick(() => {
        if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight
      })
    }
  }, 15000)

  try {
    console.log('[ui-auto][run_adhoc] payload=', requestData)
    const response = await runAdhocAITask(requestData)
    clearTimeout(stuckTimer)

    currentExecutionId.value = response.data.execution_id
    logs.value += '\n[' + new Date().toLocaleTimeString() + '] ✅ 任务已创建 execution_id=' + currentExecutionId.value
    ElMessage.success(t('uiAutomation.ai.messages.startSuccess'))

    pollLogs()

  } catch (error) {
    clearTimeout(stuckTimer)
    console.error('[ui-auto][run_adhoc] 失败:', error)
    const errorMsg = error.response?.data?.error || error.message || ''
    logs.value += '\n[' + new Date().toLocaleTimeString() + '] ❌ 任务提交失败: ' + errorMsg
    ElMessage.error(t('uiAutomation.ai.messages.startFailed') + ': ' + errorMsg)

    if (errorMsg.includes('No API Key') || errorMsg.includes('No usable AI model') || errorMsg.includes('api_key') || errorMsg.includes('API Key') || error.response?.status === 500) {
      showConfigAlert.value = true
    }

    running.value = false
    analyzing.value = false
  }
}

const goToConfig = () => {
  router.push('/configuration/ai-model')
}

const exportReport = () => {
  const report = generateReport()
  const blob = new Blob([report], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `AI测试报告_${new Date().toLocaleDateString()}.md`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('测试报告已导出')
}

const exportExcel = () => {
  const rows = plannedTasks.value.map(t => ({
    步骤: t.id,
    描述: t.description,
    状态: t.status === 'completed' ? '通过' : t.status === 'in_progress' ? '执行中' : '待执行',
    备注: ''
  }))
  const csv = convertToCSV(rows)
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `AI测试用例_${new Date().toLocaleDateString()}.csv`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('Excel 表格已导出(CSV 格式)')
}

const exportDoc = () => {
  const html = generateWordDoc()
  const blob = new Blob([html], { type: 'application/msword;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `AI测试文档_${new Date().toLocaleDateString()}.doc`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('Word 文档已导出')
}

const generateReport = () => {
  const now = new Date().toLocaleString()
  const status = plannedTasks.value.every(t => t.status === 'completed') ? '✅ 全部通过'
    : plannedTasks.value.some(t => t.status === 'failed') ? '❌ 存在错误' : '🔄 部分完成'   

  let md = `# AI 智能测试执行报告\n\n`
  md += `**执行时间**: ${now}\n\n`
  md += `**任务描述**: ${taskForm.description}\n\n`
  if (taskForm.url) md += `**目标网址**: ${taskForm.url}\n\n`
  md += `**执行状态**: ${status}\n\n`
  md += `**总步骤数**: ${plannedTasks.value.length}\n\n`
  md += `---\n\n`
  md += `## 执行步骤明细\n\n`
  plannedTasks.value.forEach(t => {
    const icon = t.status === 'completed' ? '✅' : t.status === 'failed' ? '❌' : '🔄'
    md += `### ${icon} 步骤 ${t.id}\n\n`
    md += `- **描述**: ${t.description}\n`
    md += `- **状态**: ${t.status}\n\n`
  })
  md += `## 执行日志\n\n\`\`\`\n${logs.value}\n\`\`\`\n`
  return md
}

const generateWordDoc = () => {
  const now = new Date().toLocaleString()
  let html = `<html><head><meta charset="utf-8"><title>AI测试报告</title></head><body>`
  html += `<h1>AI 智能测试执行报告</h1>`
  html += `<p><b>执行时间：</b>${now}</p>`
  html += `<p><b>任务描述：</b>${taskForm.description}</p>`
  if (taskForm.url) html += `<p><b>目标网址：</b>${taskForm.url}</p>`
  html += `<h2>执行步骤</h2><table border="1" cellpadding="6"><tr><th>步骤</th><th>描述</th><th>状态</th></tr>`
  plannedTasks.value.forEach(t => {
    const statusText = t.status === 'completed' ? '通过' : t.status === 'failed' ? '错误' : '待执行'
    html += `<tr><td>${t.id}</td><td>${t.description}</td><td>${statusText}</td></tr>`
  })
  html += `</table><h2>执行日志</h2><pre>${logs.value.replace(/</g, '&lt;')}</pre></body></html>`     
  return html
}

const convertToCSV = (rows) => {
  if (!rows.length) return ''
  const headers = Object.keys(rows[0])
  const lines = [headers.join(','), ...rows.map(r => headers.map(h => `"${(r[h] || '').toString().replace(/"/g, '""')}"`).join(','))]
  return lines.join('\n')
}

const handleStop = async () => {
  if (!currentExecutionId.value) return

  try {
    await stopAITask(currentExecutionId.value)
    ElMessage.warning(t('uiAutomation.ai.messages.stopping'))
  } catch (error) {
    console.error('停止失败:', error)
    ElMessage.error(t('uiAutomation.ai.messages.stopFailed'))
  }
}

const pollLogs = () => {
  if (pollTimeoutId) {
    clearTimeout(pollTimeoutId)
  }
  pollRetryCount = 0
  doPoll()
}

const doPoll = async () => {
  if (!currentExecutionId.value) {
    return
  }

  try {
    const response = await getAIExecutionRecordDetail(currentExecutionId.value, { timeout: 15000 })
    const record = response.data

    logs.value = record.logs || ''
    plannedTasks.value = record.planned_tasks || []
    generatedTestCases.value = record.generated_test_cases || []
    screenshotsSequence.value = record.screenshots_sequence || []
    gifPath.value = record.gif_path || ''

    if (plannedTasks.value.length > 0) {
      analyzing.value = false
    }

    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    })

    if (record.status === 'passed' || record.status === 'failed' || record.status === 'stopped') {    
      running.value = false
      analyzing.value = false
      executionFinished.value = true
      if (record.status === 'passed') {
        ElMessage.success(t('uiAutomation.ai.messages.executionSuccess'))
      } else if (record.status === 'stopped') {
        ElMessage.warning(t('uiAutomation.ai.messages.taskStopped'))
      } else {
        ElMessage.error(t('uiAutomation.ai.messages.executionFailed'))
      }
      return
    }

    pollRetryCount = 0
    scheduleNextPoll()
  } catch (error) {
    console.error('获取日志失败:', error)
    pollRetryCount++
    
    if (pollRetryCount >= maxRetryCount) {
      console.error('轮询失败次数过多，停止轮询')
      running.value = false
      analyzing.value = false
      executionFinished.value = true
      ElMessage.error(t('uiAutomation.ai.messages.pollFailed') || '轮询失败次数过多')
      return
    }
    
    scheduleNextPoll()
  }
}

const scheduleNextPoll = () => {
  const backoffMultiplier = Math.pow(2, pollRetryCount)
  const interval = Math.min(minPollInterval * backoffMultiplier, maxPollInterval)
  
  pollTimeoutId = setTimeout(() => {
    doPoll()
  }, interval)
}

const stopPolling = () => {
  if (pollTimeoutId) {
    clearTimeout(pollTimeoutId)
    pollTimeoutId = null
  }
  pollRetryCount = 0
}

const handleSaveAsCase = () => {
  showSaveDialog.value = true
  saveForm.name = ''
  saveForm.description = ''
}

const checkConfig = async () => {
  try {
    const response = await checkAIConfig()
    const data = response.data
    if (data.configured) {
      aiConfig.configured = true
      aiConfig.modelName = data.model_name
      aiConfig.provider = data.provider
      aiConfig.role = data.role
      aiConfig.message = data.message
    } else {
      aiConfig.configured = false
      aiConfig.message = data.message
    }
  } catch (error) {
    aiConfig.configured = false
    const status = error?.response?.status
    const detail = error?.response?.data?.detail || error?.response?.data?.message || error?.message || ''
    if (status === 404) {
      aiConfig.message = '后端接口未找到，请重启 Django 服务（Ctrl+C 后重新 runserver）'
    } else if (status === 401 || status === 403) {
      aiConfig.message = '未登录或权限不足，请重新登录'
    } else if (detail) {
      aiConfig.message = `检测失败(${status || '未知'}): ${detail}`
    } else {
      aiConfig.message = '无法检测 AI 配置状态，请检查网络或后端服务'
    }
    console.error('checkAIConfig error:', error)
  }
}

const confirmSaveCase = async () => {
  if (!saveFormRef.value) return

  await saveFormRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true
      try {
        await createAICase({
          name: saveForm.name,
          description: saveForm.description,
          task_description: taskForm.description
        })

        ElMessage.success(t('uiAutomation.ai.messages.saveSuccess'))
        showSaveDialog.value = false
      } catch (error) {
        console.error('保存失败:', error)
        ElMessage.error(t('uiAutomation.ai.messages.saveFailed'))
      } finally {
        saving.value = false
      }
    }
  })
}

onMounted(() => {
  const testCasesContent = localStorage.getItem('ai_test_cases_content')
  const fromAssistant = router.currentRoute.value.query.fromAssistant
  
  if (testCasesContent && fromAssistant === 'true') {
    taskForm.description = testCasesContent
    localStorage.removeItem('ai_test_cases_content')
    ElMessage.success('已从智能助手导入测试用例')
  }
})

onUnmounted(() => {
  stopPolling()
})

// keep-alive: 离开页面时暂停轮询，返回时恢复
onDeactivated(() => {
  stopPolling()
})
onActivated(() => {
  // 如果有正在运行的任务，恢复轮询
  if (currentExecutionId.value && running.value) {
    pollLogs()
  }
})

checkConfig()
</script>

<style lang="scss" scoped>
/* ============================================================
   AI 测试页面 - 现代化企业级设计
   ============================================================ */
.page-container {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  .page-title {
    font-size: 22px;
    font-weight: 700;
    margin: 0;
    color: var(--color-text);
  }
}

.card-container {
  background-color: var(--color-bg-card);
  border-radius: var(--radius-xl);
  padding: 24px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
  min-height: calc(100vh - 160px);
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 14px;
  padding-left: 12px;
  border-left: 3px solid var(--color-primary);
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: 8px;

  &::before {
    content: '';
    width: 4px;
    height: 16px;
    background: var(--color-primary);
    border-radius: 2px;
  }
}

.task-list-container {
  background-color: var(--color-bg-surface);
  border-radius: var(--radius-lg);
  padding: 16px;
  margin-bottom: 20px;
  height: calc(100vh - 240px);
  overflow-y: auto;
  border: 1px solid var(--border-color-light);

  .task-item {
    display: flex;
    align-items: flex-start;
    padding: 12px;
    border-bottom: 1px solid var(--border-color-light);
    transition: all var(--transition-fast);
    border-radius: var(--radius-md);
    margin-bottom: 8px;
    background: var(--color-bg-card);

    &:last-child {
      border-bottom: none;
      margin-bottom: 0;
    }

    &:hover {
      box-shadow: var(--shadow-sm);
    }

    &.completed {
      background-color: var(--color-success-bg);
      border-color: var(--color-success-border);

      .task-desc {
        color: var(--color-success);
        text-decoration: line-through;
      }
    }

    &.in_progress {
      background-color: var(--color-primary-bg);
      border-color: var(--color-primary-border);

      .task-desc {
        color: var(--color-primary-dark);
        font-weight: 600;
      }
    }

    .task-status-icon {
      margin-right: 12px;
      margin-top: 2px;
      font-size: 18px;
      flex-shrink: 0;
    }

    .task-content {
      flex: 1;
      line-height: 1.5;

      .task-id {
        font-weight: 700;
        margin-right: 6px;
        color: var(--color-text-secondary);
      }

      .task-desc {
        color: var(--color-text);
      }
    }
  }
}

.empty-tasks {
  color: var(--color-text-muted);
  text-align: center;
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;

  &::before {
    content: '📋';
    font-size: 48px;
    opacity: 0.5;
  }
}

.analyzing-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-primary);
  gap: 12px;

  .el-icon {
    font-size: 28px;
  }

  span {
    font-size: 14px;
    font-weight: 500;
  }
}

.log-container {
  background-color: #1a1a2e;
  border-radius: var(--radius-lg);
  height: 300px;
  overflow-y: auto;
  padding: 16px;
  color: #e0e0e0;
  font-family: var(--font-mono);
  font-size: 13px;
  border: 1px solid rgba(255, 255, 255, 0.1);

  .empty-logs {
    color: #6b7280;
    text-align: center;
    margin-top: 120px;
    font-family: var(--font-sans);
  }

  .log-content {
    margin: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    line-height: 1.6;
  }
}

.test-case-section {
  margin-bottom: 20px;

  .test-case-table-wrapper {
    margin-top: 12px;
    border-radius: var(--radius-lg);
    overflow: hidden;
    border: 1px solid var(--border-color-light);
  }
}

.form-tip {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 6px;
  line-height: 1.5;
}

.headers-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.evidence-section {
  margin-bottom: 20px;
}

.recording-card {
  margin-bottom: 14px;
  border-radius: var(--radius-lg) !important;
  border: 1px solid var(--border-color-light) !important;
  overflow: hidden;
}

.evidence-heading {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;

  &::before {
    content: '';
    width: 3px;
    height: 14px;
    background: var(--color-primary);
    border-radius: 2px;
  }
}

.recording-preview {
  width: 100%;
  max-height: 280px;
  object-fit: contain;
  background: #0f0f1a;
  border-radius: var(--radius-md);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.evidence-link {
  margin-top: 10px;
}

.screenshot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 14px;
  margin-top: 14px;
}

.screenshot-card {
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-bg-card);
  transition: all var(--transition-fast);

  &:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
  }
}

.screenshot-image {
  width: 100%;
  aspect-ratio: 16 / 10;
  object-fit: cover;
  display: block;
  background: #0f0f1a;
}

.screenshot-meta {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text);

  small {
    color: var(--color-text-muted);
    font-size: 11px;
  }
}

/* ============================================================
   响应式布局
   ============================================================ */
@media (max-width: 768px) {
  .card-container {
    padding: 16px;
  }

  .screenshot-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .log-container {
    height: 200px;
  }
}
</style>
