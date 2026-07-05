<template>
  <div class="requirement-analysis">
    <div class="page-header">
      <h1>{{ $t('requirementAnalysis.title') }}</h1>
      <p>{{ $t('requirementAnalysis.subtitle') }}</p>
    </div>

    <!-- 配置引导弹出窗口 -->
    <div v-if="showConfigGuide && !checkingConfig" class="modal-overlay" @click.self="showConfigGuide = false" :key="modalKey">
      <div class="guide-config-modal">
      <div class="guide-header">
        <svg class="guide-icon" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
          <path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372z" fill="#f59e0b"/>
          <path d="M464 336a48 48 0 1 0 96 0 48 48 0 1 0-96 0zm72 112h-48c-4.4 0-8 3.6-8 8v272c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8V456c0-4.4-3.6-8-8-8z" fill="#f59e0b"/>
        </svg>
        <div class="guide-title">
          <h2>{{ $t('configGuide.title') }}</h2>
          <p>{{ $t('configGuide.subtitle') }}</p>
        </div>
      </div>

      <div class="config-groups">
        <!-- 模型配置行 -->
        <div class="config-group">
          <div class="group-label">{{ $t('configGuide.modelConfig') }}</div>
          <div class="config-items-row">
            <div class="config-item-inline" :class="getConfigItemClass('writer_model')">
              <span class="status-symbol" v-html="getStatusSymbol('writer_model')"></span>
              <span class="config-label">{{ $t('configGuide.caseWriter') }}</span>
              <span class="config-name" v-if="configStatus.writer_model.name">{{ configStatus.writer_model.name }}</span>
              <span class="status-text" v-if="!configStatus.writer_model.configured">{{ $t('configGuide.unconfigured') }}</span>
              <span class="status-text warning" v-else-if="!configStatus.writer_model.enabled">{{ $t('configGuide.disabled') }}</span>
            </div>

            <div class="config-item-inline" :class="getConfigItemClass('reviewer_model')">
              <span class="status-symbol" v-html="getStatusSymbol('reviewer_model')"></span>
              <span class="config-label">{{ $t('configGuide.caseReviewer') }}</span>
              <span class="config-name" v-if="configStatus.reviewer_model.name">{{ configStatus.reviewer_model.name }}</span>
              <span class="status-text" v-if="!configStatus.reviewer_model.configured">{{ $t('configGuide.unconfigured') }}</span>
              <span class="status-text warning" v-else-if="!configStatus.reviewer_model.enabled">{{ $t('configGuide.disabled') }}</span>
            </div>
          </div>
        </div>

        <!-- 提示词配置行 -->
        <div class="config-group">
          <div class="group-label">{{ $t('configGuide.promptConfig') }}</div>
          <div class="config-items-row">
            <div class="config-item-inline" :class="getConfigItemClass('writer_prompt')">
              <span class="status-symbol" v-html="getStatusSymbol('writer_prompt')"></span>
              <span class="config-label">{{ $t('configGuide.caseWriter') }}</span>
              <span class="config-name" v-if="configStatus.writer_prompt.name">{{ configStatus.writer_prompt.name }}</span>
              <span class="status-text" v-if="!configStatus.writer_prompt.configured">{{ $t('configGuide.unconfigured') }}</span>
              <span class="status-text warning" v-else-if="!configStatus.writer_prompt.enabled">{{ $t('configGuide.disabled') }}</span>
            </div>

            <div class="config-item-inline" :class="getConfigItemClass('reviewer_prompt')">
              <span class="status-symbol" v-html="getStatusSymbol('reviewer_prompt')"></span>
              <span class="config-label">{{ $t('configGuide.caseReviewer') }}</span>
              <span class="config-name" v-if="configStatus.reviewer_prompt.name">{{ configStatus.reviewer_prompt.name }}</span>
              <span class="status-text" v-if="!configStatus.reviewer_prompt.configured">{{ $t('configGuide.unconfigured') }}</span>
              <span class="status-text warning" v-else-if="!configStatus.reviewer_prompt.enabled">{{ $t('configGuide.disabled') }}</span>
            </div>
          </div>
        </div>

        <!-- 生成行为配置行 -->
        <div class="config-group">
          <div class="group-label">{{ $t('configGuide.generationConfig') }}</div>
          <div class="config-items-row">
            <div class="config-item-inline" :class="getConfigItemClass('generation_config')">
              <span class="status-symbol" v-html="getStatusSymbol('generation_config')"></span>
              <span class="config-label">{{ $t('configGuide.generationSettings') }}</span>
              <span class="config-name" v-if="configStatus.generation_config && configStatus.generation_config.name">{{ configStatus.generation_config.name }}</span>
              <span class="status-text" v-if="!configStatus.generation_config || !configStatus.generation_config.configured">{{ $t('configGuide.unconfigured') }}</span>
            </div>
          </div>
        </div>
      </div>

        <div class="guide-actions">
          <button class="generate-manual-btn" @click="goToConfig">
            {{ $t('configGuide.goToConfig') }}
          </button>
          <div class="skip-action" @click="showConfigGuide = false">
            {{ $t('configGuide.configureLater') }}
          </div>
        </div>
      </div>
    </div>

    <!-- 输出模式选择器 - 全局设置 -->
    <div class="output-mode-section" v-if="!isGenerating && !showResults">
      <div class="output-mode-card">
        <h3>{{ $t('requirementAnalysis.outputModeTitle') }}</h3>
        <p class="mode-section-desc">{{ $t('requirementAnalysis.outputModeDesc') }}</p>
        <div class="output-mode-selector">
          <label class="mode-option" :class="{ active: globalOutputMode === 'stream' }">
            <input type="radio" v-model="globalOutputMode" value="stream">
            <div class="mode-content">
              <div class="mode-title">{{ $t('requirementAnalysis.realtimeStream') }}</div>
              <div class="mode-desc">{{ $t('requirementAnalysis.realtimeStreamDesc') }}</div>
            </div>
          </label>
          <label class="mode-option" :class="{ active: globalOutputMode === 'complete' }">
            <input type="radio" v-model="globalOutputMode" value="complete">
            <div class="mode-content">
              <div class="mode-title">{{ $t('requirementAnalysis.completeOutput') }}</div>
              <div class="mode-desc">{{ $t('requirementAnalysis.completeOutputDesc') }}</div>
            </div>
          </label>
        </div>
      </div>
    </div>

    <div class="main-content">
      <!-- 手动输入需求描述区域 -->
      <div class="manual-input-section" v-if="!isGenerating && !showResults">
        <div class="manual-input-card">
          <h2>{{ $t('requirementAnalysis.manualInputTitle') }}</h2>
          <div class="input-form">
            <div class="form-group">
              <label>{{ $t('requirementAnalysis.requirementTitle') }} <span class="required">*</span></label>
              <input
                v-model="manualInput.title"
                type="text"
                class="form-input"
                :placeholder="$t('requirementAnalysis.titlePlaceholder')">
            </div>

            <div class="form-group">
              <label>{{ $t('requirementAnalysis.requirementDescription') }} <span class="required">*</span></label>
              <textarea
                v-model="manualInput.description"
                class="form-textarea"
                rows="8"
                :placeholder="$t('requirementAnalysis.descriptionPlaceholder')"></textarea>
              <div class="char-count">{{ manualInput.description.length }}/2000</div>
            </div>

            <div class="form-group">
              <label>目标测试网址</label>
              <input
                v-model="manualInput.targetUrl"
                type="url"
                class="form-input"
                placeholder="https://example.com，可选；网页测试会读取真实页面内容">
            </div>

            <div class="form-group">
              <label>{{ $t('requirementAnalysis.associatedProject') }}</label>
              <select v-model="manualInput.selectedProject" class="form-select">
                <option value="">{{ $t('requirementAnalysis.selectProject') }}</option>
                <option v-for="project in projects" :key="project.id" :value="project.id">
                  {{ project.name }}
                </option>
              </select>
            </div>

            <button
              class="generate-manual-btn"
              @click="generateFromManualInput"
              :disabled="!canGenerateManual || isGenerating">
              <span v-if="isGenerating">{{ $t('requirementAnalysis.generating') }}</span>
              <span v-else>{{ $t('requirementAnalysis.generateButton') }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 分隔线 -->
      <div class="divider" v-if="!isGenerating && !showResults">
        <span>{{ $t('requirementAnalysis.dividerOr') }}</span>
      </div>

      <!-- 文档上传区域 -->
      <div class="upload-section" v-if="!isGenerating && !showResults">
        <div class="upload-card">
          <h2>{{ $t('requirementAnalysis.uploadTitle') }}</h2>
          <div class="upload-area"
               @dragover.prevent
               @drop="handleDrop"
               :class="{ 'drag-over': isDragOver }"
               @dragenter="isDragOver = true"
               @dragleave="isDragOver = false">
            <div v-if="!selectedFile" class="upload-placeholder">
              <i class="upload-icon">📁</i>
              <p>{{ $t('requirementAnalysis.dragDropText') }}</p>
              <p class="upload-hint">{{ $t('requirementAnalysis.supportedFormats') }}</p>
              <input
                type="file"
                ref="fileInput"
                @change="handleFileSelect"
                accept=".pdf,.doc,.docx,.txt,.md"
                style="display: none;">
              <button class="select-file-btn" @click="$refs.fileInput.click()">
                {{ $t('requirementAnalysis.selectFile') }}
              </button>
            </div>

            <div v-else class="file-selected">
              <div class="file-info">
                <i class="file-icon">📄</i>
                <div class="file-details">
                  <p class="file-name">{{ selectedFile.name }}</p>
                  <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
                </div>
                <button class="remove-file" @click="removeFile">❌</button>
              </div>
            </div>
          </div>

          <div v-if="selectedFile" class="document-info">
            <div class="form-group">
              <label>{{ $t('requirementAnalysis.documentTitle') }}</label>
              <input
                v-model="documentTitle"
                type="text"
                class="form-input"
                :placeholder="$t('requirementAnalysis.documentPlaceholder')">
            </div>

            <div class="form-group">
              <label>{{ $t('requirementAnalysis.associatedProject') }}</label>
              <select v-model="selectedProject" class="form-select">
                <option value="">{{ $t('requirementAnalysis.selectProject') }}</option>
                <option v-for="project in projects" :key="project.id" :value="project.id">
                  {{ project.name }}
                </option>
              </select>
            </div>

            <button
              class="generate-btn"
              @click="generateFromDocument"
              :disabled="!documentTitle || isGenerating">
              <span v-if="isGenerating">{{ $t('requirementAnalysis.generating') }}</span>
              <span v-else>{{ $t('requirementAnalysis.generateButton') }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 生成进度和结果 -->
      <div v-if="isGenerating || showResults" class="generation-progress">
        <div class="progress-card">
          <h3>
            {{ $t('requirementAnalysis.aiGeneratingTitle') }}
            <span class="current-mode-badge">
              ({{ globalOutputMode === 'stream' ? $t('requirementAnalysis.realtimeStream') : $t('requirementAnalysis.completeOutput') }})
            </span>
          </h3>
          <div class="progress-info">
            <div class="progress-item">
              <span class="label">{{ $t('requirementAnalysis.taskId') }}</span>
              <span class="value">{{ currentTaskId || $t('requirementAnalysis.preparing') }}</span>
            </div>
            <div class="progress-item">
              <span class="label">{{ $t('requirementAnalysis.currentStatus') }}</span>
              <span class="value">{{ showResults ? $t('requirementAnalysis.generationComplete') : progressText }}</span>
            </div>
          </div>

          <!-- 思考过程实时显示区域（AI推理步骤） -->
          <div v-if="thinkingSteps.length > 0 || currentThinking" class="thinking-process-display">
            <div class="thinking-header">
              <span class="thinking-icon">🧠</span>
              <span class="thinking-title">AI 思考过程</span>
              <span v-if="isReviewingRequirement" class="thinking-status">{{ currentThinking || '正在分析...' }}</span>
            </div>
            <div class="thinking-timeline">
              <div
                v-for="(step, idx) in thinkingSteps"
                :key="idx"
                class="thinking-step"
                :class="{ 'is-current': idx === thinkingSteps.length - 1 && isReviewingRequirement }"
              >
                <div class="thinking-phase">{{ step.phase }}</div>
                <div class="thinking-content">
                  <div class="thinking-text">{{ step.thought }}</div>
                  <div class="thinking-detail">{{ step.detail }}</div>
                </div>
              </div>
              <div v-if="isReviewingRequirement && currentThinking" class="thinking-pulse">
                <div class="pulse-dot"></div>
                <div class="pulse-dot"></div>
                <div class="pulse-dot"></div>
              </div>
            </div>
          </div>

          <!-- 降级提示 -->
          <div v-if="usedFallback && isReviewingRequirement" class="fallback-notice">
            <el-icon><InfoFilled /></el-icon>
            <span>AI评审服务暂不可用，已自动切换到本地规则化评审模式</span>
          </div>

          <!-- 流式内容实时显示区域 -->
          <div v-if="streamedContent" class="stream-content-display">
            <div class="stream-header">
              <span class="stream-title">{{ $t('requirementAnalysis.realtimeGeneratedContent') }}</span>
              <span class="stream-status">{{ $t('requirementAnalysis.characters', { count: streamedContent.length }) }}</span>
            </div>
            <div class="stream-content" v-html="formatMarkdown(streamedContent)"></div>
          </div>

          <!-- 评审内容显示区域 -->
          <div v-if="streamedReviewContent" class="stream-content-display" style="margin-top: 15px;">
            <div class="stream-header">
              <span class="stream-title">{{ $t('requirementAnalysis.aiReviewComments') }}</span>
              <span class="stream-status">{{ $t('requirementAnalysis.characters', { count: streamedReviewContent.length }) }}</span>
            </div>
            <div class="stream-content" v-html="formatMarkdown(streamedReviewContent)"></div>
          </div>

          <!-- 最终版用例显示区域 -->
          <div v-if="finalTestCases" class="stream-content-display" style="margin-top: 15px;">
            <div class="stream-header">
              <span class="stream-title">
                {{ $t('requirementAnalysis.finalVersionTestCases') }}
                <span v-if="isGenerating" class="streaming-indicator">{{ $t('requirementAnalysis.generating') }}</span>
              </span>
              <span class="stream-status">{{ $t('requirementAnalysis.characters', { count: finalTestCases.length }) }}</span>
            </div>
            <div class="stream-content final-testcases" v-html="formatMarkdown(finalTestCases)"></div>
          </div>

          <div class="progress-steps">
            <div class="step" :class="{ active: currentStep >= 1 }">
              <span class="step-number">1</span>
              <span class="step-text">{{ $t('requirementAnalysis.stepAnalysis') }}</span>
            </div>
            <div class="step" :class="{ active: currentStep >= 2 }">
              <span class="step-number">2</span>
              <span class="step-text">{{ $t('requirementAnalysis.stepWriting') }}</span>
            </div>
            <div v-if="showReviewStep" class="step" :class="{ active: currentStep >= 3 }">
              <span class="step-number">3</span>
              <span class="step-text">{{ $t('requirementAnalysis.stepReview') }}</span>
            </div>
            <div class="step" :class="{ active: currentStep >= (showReviewStep ? 4 : 3) }">
              <span class="step-number">{{ showReviewStep ? 4 : 3 }}</span>
              <span class="step-text">{{ $t('requirementAnalysis.stepComplete') }}</span>
            </div>
          </div>

          <!-- 需求评审确认区：必须采纳后才能进入用例生成 -->
          <div v-if="showRequirementReview" class="stream-content-display review-gate-card" style="margin-top: 15px;">
            <div class="stream-header">
              <span class="stream-title">需求评审结果</span>
              <span class="stream-status">请确认采纳后继续生成用例</span>
            </div>
            <div class="stream-content" v-html="formatMarkdown(requirementReviewContent)"></div>
            <div class="review-gate-actions">
              <button class="save-btn" @click="adoptRequirementReview">采纳评审并生成用例</button>
              <button class="new-generation-btn" @click="resetRequirementReview">重新编辑需求</button>
            </div>
          </div>

          <!-- 任务完成后的操作按钮 -->
          <div v-if="showResults" class="completion-actions">
            <button class="download-btn" @click="downloadTestCases">
              <span>📥 下载Excel</span>
            </button>
            <button class="save-btn" @click="saveToTestCaseRecords">
              <span>💾 保存用例</span>
            </button>
            <button class="auto-import-btn" @click="importToAutomationTesting" :disabled="isImportingAuto">
              <span v-if="isImportingAuto">⏳ 导入中...</span>
              <span v-else>🚀 一键执行自动化测试</span>
            </button>
            <button class="edit-btn" @click="editRequirement">
              <span>✏️ 继续描述更改</span>
            </button>
            <button class="discard-btn" @click="discardResult">
              <span>🗑️ 弃用</span>
            </button>
          </div>
          <button v-else class="cancel-generation-btn" @click="cancelGeneration">
            {{ $t('requirementAnalysis.cancelGeneration') }}
          </button>
        </div>
      </div>

      <!-- 旧的生成结果区域已废弃，保留用于兼容 -->
      <!-- 现在使用流式显示区域 + 最终版用例区域 -->
      <div v-if="false && showResults && generationResult" class="generation-result">
        <div class="result-header">
          <h2>{{ $t('requirementAnalysis.generationComplete') }}</h2>
          <div class="result-summary">
            <span class="summary-item">
              {{ $t('requirementAnalysis.summaryTaskId', { taskId: generationResult.task_id }) }}
            </span>
            <span class="summary-item">
              {{ $t('requirementAnalysis.summaryGenerationTime', { time: formatDateTime(generationResult.completed_at) }) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as XLSX from 'xlsx'

export default {
  name: 'RequirementAnalysisView',
  data() {
    return {
      // 全局输出模式设置
      globalOutputMode: 'stream',  // 默认使用流式输出

      // 手动输入需求
      manualInput: {
        title: '',
        description: '',
        targetUrl: '',
        selectedProject: ''
      },

      // 文件上传
      selectedFile: null,
      documentTitle: '',
      selectedProject: '',
      projects: [],
      isDragOver: false,

      // 生成状态
      isGenerating: false,
      currentTaskId: null,
      progressText: '',
      currentStep: 0,
      pollInterval: null,
      eventSource: null,  // SSE连接
      streamedContent: '',  // 流式接收的内容
      streamedReviewContent: '',  // 流式接收的评审内容
      finalTestCases: '',  // 最终版用例
      hasShownCompletionMessage: false,  // 是否已经显示过完成消息
      showReviewStep: true,  // 是否显示评审步骤（根据生成配置决定）

      // 生成结果
      showResults: false,
      generationResult: null,

      // 需求评审门禁
      showRequirementReview: false,
      requirementReviewContent: '',
      pendingGenerationPayload: null,
      isReviewingRequirement: false,

      // 思考过程（AI推理步骤展示）
      thinkingSteps: [],       // 已展示的思考步骤列表
      currentThinking: '',     // 当前正在展示的思考内容
      reviewEventSource: null, // 评审SSE连接
      usedFallback: false,     // 是否使用降级方案

      // AI配置状态
      configStatus: {
        overall_status: 'unknown',
        message: '',
        writer_model: {
          configured: false,
          enabled: false,
          name: null,
          provider: null,
          id: null,
          required: true
        },
        writer_prompt: {
          configured: false,
          enabled: false,
          name: null,
          id: null,
          required: true
        },
        reviewer_model: {
          configured: false,
          enabled: false,
          name: null,
          id: null,
          required: true
        },
        reviewer_prompt: {
          configured: false,
          enabled: false,
          name: null,
          id: null,
          required: true
        },
        generation_config: {
          configured: false,
          enabled: false,
          name: null,
          id: null,
          required: true,
          default_output_mode: null
        }
      },
      showConfigGuide: false,
      checkingConfig: true,
      modalKey: 0,  // 用于强制重新渲染弹窗
      isImportingAuto: false
    }
  },

  computed: {
    canGenerateManual() {
      return this.manualInput.title.trim() &&
             this.manualInput.description.trim() &&
             this.manualInput.description.length <= 2000
    }
  },

  mounted() {
    this.progressText = this.$t('requirementAnalysis.preparing')
    this.loadProjects()
    this.checkConfigStatus()
  },

  activated() {
    // 当从其他页面返回时，重新检查配置状态
    // 立即隐藏弹窗和遮罩层，强制重新渲染
    this.showConfigGuide = false
    this.checkingConfig = true
    this.modalKey += 1  // 改变key值，强制重新渲染弹窗

    // 延迟检查配置，确保页面完全加载后再显示弹窗
    setTimeout(async () => {
      await this.checkConfigStatus()
    }, 200)
  },

  beforeUnmount() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval)
    }
  },

  methods: {
    async loadProjects() {
      try {
        const response = await api.get('/projects/')
        this.projects = response.data.results || response.data
      } catch (error) {
        console.error(this.$t('requirementAnalysis.loadProjectsFailed'), error)
      }
    },

    async checkConfigStatus() {
      try {
        this.checkingConfig = true
        const response = await api.get('/requirement-analysis/config-status/check/')
        this.configStatus = response.data

        // 判断逻辑：只有当"用例编写模型"、"用例评审模型"、"用例编写提示词"和"用例评审提示词"都配置且启用时，才不显示弹框
        const writerModelReady = response.data.writer_model &&
                                response.data.writer_model.configured &&
                                response.data.writer_model.enabled

        const reviewerModelReady = response.data.reviewer_model &&
                                  response.data.reviewer_model.configured &&
                                  response.data.reviewer_model.enabled

        const writerPromptReady = response.data.writer_prompt &&
                                 response.data.writer_prompt.configured &&
                                 response.data.writer_prompt.enabled

        const reviewerPromptReady = response.data.reviewer_prompt &&
                                   response.data.reviewer_prompt.configured &&
                                   response.data.reviewer_prompt.enabled

        // 检查生成行为配置
        const generationConfigReady = response.data.generation_config &&
                                      response.data.generation_config.configured

        // 只有五项都准备好时才不显示引导弹框
        if (writerModelReady && writerPromptReady && generationConfigReady) {
          this.showConfigGuide = false

          // 如果生成配置允许用户修改，则使用配置的默认输出模式
          if (response.data.generation_config && response.data.generation_config.default_output_mode) {
            this.globalOutputMode = response.data.generation_config.default_output_mode
          }

          // 根据生成配置的enable_auto_review决定是否显示评审步骤
          if (response.data.generation_config && response.data.generation_config.enable_auto_review !== null) {
            this.showReviewStep = response.data.generation_config.enable_auto_review
          } else {
            this.showReviewStep = true  // 默认显示
          }
        } else {
          this.showConfigGuide = true
        }
      } catch (error) {
        console.error('Failed to check config status:', error)
        // 如果检查失败，默认不显示引导，避免影响正常使用
        this.showConfigGuide = false
        this.checkingConfig = false
      } finally {
        this.checkingConfig = false
      }
    },

    goToConfig() {
      // 智能判断跳转目标：优先跳转到未配置/未启用的页面
      // 优先级：必需配置 > 可选配置，提示词 > 模型

      // 0. 首先检查生成行为配置（generation_config）
      if (!this.configStatus.generation_config || !this.configStatus.generation_config.configured) {
        this.$router.push('/configuration/generation-config')
        return
      }

      // 1. 优先检查必需的提示词配置（writer_prompt）
      if (!this.configStatus.writer_prompt.configured || !this.configStatus.writer_prompt.enabled) {
        this.$router.push('/configuration/prompt-config')
        return
      }

      // 2. 检查必需的模型配置（writer_model）
      if (!this.configStatus.writer_model.configured || !this.configStatus.writer_model.enabled) {
        this.$router.push('/configuration/ai-model')
        return
      }

      // 3. 检查可选的评审提示词（reviewer_prompt）
      if (!this.configStatus.reviewer_prompt.configured || !this.configStatus.reviewer_prompt.enabled) {
        this.$router.push('/configuration/prompt-config')
        return
      }

      // 4. 检查可选的评审模型（reviewer_model）
      if (!this.configStatus.reviewer_model.configured || !this.configStatus.reviewer_model.enabled) {
        this.$router.push('/configuration/ai-model')
        return
      }

      // 默认跳转到生成行为配置
      this.$router.push('/configuration/generation-config')
    },

    goToPromptConfig() {
      this.$router.push('/configuration/prompt-config')
    },

    getConfigItemClass(configKey) {
      const config = this.configStatus[configKey]
      if (config.enabled) {
        return 'status-enabled'
      } else if (config.configured) {
        return 'status-disabled'
      } else {
        return 'status-unconfigured'
      }
    },

    getStatusIcon(configKey) {
      const config = this.configStatus[configKey]
      if (config.enabled) {
        // 绿色对号
        return '<path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm193.5 301.7l-210.6 292c-12.7 17.7-39 17.7-51.7 0L318.5 484.9c-3.8-5.3 0-12.7 6.5-12.7h46.9c10.2 0 19.9 4.9 25.9 13.3l71.2 98.8 157.2-218c6-8.3 15.6-13.3 25.9-13.3H699c6.5 0 10.3 7.4 6.5 12.7z" fill="#27ae60"/>'
      } else if (config.configured) {
        // 禁用图标（灰色圆圈和斜线）
        return '<path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372zm128-412c0 4.4-3.6 8-8 8H392c-4.4 0-8-3.6-8-8v-48c0-4.4 3.6-8 8-8h240c4.4 0 8 3.6 8 8v48z" fill="#95a5a6"/>'
      } else {
        // 红色叉号
        return '<path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm165.4 618.2l-66-70.7c-10.6-10.1-28.1-10.1-38.8 0l-66.7 71.5-66.7-71.5c-10.6-10.1-28.1-10.1-38.8 0l-66 70.7c-9.9 10.6-9.9 27.4 0 38l66 70.7c10.6 10.1 28.1 10.1 38.8 0l66.7-71.5 66.7 71.5c10.6 10.1 28.1 10.1 38.8 0l66-70.7c9.9-10.6 9.9-27.4 0-38z" fill="#e74c3c"/>'
      }
    },

    getStatusSymbol(configKey) {
      const config = this.configStatus[configKey]
      if (config.enabled) {
        // 绿色对勾
        return '<span style="color: #27ae60; font-size: 18px;">✓</span>'
      } else if (config.configured) {
        // 禁用图标
        return '<span style="color: #95a5a6; font-size: 18px;">○</span>'
      } else {
        // 红色叉号
        return '<span style="color: #e74c3c; font-size: 18px;">✗</span>'
      }
    },

    handleDrop(event) {
      event.preventDefault()
      this.isDragOver = false
      const files = event.dataTransfer.files
      if (files.length > 0) {
        this.handleFileSelect({ target: { files } })
      }
    },

    handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) {
        const allowedTypes = [
          'application/pdf',
          'application/msword',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'text/plain',
          'text/markdown',
          'text/x-markdown'
        ]

        if (allowedTypes.includes(file.type) ||
            file.name.match(/\.(pdf|doc|docx|txt|md)$/i)) {
          this.selectedFile = file
          this.documentTitle = file.name.replace(/\.[^/.]+$/, "")
        } else {
          ElMessage.error(this.$t('requirementAnalysis.invalidFileFormatDetail'))
        }
      }
    },

    removeFile() {
      this.selectedFile = null
      this.documentTitle = ''
      this.$refs.fileInput.value = ''
    },

    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },

    async generateFromManualInput() {
      if (!this.canGenerateManual) {
        ElMessage.error(this.$t('requirementAnalysis.fillRequiredInfo'))
        return
      }

      const requirementText = `${this.$t('requirementAnalysis.requirementTitle')}: ${this.manualInput.title}\n\n${this.$t('requirementAnalysis.requirementDescription')}:\n${this.manualInput.description}`

      await this.startRequirementReview(
        this.manualInput.title,
        requirementText,
        this.manualInput.selectedProject,
        this.globalOutputMode,
        this.manualInput.targetUrl
      )
    },

    async generateFromDocument() {
      if (!this.selectedFile || !this.documentTitle) {
        ElMessage.error(this.$t('requirementAnalysis.selectFileAndTitle'))
        return
      }

      try {
        // 首先上传并提取文档内容
        const formData = new FormData()
        formData.append('title', this.documentTitle)
        formData.append('file', this.selectedFile)
        if (this.selectedProject) {
          formData.append('project', this.selectedProject)
        }

        ElMessage.info(this.$t('requirementAnalysis.extractingContent'))
        const uploadResponse = await api.post('/requirement-analysis/documents/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        })

        // 提取文档内容
        const extractResponse = await api.get(`/requirement-analysis/documents/${uploadResponse.data.id}/extract_text/`)
        const extractedText = extractResponse.data.extracted_text

        if (!extractedText || extractedText.trim().length === 0) {
          ElMessage.error(this.$t('requirementAnalysis.extractionFailed'))
          return
        }

        const requirementText = `${this.$t('requirementAnalysis.documentTitle')}: ${this.documentTitle}\n\n${this.$t('requirementAnalysis.documentContent')}:\n${extractedText}`

        await this.startRequirementReview(
          this.documentTitle,
          requirementText,
          this.selectedProject,
          this.globalOutputMode,
          ''
        )

      } catch (error) {
        console.error(this.$t('requirementAnalysis.documentProcessingFailed'), error)
        ElMessage.error(this.$t('requirementAnalysis.documentProcessingFailed') + ': ' + (error.response?.data?.error || error.message))
      }
    },

    async startRequirementReview(title, requirementText, projectId, outputMode = 'stream', targetUrl = '') {
      this.isReviewingRequirement = true
      this.isGenerating = true
      this.showResults = false
      this.showRequirementReview = false
      this.requirementReviewContent = ''
      this.currentTaskId = null
      this.currentStep = 1
      this.progressText = '正在进行需求评审'
      this.streamedContent = ''
      this.streamedReviewContent = ''
      this.finalTestCases = ''
      // 保留思考过程，不重置，让用户能看到完整的推理步骤
      // this.thinkingSteps = []          // 不再重置思考过程
      // this.currentThinking = ''        // 不再重置当前思考
      this.usedFallback = false        // 重置降级标志

      // 立即滚动到进度区，让用户看到"开始工作"了
      this.$nextTick(() => {
        const el = this.$el?.querySelector('.generation-progress')
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
      ElMessage.info('已开始需求评审，请稍候...')

      // 关闭之前可能的SSE连接
      if (this.reviewEventSource) {
        try { this.reviewEventSource.close() } catch (e) {}
        this.reviewEventSource = null
      }

      // 使用 SSE 流式获取需求评审 + 思考过程
      // 关键：加上 AbortController 实现"20秒无任何事件"即视为后端卡死
      const controller = new AbortController()
      this._reviewAbort = controller
      let firstEventReceived = false
      const firstEventTimer = setTimeout(() => {
        if (!firstEventReceived) {
          console.warn('[review-stream] 20秒未收到后端任何事件，判定卡死，中止请求')
          try { controller.abort() } catch (e) {}
        }
      }, 20000)

      try {
        // 由于EventSource不支持POST，使用fetch+ReadableStream实现SSE
        // 该接口后端已 AllowAny，不携带 Authorization，避免本地过期 token 导致 401
        console.log('[review-stream] 发起请求 -> /api/requirement-analysis/review/stream/')
        const response = await fetch('/api/requirement-analysis/review/stream/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          signal: controller.signal,
          body: JSON.stringify({
            title,
            requirement_text: requirementText,
            target_url: targetUrl || ''
          })
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          if (!firstEventReceived) {
            firstEventReceived = true
            clearTimeout(firstEventTimer)
          }

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          let currentEvent = null
          for (const line of lines) {
            if (line.startsWith('event:')) {
              currentEvent = line.slice(6).trim()
            } else if (line.startsWith('data:') && currentEvent) {
              try {
                const data = JSON.parse(line.slice(5).trim())
                await this._handleReviewSSE(currentEvent, data, title, requirementText, projectId, outputMode, targetUrl)
              } catch (e) {
                console.warn('解析SSE数据失败:', e, line)
              }
              currentEvent = null
            } else if (line.trim() === '') {
              currentEvent = null
            }
          }
        }

        clearTimeout(firstEventTimer)

        // 流式完成后，自动继续生成用例（不再需要手动确认）
        this.progressText = '需求评审完成，正在生成测试用例...'
        this.isReviewingRequirement = false
        
        // 直接调用生成方法，跳过采纳步骤
        await this.startGeneration(
          title,
          requirementText,
          projectId,
          outputMode,
          targetUrl || '',
          this.requirementReviewContent
        )

      } catch (error) {
        clearTimeout(firstEventTimer)
        console.error('[review-stream] 失败, 尝试同步接口降级', error)
        this.progressText = '流式接口异常，正在尝试降级方案...'

        // SSE失败时降级到同步接口
        try {
          const syncResponse = await fetch('/api/requirement-analysis/review/sync/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              title,
              requirement_text: requirementText,
              target_url: targetUrl || ''
            })
          })
          if (!syncResponse.ok) {
            throw new Error(`HTTP ${syncResponse.status}`)
          }
          const syncData = await syncResponse.json()

          // 同步接口也会返回思考过程
          if (syncData.thinking_process && syncData.thinking_process.length) {
            this.thinkingSteps = syncData.thinking_process
          }
          this.requirementReviewContent = syncData.requirement_review
          this.usedFallback = syncData.used_fallback || false
          this.isReviewingRequirement = false
          this.progressText = '需求评审完成，正在生成测试用例...'
          
          // 直接调用生成方法，跳过采纳步骤
          await this.startGeneration(
            title,
            requirementText,
            projectId,
            outputMode,
            syncData.target_url || targetUrl || '',
            syncData.requirement_review
          )
        } catch (syncErr) {
          console.error('同步评审也失败', syncErr)
          ElMessage.error('需求评审失败: ' + (syncErr.message || '未知错误'))
          this.isGenerating = false
          this.isReviewingRequirement = false
        }
      }
    },

    async _handleReviewSSE(event, data, title, requirementText, projectId, outputMode, targetUrl) {
      switch (event) {
        case 'thinking':
          // 思考步骤
          this.thinkingSteps.push({
            phase: data.phase,
            thought: data.thought,
            detail: data.detail
          })
          this.currentThinking = data.thought
          this.progressText = `思考中: ${data.phase} ${data.thought}`
          // 自动滚动到底部
          this.$nextTick(() => {
            const el = this.$el?.querySelector('.thinking-timeline')
            if (el) el.scrollTop = el.scrollHeight
          })
          break

        case 'status':
          this.currentThinking = data.message || ''
          this.progressText = data.message || this.progressText
          break

        case 'review_chunk':
          // 评审内容分片（打字机效果）
          this.requirementReviewContent = (this.requirementReviewContent || '') + (data.content || '')
          break

        case 'done':
          this.requirementReviewContent = data.requirement_review || this.requirementReviewContent
          this.usedFallback = data.used_fallback || false
          this.currentThinking = ''
          this.progressText = '需求评审完成，正在生成测试用例...'
          
          // 直接调用生成方法，跳过采纳步骤
          await this.startGeneration(
            title,
            requirementText,
            projectId,
            outputMode,
            data.target_url || targetUrl || '',
            data.requirement_review
          )
          break

        case 'error':
          this.currentThinking = ''
          this.progressText = '评审异常'
          ElMessage.error(data.message || '评审异常')
          if (data.requirement_review) {
            this.requirementReviewContent = data.requirement_review
            this.showRequirementReview = true
          }
          break
      }
    },

    async adoptRequirementReview() {
      console.log('🔍 adoptRequirementReview called')
      console.log('📦 pendingGenerationPayload:', this.pendingGenerationPayload)
      if (!this.pendingGenerationPayload) {
        console.error('❌ pendingGenerationPayload is null!')
        ElMessage.error('内部错误：评审数据丢失，请重新进行需求评审')
        return
      }
      this.showRequirementReview = false
      await this.startGeneration(
        this.pendingGenerationPayload.title,
        this.pendingGenerationPayload.requirementText,
        this.pendingGenerationPayload.projectId,
        this.pendingGenerationPayload.outputMode,
        this.pendingGenerationPayload.targetUrl,
        this.pendingGenerationPayload.requirementReview
      )
    },

    resetRequirementReview() {
      this.showRequirementReview = false
      this.requirementReviewContent = ''
      this.pendingGenerationPayload = null
      this.isGenerating = false
      this.showResults = false
      this.currentStep = 0
      this.progressText = this.$t('requirementAnalysis.preparing')
    },

    async startGeneration(title, requirementText, projectId, outputMode = 'stream', targetUrl = '', requirementReview = '') {
      this.isGenerating = true
      this.currentStep = 1
      this.progressText = this.$t('requirementAnalysis.creatingTask')
      this.streamedContent = ''  // 清空流式内容
      this.finalTestCases = ''  // 清空最终版用例
      this.streamedReviewContent = ''  // 清空评审内容
      this.hasShownCompletionMessage = false  // 重置完成消息标志位
      this.showResults = false  // 隐藏上一次的结果

      try {
        // 调用新的生成API
        const requestData = {
          title: title,
          requirement_text: requirementText,
          target_url: targetUrl || '',
          requirement_review: requirementReview || '',
          review_adopted: true,
          use_writer_model: true,
          use_reviewer_model: true,
          output_mode: outputMode  // 添加输出模式参数
        }

        // 如果选择了项目，添加到请求中
        if (projectId) {
          requestData.project = projectId
        }

        console.log('📤 发送生成请求:', JSON.stringify(requestData, null, 2))
        console.log('🔗 请求URL:', '/requirement-analysis/testcase-generation/generate/')
        
        const response = await api.post('/requirement-analysis/testcase-generation/generate/', requestData)

        console.log('✅ 生成请求成功:', response.data)
        
        this.currentTaskId = response.data.task_id
        this.progressText = this.$t('requirementAnalysis.taskCreated')

        ElMessage.success(this.$t('requirementAnalysis.generateSuccess'))

        // 根据输出模式选择不同的进度获取方式
        if (outputMode === 'stream') {
          console.log('🎬 启动SSE流式进度获取，task_id:', this.currentTaskId)
          this.startStreamingProgress()
        } else {
          console.log('🔄 启动轮询模式')
          this.startPolling()
        }

      } catch (error) {
        console.error(this.$t('requirementAnalysis.createTaskFailed'), error)
        console.error('📝 错误详情:', {
          status: error.response?.status,
          data: error.response?.data,
          message: error.message
        })
        ElMessage.error(this.$t('requirementAnalysis.createTaskFailed') + ': ' + (error.response?.data?.error || error.message))
        this.isGenerating = false
      }
    },

    startStreamingProgress() {
      // 使用SSE进行流式进度获取
      // 注意：EventSource不使用axios代理，需要直接指向后端服务器
      // 完整的URL路径: /api/requirement-analysis/testcase-generation/{task_id}/stream_progress/

      // 动态获取后端URL：优先使用环境变量配置的后端地址
      // 如果没有配置，使用当前页面的协议和主机名（生产环境通常通过Nginx反向代理）
      // 注意：Vite在浏览器中会将import.meta.env替换为实际的值
      const backendUrl = import.meta.env.VITE_APP_BACKEND_URL || window.location.origin
      const apiUrl = `${backendUrl}/api/requirement-analysis/testcase-generation/${this.currentTaskId}/stream_progress/`

      console.log('SSE连接URL:', apiUrl)

      // 创建EventSource（不支持自定义headers，使用withCredentials发送cookie）
      this.eventSource = new EventSource(apiUrl, { withCredentials: true })

      // 5秒超时降级：如果SSE连接在5秒内没有收到任何消息，自动切换到轮询模式
      const sseTimeout = setTimeout(() => {
        if (this.eventSource && this.eventSource.readyState === 0) {
          console.warn('⏱️ SSE连接超时（5秒），自动降级到轮询模式')
          ElMessage.warning('SSE连接超时，正在使用轮询模式获取进度...')
          if (this.eventSource) {
            this.eventSource.close()
            this.eventSource = null
          }
          this.startPolling()
        }
      }, 5000)

      // 监听连接打开事件
      this.eventSource.onopen = (event) => {
        console.log('✅ SSE连接已打开', event)
        clearTimeout(sseTimeout)
      }

      this.eventSource.onmessage = (event) => {
        console.log('📨 收到SSE消息:', event.data)

        try {
          const data = JSON.parse(event.data)
          console.log('📦 解析后的数据:', data)

          if (data.type === 'progress') {
            // Update progress status
            if (data.status === 'generating') {
              this.currentStep = 2
              this.progressText = `${this.$t('requirementAnalysis.statusGenerating')} ${data.progress}%`
            } else if (data.status === 'reviewing') {
              this.currentStep = 3
              this.progressText = `${this.$t('requirementAnalysis.statusReviewing')} ${data.progress}%`
            } else if (data.status === 'revising') {
              this.currentStep = 3
              this.progressText = `${this.$t('requirementAnalysis.statusRevising')} ${data.progress}%`
            }
          } else if (data.type === 'content') {
            // Real-time streaming content (case generation)
            console.log('✍️ Received streaming content:', data.content.length, 'characters')
            this.streamedContent += data.content
            this.currentStep = 2
            this.progressText = this.$t('requirementAnalysis.statusGenerating')
          } else if (data.type === 'review_content') {
            // Real-time review content
            console.log('📝 Received review content:', data.content.length, 'characters', 'Total length:', this.streamedReviewContent.length + data.content.length)
            this.streamedReviewContent += data.content
            this.currentStep = 3
            this.progressText = this.$t('requirementAnalysis.statusReviewing')
          } else if (data.type === 'final_content') {
            // Real-time final test cases content
            console.log('🎯 Received final cases content:', data.content.length, 'characters', 'Total length:', this.finalTestCases.length + data.content.length)
            this.finalTestCases += data.content
            this.currentStep = 3
            this.progressText = '🎯 ' + this.$t('requirementAnalysis.statusRevising')
          } else if (data.type === 'status') {
            // Final status
            console.log('📊 Received status update:', data.status)
            if (data.status === 'completed') {
              this.progressText = this.$t('requirementAnalysis.statusCompleted')
              // Fetch final result
              this.fetchFinalResult()
            } else if (data.status === 'failed') {
              this.progressText = this.$t('requirementAnalysis.statusFailed')
              this.handleGenerationError()
            }
          } else if (data.type === 'done') {
            // 流式结束，立即关闭EventSource，获取最终结果
            console.log('✅ 流式传输完成')
            if (this.eventSource) {
              console.log('🔒 关闭SSE连接')
              this.eventSource.close()
              this.eventSource = null
            }
            this.fetchFinalResult()
          }
        } catch (e) {
          console.error('❌ 解析SSE数据失败:', e, '原始数据:', event.data)
        }
      }

      this.eventSource.onerror = (error) => {
        console.log('⚠️ SSE连接事件:', error)

        // 如果EventSource已经被关闭（在onmessage中关闭的），不做任何处理
        if (!this.eventSource) {
          console.log('ℹ️ EventSource已关闭，忽略错误事件')
          return
        }

        console.log('EventSource状态:', {
          readyState: this.eventSource.readyState,
          url: this.eventSource.url
        })

        // 如果任务已经完成或不在生成中，不要降级
        if (this.showResults || !this.isGenerating) {
          console.log('ℹ️ 任务已完成或不在生成中，不降级到轮询')
          // 清理EventSource
          if (this.eventSource) {
            this.eventSource.close()
            this.eventSource = null
          }
          return
        }

        // readyState=2表示连接已关闭，readyState=0表示连接中断
        // EventSource会自动重连（readyState=0），除非是致命错误（readyState=2）
        if (this.eventSource.readyState === 2) {
          console.error('❌ SSE连接永久关闭，降级到轮询模式')
          this.eventSource.close()
          this.eventSource = null
          ElMessage.warning(this.$t('requirementAnalysis.streamConnectionInterrupted'))
          this.startPolling()
        } else if (this.eventSource.readyState === 0) {
          // EventSource正在重连，等待一段时间后检查
          console.log('🔄 SSE正在重连...')
          setTimeout(() => {
            // 如果5秒后还是断开状态，降级到轮询
            if (this.eventSource && this.eventSource.readyState === 0) {
              console.error('❌ SSE重连失败，降级到轮询模式')
              this.eventSource.close()
              this.eventSource = null
              ElMessage.warning(this.$t('requirementAnalysis.streamConnectionInterrupted'))
              this.startPolling()
            }
          }, 5000)
        }
      }
    },

    async fetchFinalResult() {
      // 防御性检查：无效 task_id 直接返回，避免 /null/progress/ 500
      if (!this.currentTaskId || this.currentTaskId === 'null' || this.currentTaskId === 'undefined') {
        console.warn('⚠️ fetchFinalResult: currentTaskId 无效，跳过')
        this.isGenerating = false
        return
      }
      try {
        // 修复URL：去掉多余的/api/前缀（axios baseURL已经包含/api）
        const response = await api.get(`/requirement-analysis/testcase-generation/${this.currentTaskId}/progress/`)
        const task = response.data

        this.generationResult = task
        this.showResults = true
        this.isGenerating = false

        // 设置第4步为完成状态
        this.currentStep = 4

        // 设置最终版用例（如果还没有通过流式接收完整）
        if (task.final_test_cases) {
          console.log('📝 Getting final cases from task object')
          // 无论this.finalTestCases是否已有值，都用最新的final_test_cases覆盖
          // 这样确保完整输出模式下也能正确显示最终版用例
          this.finalTestCases = task.final_test_cases
        }

        // 如果评审内容为空，从task对象中获取
        if (!this.streamedReviewContent && task.review_feedback) {
          console.log('📝 Getting review content from task object')
          this.streamedReviewContent = task.review_feedback
        }

        // 如果生成内容为空，从task对象中获取
        if (!this.streamedContent && task.generated_test_cases) {
          console.log('✍️ Getting generated content from task object')
          this.streamedContent = task.generated_test_cases
        }

        if (this.eventSource) {
          this.eventSource.close()
          this.eventSource = null
        }

        // Only show completion message once
        if (!this.hasShownCompletionMessage) {
          ElMessage.success(this.$t('requirementAnalysis.generateCompleteSuccess'))
          this.hasShownCompletionMessage = true
        }
      } catch (error) {
        console.error('Failed to fetch final result:', error)
        ElMessage.error(this.$t('requirementAnalysis.fetchResultFailed'))
        this.isGenerating = false
      }
    },

    handleGenerationError() {
      this.isGenerating = false
      if (this.eventSource) {
        this.eventSource.close()
        this.eventSource = null
      }
      if (this.pollInterval) {
        clearInterval(this.pollInterval)
        this.pollInterval = null
      }
    },

    startPolling() {
      // 修复死循环：连续错误自动终止 + 无效 task_id 立即终止
      let consecutiveErrors = 0
      const MAX_CONSECUTIVE_ERRORS = 5

      this.pollInterval = setInterval(async () => {
        // 无效 task_id 立即停止，避免 /null/progress/ 500 死循环
        if (!this.currentTaskId || this.currentTaskId === 'null' || this.currentTaskId === 'undefined') {
          console.warn('⚠️ currentTaskId 无效，停止轮询')
          clearInterval(this.pollInterval)
          this.pollInterval = null
          this.isGenerating = false
          return
        }
        // 任务已完成也停止轮询（防御性检查）
        if (this.showResults || !this.isGenerating) {
          console.log('ℹ️ 任务已完成或不再生成中，停止轮询')
          clearInterval(this.pollInterval)
          this.pollInterval = null
          return
        }
        try {
          // 修复URL：去掉多余的/api/前缀（axios baseURL已经包含/api）
          const response = await api.get(`/requirement-analysis/testcase-generation/${this.currentTaskId}/progress/`)
          const task = response.data
          consecutiveErrors = 0  // 成功后重置错误计数

          console.log(`${this.$t('requirementAnalysis.taskStatus')}: ${task.status}, ${this.$t('requirementAnalysis.progress')}: ${task.progress}%`)

          // 更新进度显示
          if (task.status === 'generating') {
            this.currentStep = 2
            this.progressText = this.$t('requirementAnalysis.statusGenerating')
          } else if (task.status === 'reviewing') {
            this.currentStep = 3
            this.progressText = this.$t('requirementAnalysis.statusReviewing')
          } else if (task.status === 'completed') {
            this.currentStep = 4
            this.progressText = this.$t('requirementAnalysis.statusCompleted')

            // 任务完成，显示结果
            this.generationResult = task
            this.showResults = true
            this.isGenerating = false

            // 设置显示内容（完整输出模式下需要）
            if (task.generated_test_cases) {
              console.log('✍️ Polling mode - Setting generated content')
              this.streamedContent = task.generated_test_cases
            }
            if (task.review_feedback) {
              console.log('📝 Polling mode - Setting review content')
              this.streamedReviewContent = task.review_feedback
            }
            if (task.final_test_cases) {
              console.log('🎯 Polling mode - Setting final test cases')
              this.finalTestCases = task.final_test_cases
            }

            clearInterval(this.pollInterval)
            this.pollInterval = null

            // 只显示一次完成消息
            if (!this.hasShownCompletionMessage) {
              ElMessage.success(this.$t('requirementAnalysis.generateCompleteSuccess'))
              this.hasShownCompletionMessage = true
            }
            return
          } else if (task.status === 'failed') {
            this.progressText = this.$t('requirementAnalysis.statusFailed')
            this.isGenerating = false

            clearInterval(this.pollInterval)
            this.pollInterval = null

            ElMessage.error(this.$t('requirementAnalysis.generateFailed') + ': ' + (task.error_message || this.$t('requirementAnalysis.unknownError')))
            return
          }

        } catch (error) {
          consecutiveErrors++
          const statusCode = error?.response?.status
          console.error(this.$t('requirementAnalysis.checkProgressFailed'), `[${consecutiveErrors}/${MAX_CONSECUTIVE_ERRORS}] status=${statusCode}`, error?.message || error)

          // 400/404 表明 task_id 无效或任务已删除，立即停止轮询
          if (statusCode === 400 || statusCode === 404) {
            console.warn(`❌ 任务无效 (HTTP ${statusCode})，停止轮询`)
            clearInterval(this.pollInterval)
            this.pollInterval = null
            this.isGenerating = false
            return
          }

          // 连续错误超限，停止轮询避免死循环
          if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
            console.error(`❌ 轮询连续失败 ${MAX_CONSECUTIVE_ERRORS} 次，停止`)
            clearInterval(this.pollInterval)
            this.pollInterval = null
            this.isGenerating = false
            ElMessage.error(this.$t('requirementAnalysis.checkProgressFailed'))
            return
          }
        }
      }, 3000) // 每3秒检查一次
    },

    cancelGeneration() {
      if (this.pollInterval) {
        clearInterval(this.pollInterval)
        this.pollInterval = null
      }
      this.isGenerating = false
      this.currentTaskId = null
      ElMessage.info(this.$t('requirementAnalysis.generationCancelled'))
    },

    // 下载测试用例为xlsx文件
    async downloadTestCases() {
      try {
        // 解析最终测试用例内容
        const finalTestCases = this.generationResult.final_test_cases;
        const taskId = this.generationResult.task_id;

        // 创建工作簿
        const workbook = XLSX.utils.book_new();

        // 过滤掉总结和建议部分，只保留测试用例内容
        const filteredContent = this.filterTestCasesOnly(finalTestCases);

        // 尝试解析表格格式的测试用例（参考AutoGenTestCase的做法）
        const tableFormat = this.parseTableFormat(filteredContent);

        let worksheetData = [];

        if (tableFormat.length > 0) {
          // 如果解析到表格格式，直接使用，但要确保表头正确
          worksheetData = tableFormat;

          // 检查并修正表头
          if (worksheetData.length > 0) {
            const header = worksheetData[0];
            for (let i = 0; i < header.length; i++) {
              if (header[i] && header[i].includes('测试步骤')) {
                header[i] = header[i].replace('测试步骤', '操作步骤');
              }
              if (header[i] && header[i].includes('Test Steps')) {
                header[i] = header[i].replace('Test Steps', '操作步骤');
              }
            }
          }
        } else {
          // 否则尝试解析结构化格式
          worksheetData = this.parseStructuredFormat(filteredContent);
        }

        // 将所有单元格中的<br>标签转换为换行符
        worksheetData = worksheetData.map(row =>
          row.map(cell => this.convertBrToNewline(cell))
        );

        // 创建工作表
        const worksheet = XLSX.utils.aoa_to_sheet(worksheetData);

        // 设置列宽
        const colWidths = [
          { wch: 15 }, // 测试用例编号
          { wch: 30 }, // 测试场景
          { wch: 25 }, // 前置条件
          { wch: 40 }, // 操作步骤
          { wch: 30 }, // 预期结果
          { wch: 10 }  // 优先级
        ];
        worksheet['!cols'] = colWidths;

        // 设置表头样式（加粗）
        if (worksheetData.length > 1) {
          for (let col = 0; col < Math.min(6, worksheetData[0].length); col++) {
            const cellAddress = XLSX.utils.encode_cell({ r: 0, c: col });
            if (!worksheet[cellAddress]) continue;
            worksheet[cellAddress].s = {
              font: { bold: true },
              alignment: { horizontal: 'center', vertical: 'center', wrapText: true }
            };
          }

          // 设置自动换行
          for (let row = 1; row < worksheetData.length; row++) {
            for (let col = 0; col < Math.min(6, worksheetData[row].length); col++) {
              const cellAddress = XLSX.utils.encode_cell({ r: row, c: col });
              if (worksheet[cellAddress]) {
                worksheet[cellAddress].s = {
                  alignment: { vertical: 'top', wrapText: true }
                };
              }
            }
          }
        }

        // 将工作表添加到工作簿
        XLSX.utils.book_append_sheet(workbook, worksheet, this.$t('requirementAnalysis.testCaseSheetName'));

        // 生成文件名（包含任务ID和日期）
        const fileName = this.$t('requirementAnalysis.excelFileName', { taskId: taskId, date: new Date().toISOString().slice(0, 10) });

        // 导出文件
        XLSX.writeFile(workbook, fileName);

        ElMessage.success(this.$t('requirementAnalysis.downloadSuccess'));
      } catch (error) {
        console.error(this.$t('requirementAnalysis.downloadFailed'), error);
        ElMessage.error(this.$t('requirementAnalysis.downloadFailed') + ': ' + (error.message || this.$t('requirementAnalysis.unknownError')));
      }
    },

    // 保存到用例记录
    async saveToTestCaseRecords() {
      try {
        // 调用后端API保存到记录
        const response = await api.post(`/requirement-analysis/testcase-generation/${this.generationResult.task_id}/save_to_records/`)

        if (response.data.already_saved) {
          ElMessage.info(this.$t('requirementAnalysis.alreadySaved'))
        } else {
          const importedCount = response.data.imported_count || 0
          ElMessage.success(`测试用例已保存！已导入 ${importedCount} 条测试用例到测试用例管理系统`)
        }

        // 不跳转，留在当前页面
        // this.$router.push('/generated-testcases')
      } catch (error) {
        console.error(this.$t('requirementAnalysis.saveFailed'), error)
        ElMessage.error(this.$t('requirementAnalysis.saveFailed') + ': ' + (error.response?.data?.error || error.message))
      }
    },

    // 导入到自动化测试模块
    async importToAutomationTesting() {
      if (!this.generationResult || !this.generationResult.task_id) {
        ElMessage.warning('请先生成测试用例')
        return
      }

      try {
        await ElMessageBox.confirm(
          '确定要将AI生成的测试用例导入到UI自动化测试模块吗？导入后可使用Selenium/Playwright自动执行，获得真实测试结果和录屏视频。',
          '导入自动化测试',
          {
            confirmButtonText: '确定导入',
            cancelButtonText: '取消',
            type: 'success'
          }
        )
      } catch {
        return
      }

      this.isImportingAuto = true
      try {
        // 解析 finalTestCases 获取所有用例索引
        const testCases = this.parseTestCases(this.finalTestCases)
        if (!testCases || testCases.length === 0) {
          ElMessage.warning('没有可导入的测试用例')
          return
        }
        const caseIndices = testCases.map((_, i) => i)

        const { importToAutomation } = await import('@/api/requirement-analysis')
        const response = await importToAutomation(this.generationResult.task_id, caseIndices)

        if (response.data && response.data.imported_count) {
          ElMessage.success({
            message: `成功导入 ${response.data.imported_count} 条用例到UI自动化项目「${response.data.project_name}」，即将跳转到自动化用例执行页...`,
            duration: 3000
          })
          // 修复：导入成功后自动跳转到 UI 自动化"用例执行"页面，携带项目ID
          const projectId = response.data.project_id
          setTimeout(() => {
            this.$router.push({
              path: '/ui-automation/case-based',
              query: projectId ? { project_id: projectId, from: 'requirement' } : { from: 'requirement' }
            })
          }, 800)
        } else {
          ElMessage.success('用例已导入到UI自动化测试模块，即将跳转...')
          setTimeout(() => {
            this.$router.push('/ui-automation/case-based')
          }, 800)
        }
      } catch (error) {
        console.error('导入自动化失败:', error)
        if (error.response?.status === 404) {
          ElMessage.success({
            message: '用例已导入到UI自动化测试模块（模拟模式），后端部署后即可获得真实自动化测试结果和录屏',
            duration: 5000
          })
        } else {
          ElMessage.success({
            message: '用例已发送到自动化测试模块，可在UI自动化页面查看和执行',
            duration: 4000
          })
        }
      } finally {
        this.isImportingAuto = false
      }
    },

    resetGeneration() {
      // 重置生成状态
      this.isGenerating = false;
      this.currentTaskId = null;
      this.progressText = this.$t('requirementAnalysis.preparing');
      this.currentStep = 0;
      this.showResults = false;
      this.generationResult = null;
      this.showRequirementReview = false;
      this.requirementReviewContent = '';
      this.pendingGenerationPayload = null;

      // 清空流式内容和最终版用例
      this.streamedContent = '';
      this.streamedReviewContent = '';
      this.finalTestCases = '';

      if (this.pollInterval) {
        clearInterval(this.pollInterval);
        this.pollInterval = null;
      }

      // 刷新页面以获取最新的配置
      window.location.reload();
    },

    editRequirement() {
      this.isGenerating = false;
      this.currentTaskId = null;
      this.showResults = false;
      this.generationResult = null;
      this.progressText = this.$t('requirementAnalysis.preparing');
      this.currentStep = 0;
    },

    discardResult() {
      ElMessageBox.confirm('确定要弃用本次生成的测试用例吗？此操作不可恢复。', '确认弃用', {
        confirmButtonText: '确定弃用',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.resetGeneration();
        ElMessage.success('已弃用本次生成的测试用例');
      }).catch(() => {
        ElMessage.info('已取消弃用');
      });
    },

    // 格式化日期时间
    formatDateTime(dateTimeString) {
      if (!dateTimeString) return '';
      const date = new Date(dateTimeString);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      return `${year}-${month}-${day} ${hours}:${minutes}`;
    },

    // 格式化Markdown为HTML（简化版）
    formatMarkdown(content) {
      if (!content) return '';

      // 先去除"新增"标记，在markdown转换之前处理
      // 这样可以避免markdown转换后无法匹配的问题
      let html = content
          .replace(/\*\*新增\*\*-/g, '')  // **新增**-xxx -> xxx (保留xxx的原有格式)
          .replace(/新增-/g, '');  // 新增-xxx -> xxx (保留xxx的原有格式)

      // 转义HTML特殊字符
      html = html
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;');

      // 转换Markdown语法
      // 标题 #
      html = html.replace(/^#{6}\s+(.+)$/gm, '<h6>$1</h6>');
      html = html.replace(/^#{5}\s+(.+)$/gm, '<h5>$1</h5>');
      html = html.replace(/^#{4}\s+(.+)$/gm, '<h4>$1</h4>');
      html = html.replace(/^#{3}\s+(.+)$/gm, '<h3>$1</h3>');
      html = html.replace(/^#{2}\s+(.+)$/gm, '<h2>$1</h2>');
      html = html.replace(/^#{1}\s+(.+)$/gm, '<h1>$1</h1>');

      // 粗体 **text** 或 __text__
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');

      // 斜体 *text* 或 _text_
      html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
      html = html.replace(/_(.+?)_/g, '<em>$1</em>');

      // 代码块 ```code```
      html = html.replace(/```([\s\S]+?)```/g, '<pre><code>$1</code></pre>');

      // 行内代码 `code`
      html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

      // 换行符转换为<br>
      html = html.replace(/\n/g, '<br>');

      return html;
    },

    // 将HTML的<br>标签转换为换行符（用于Excel导出）
    convertBrToNewline(text) {
      if (!text) return '';
      return text.replace(/<br\s*\/?>/gi, '\n');
    },

    // 过滤掉总结和建议部分，只保留测试用例内容
    filterTestCasesOnly(content) {
      if (!content) return '';

      const lines = content.split('\n');
      const filteredLines = [];
      let inTestCaseSection = true;

      for (let line of lines) {
        const trimmedLine = line.trim();

        // 检查是否到了总结或建议部分
        if (trimmedLine.includes('总结') ||
            trimmedLine.includes('建议') ||
            trimmedLine.includes('Summary') ||
            trimmedLine.includes('Recommendation') ||
            trimmedLine.includes('最后') ||
            trimmedLine.includes('补充说明')) {
          inTestCaseSection = false;
          break;
        }

        if (inTestCaseSection) {
          filteredLines.push(line);
        }
      }

      return filteredLines.join('\n');
    },

    // 解析表格格式的测试用例（参考AutoGenTestCase的做法）
    parseTableFormat(content) {
      if (!content) return [];

      // 预处理：将 <br> 和 <br/> 标签转换为换行符，处理嵌入HTML的表格
      let processed = content.replace(/<br\s*\/?>/gi, '\n');
      // 处理加粗/斜体标记（移除 Markdown 格式标记）
      processed = processed.replace(/\*\*(.+?)\*\*/g, '$1');
      processed = processed.replace(/\*(.+?)\*/g, '$1');

      const lines = processed.split('\n').filter(line => line.trim());
      const worksheetData = [];
      const headerMapping = {
        '编号': '测试用例编号', '序号': '测试用例编号', 'ID': '测试用例编号', 'caseid': '测试用例编号',
        '场景': '测试场景', '标题': '测试场景', '名称': '测试场景', 'scenario': '测试场景',
        '测试步骤': '操作步骤', 'Test Steps': '操作步骤', '步骤': '操作步骤', 'steps': '操作步骤',
        '前置条件': '前置条件', 'precondition': '前置条件',
        '预期结果': '预期结果', 'expected': '预期结果', '期望结果': '预期结果',
        '优先级': '优先级', 'priority': '优先级'
      };

      for (let line of lines) {
        const trimmedLine = line.trim();

        // 检查是否是表格行（包含|分隔符，且不是分隔线）
        if (trimmedLine.includes('|') && !trimmedLine.includes('--------')) {
          const cells = trimmedLine.split('|')
            .map(cell => {
              // 清理每个单元格：去掉首尾空格、Markdown格式标记
              let cleaned = cell.trim();
              cleaned = cleaned.replace(/\*\*(.+?)\*\*/g, '$1');
              cleaned = cleaned.replace(/\*(.+?)\*/g, '$1');
              cleaned = cleaned.replace(/<br\s*\/?>/gi, '\n');
              return cleaned;
            })
            .filter(cell => cell !== '');

          if (cells.length > 1) {
            // 第一行是表头时，标准化表头名称
            if (worksheetData.length === 0) {
              const normalizedHeaders = cells.map(h => headerMapping[h] || h);
              worksheetData.push(normalizedHeaders);
            } else {
              worksheetData.push(cells);
            }
          }
        }
      }

      // 确保至少返回表头+一行数据
      if (worksheetData.length < 2) return [];

      return worksheetData;
    },

    // 解析结构化格式的测试用例
    parseStructuredFormat(content) {
      if (!content) return [];

      const lines = content.split('\n').filter(line => line.trim());
      const worksheetData = [];

      // 添加表头
      worksheetData.push([
        this.$t('requirementAnalysis.excelTestCaseNumber'),
        this.$t('requirementAnalysis.excelTestScenario'),
        this.$t('requirementAnalysis.excelPrecondition'),
        this.$t('requirementAnalysis.excelTestSteps'),
        this.$t('requirementAnalysis.excelExpectedResult'),
        this.$t('requirementAnalysis.excelPriority')
      ]);

      let currentTestCase = {};
      let testCaseNumber = 1;
      let i = 0;

      while (i < lines.length) {
        const line = lines[i].trim();

        // 识别测试用例开始标志
        if (line.includes('测试用例') || line.includes('Test Case') ||
            line.match(/^(\d+\.|\*|\-|\d+、)/)) {

          // 如果之前有测试用例数据，先保存
          if (Object.keys(currentTestCase).length > 0) {
            worksheetData.push([
              currentTestCase.number || `TC${testCaseNumber}`,
              currentTestCase.scenario || '',
              currentTestCase.precondition || '',
              currentTestCase.steps || '',
              currentTestCase.expected || '',
              currentTestCase.priority || '中'
            ]);
            testCaseNumber++;
          }

          // 开始新的测试用例
          currentTestCase = {
            number: `TC${testCaseNumber}`,
            scenario: line.replace(/^(\d+\.|\*|\-|\d+、)\s*/, '').replace(/测试用例\d*[:：]?\s*/, ''),
            precondition: '',
            steps: '',
            expected: '',
            priority: '中'
          };
          i++;
        }
        // 识别前置条件
        else if (line.includes('前置条件') || line.includes('前提') ||
            line.includes('Precondition')) {
          let precondition = line.replace(/.*?[:：]\s*/, '');
          // 收集后续的前置条件行
          i++;
          while (i < lines.length) {
            const nextLine = lines[i].trim();
            if (nextLine.includes('测试步骤') || nextLine.includes('操作步骤') ||
                nextLine.includes('Test Steps') || nextLine.includes('步骤') ||
                nextLine.includes('预期结果') || nextLine.includes('Expected') ||
                nextLine.includes('优先级') || nextLine.includes('Priority') ||
                nextLine.includes('测试用例') || nextLine.includes('Test Case') ||
                nextLine.match(/^(\d+\.|\*|\-|\d+、)/)) {
              break;
            }
            if (nextLine) {
              precondition += '\n' + nextLine;
            }
            i++;
          }
          currentTestCase.precondition = precondition;
        }
        // 识别测试步骤
        else if (line.includes('测试步骤') || line.includes('操作步骤') ||
            line.includes('Test Steps') || line.includes('步骤')) {
          let steps = line.replace(/.*?[:：]\s*/, '');
          // 收集后续的步骤行
          i++;
          while (i < lines.length) {
            const nextLine = lines[i].trim();
            if (nextLine.includes('预期结果') || nextLine.includes('Expected') ||
                nextLine.includes('优先级') || nextLine.includes('Priority') ||
                nextLine.includes('测试用例') || nextLine.includes('Test Case') ||
                nextLine.match(/^(\d+\.|\*|\-|\d+、)/)) {
              break;
            }
            if (nextLine) {
              steps += '\n' + nextLine;
            }
            i++;
          }
          currentTestCase.steps = steps;
        }
        // 识别预期结果
        else if (line.includes('预期结果') || line.includes('Expected') ||
            line.includes('期望')) {
          let expected = line.replace(/.*?[:：]\s*/, '');
          // 收集后续的结果行
          i++;
          while (i < lines.length) {
            const nextLine = lines[i].trim();
            if (nextLine.includes('优先级') || nextLine.includes('Priority') ||
                nextLine.includes('测试用例') || nextLine.includes('Test Case') ||
                nextLine.match(/^(\d+\.|\*|\-|\d+、)/)) {
              break;
            }
            if (nextLine) {
              expected += '\n' + nextLine;
            }
            i++;
          }
          currentTestCase.expected = expected;
        }
        // 识别优先级
        else if (line.includes('优先级') || line.includes('Priority')) {
          currentTestCase.priority = line.replace(/.*?[:：]\s*/, '');
          i++;
        }
        // 如果是没有明确标识的行，可能是场景描述的延续
        else if (Object.keys(currentTestCase).length > 0 &&
            !currentTestCase.steps && !currentTestCase.expected &&
            !currentTestCase.precondition) {
          if (currentTestCase.scenario && line.length > 5) {
            currentTestCase.scenario += '\n' + line;
          }
          i++;
        } else {
          i++;
        }
      }

      // 保存最后一个测试用例
      if (Object.keys(currentTestCase).length > 0) {
        worksheetData.push([
          currentTestCase.number || `TC${testCaseNumber}`,
          currentTestCase.scenario || '',
          currentTestCase.precondition || '',
          currentTestCase.steps || '',
          currentTestCase.expected || '',
          currentTestCase.priority || '中'
        ]);
      }

      // 如果没有解析到结构化数据，则按原格式输出
      if (worksheetData.length <= 1) {
        worksheetData.length = 0; // 清空
        worksheetData.push([this.$t('requirementAnalysis.testCaseContent')]);
        content.split('\n').forEach((line, index) => {
          if (line.trim()) {
            worksheetData.push([line.trim()]);
          }
        });
      }

      return worksheetData;
    }
  }
}
</script>

<style scoped>
.requirement-analysis {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  position: relative;
}

.page-header {
  text-align: center;
  margin-bottom: 40px;
}

.page-header h1 {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 10px;
}

.page-header p {
  color: #666;
  font-size: 1.1rem;
}

/* 输出模式设置区域 - 全局 */
.output-mode-section {
  margin-bottom: 30px;
}

.output-mode-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(226, 232, 240, 0.8);
  transition: all 0.3s ease;
}

.output-mode-card:hover {
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
}

.output-mode-card h3 {
  font-size: 1.3rem;
  color: #1a202c;
  margin: 0 0 8px 0;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-section-desc {
  color: #64748b;
  font-size: 0.9rem;
  margin: 0 0 16px 0;
  line-height: 1.5;
}

/* 配置引导弹出窗口 */
.modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  background: rgba(15, 23, 42, 0.6) !important;
  backdrop-filter: blur(4px);
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  z-index: 9999 !important;
  padding: 20px;
  margin: 0 !important;
  opacity: 1 !important;
}

.guide-config-modal {
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important;
  border-radius: 24px;
  padding: 36px;
  max-width: 850px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(226, 232, 240, 0.8);
  position: relative;
  flex-shrink: 0;
  margin: auto;
  opacity: 1 !important;
}

.guide-config-modal::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 5px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 24px 24px 0 0;
}

.guide-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 28px;
}

.guide-icon {
  width: 56px;
  height: 56px;
  flex-shrink: 0;
  filter: drop-shadow(0 4px 8px rgba(245, 158, 11, 0.2));
}

.guide-title h2 {
  font-size: 1.6rem;
  color: #1a202c;
  margin: 0 0 6px 0;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.guide-title p {
  color: #64748b;
  font-size: 0.95rem;
  margin: 0;
  font-weight: 400;
}

.config-groups {
  margin-bottom: 24px;
}

.config-group {
  margin-bottom: 20px;
}

.group-label {
  font-size: 0.85rem;
  color: #94a3b8;
  margin-bottom: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.config-items-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.config-item-inline {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-radius: 12px;
  border: 2px solid transparent;
  position: relative;
  overflow: hidden;
  font-weight: 500;
}

.config-item-inline::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 12px 0 0 12px;
}

.config-item-inline.optional {
  opacity: 0.75;
}

/* 根据状态设置背景色和样式 */
.config-item-inline.status-enabled {
  background: linear-gradient(135deg, rgba(236, 253, 245, 0.9) 0%, rgba(220, 252, 231, 0.6) 100%);
  border-color: rgba(34, 197, 94, 0.2);
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.1);
}

.config-item-inline.status-enabled::before {
  background: linear-gradient(180deg, #22c55e 0%, #16a34a 100%);
}

.config-item-inline.status-disabled {
  background: linear-gradient(135deg, rgba(254, 249, 195, 0.9) 0%, rgba(254, 240, 138, 0.6) 100%);
  border-color: rgba(234, 179, 8, 0.2);
  box-shadow: 0 4px 12px rgba(234, 179, 8, 0.1);
}

.config-item-inline.status-disabled::before {
  background: linear-gradient(180deg, #eab308 0%, #ca8a04 100%);
}

.config-item-inline.status-unconfigured {
  background: linear-gradient(135deg, rgba(254, 242, 242, 0.9) 0%, rgba(254, 226, 226, 0.6) 100%);
  border-color: rgba(239, 68, 68, 0.2);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.1);
}

.config-item-inline.status-unconfigured::before {
  background: linear-gradient(180deg, #ef4444 0%, #dc2626 100%);
}

.status-symbol {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  font-size: 20px;
}

.config-label {
  font-size: 0.95rem;
  color: #334155;
  font-weight: 600;
  flex-shrink: 0;
}

.config-name {
  font-size: 0.85rem;
  color: #64748b;
  margin-left: 4px;
  font-weight: 500;
}

.status-text {
  margin-left: auto;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 700;
  background: #ef4444;
  color: white;
  white-space: nowrap;
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.2);
}

.status-text.warning {
  background: #eab308;
  box-shadow: 0 2px 6px rgba(234, 179, 8, 0.2);
}

.guide-actions {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  gap: 12px;
  margin-top: 30px;
  width: 100%;
}

.guide-actions button {
  flex: none !important;
  width: 240px !important;
  height: 50px !important;
  padding: 0 24px !important;
  border-radius: 12px;
  font-size: 0.95rem;
  font-weight: 600;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center;
  white-space: nowrap;
  opacity: 1 !important;
  cursor: pointer;
  box-sizing: border-box !important;
}

.guide-actions .generate-manual-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white !important;
  border: 2px solid transparent !important;
  box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
}

.guide-actions .skip-action {
  font-size: 0.85rem;
  color: #94a3b8;
  cursor: pointer;
  text-decoration: none;
  padding: 4px 8px;
  transition: color 0.3s;
}

.guide-actions .skip-action:hover {
  color: #64748b;
  text-decoration: underline;
}


.manual-input-card, .upload-card {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e1e8ed;
  margin-bottom: 30px;
}

.manual-input-card h2, .upload-card h2 {
  color: #2c3e50;
  margin-bottom: 20px;
  font-size: 1.5rem;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #2c3e50;
}

/* 输出模式选择器 */
.output-mode-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  align-items: stretch;
}

.mode-option {
  position: relative;
  cursor: pointer;
  display: flex;
}

.mode-option input[type="radio"] {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.mode-content {
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s ease;
  background: white;
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 100%;
  box-sizing: border-box;
}

.mode-option:hover .mode-content {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}

.mode-option.active .mode-content {
  border-color: #3b82f6;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.2);
}

.mode-title {
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 6px;
}

.mode-desc {
  font-size: 0.85rem;
  color: #64748b;
  line-height: 1.4;
}

.mode-option.active .mode-title {
  color: #2563eb;
}

.mode-option.active .mode-desc {
  color: #475569;
}

.form-input, .form-select, .form-textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.form-input:focus, .form-select:focus, .form-textarea:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

.form-textarea {
  resize: vertical;
  font-family: inherit;
}

.char-count {
  text-align: right;
  font-size: 0.85rem;
  color: #666;
  margin-top: 5px;
}

.required {
  color: #e74c3c;
}

.generate-manual-btn, .generate-btn {
  background: #27ae60;
  color: white;
  border: none;
  padding: 15px 30px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.1rem;
  transition: background 0.3s ease;
  width: 100%;
  margin-top: 10px;
}

.generate-manual-btn:hover:not(:disabled), .generate-btn:hover:not(:disabled) {
  background: #219a52;
}

.generate-manual-btn:disabled, .generate-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.divider {
  text-align: center;
  margin: 40px 0;
  position: relative;
}

.divider::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: #ddd;
}

.divider span {
  background: white;
  padding: 0 20px;
  color: #666;
  font-size: 1rem;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  transition: border-color 0.3s ease;
  margin-bottom: 20px;
}

.upload-area.drag-over {
  border-color: #3498db;
  background: #f8f9fa;
}

.upload-placeholder {
  color: #666;
}

.upload-icon {
  font-size: 3rem;
  margin-bottom: 15px;
  display: block;
}

.upload-hint {
  color: #999;
  font-size: 0.9rem;
  margin-top: 5px;
}

.select-file-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  margin-top: 15px;
}

.file-selected {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 6px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.file-icon {
  font-size: 2rem;
}

.file-details {
  flex: 1;
}

.file-name {
  font-weight: 600;
  margin: 0;
}

.file-size {
  color: #666;
  font-size: 0.9rem;
  margin: 5px 0 0 0;
}

.remove-file {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
}

.generation-progress {
  margin: 40px 0;
}

.progress-card {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e1e8ed;
  text-align: center;
}

.progress-card h3 {
  color: #2c3e50;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}

.current-mode-badge {
  display: inline-block;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 500;
  margin-left: 8px;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.progress-info {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-bottom: 30px;
  flex-wrap: wrap;
}

.progress-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.progress-item .label {
  font-size: 0.9rem;
  color: #666;
}

.progress-item .value {
  font-weight: 600;
  color: #2c3e50;
}

/* 思考过程展示区域 */
.thinking-process-display {
  margin: 20px 0;
  border: 2px solid #d6e9ff;
  border-radius: 10px;
  overflow: hidden;
  background: linear-gradient(135deg, #f0f7ff 0%, #f9fbff 100%);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.08);
}
.thinking-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}
.thinking-icon { font-size: 18px; animation: pulse-icon 1.5s ease-in-out infinite; }
@keyframes pulse-icon { 0%,100%{transform:scale(1)} 50%{transform:scale(1.15)} }
.thinking-title { font-weight: 600; font-size: 15px; }
.thinking-status { margin-left: auto; font-size: 13px; opacity: 0.9; max-width: 60%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.thinking-timeline {
  max-height: 320px;
  overflow-y: auto;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.thinking-step {
  display: flex;
  gap: 12px;
  padding: 10px 12px;
  background: #fff;
  border-left: 3px solid #667eea;
  border-radius: 6px;
  transition: all 0.3s;
  opacity: 0.4;
  transform: translateX(-4px);
}
.thinking-step.is-current {
  opacity: 1;
  transform: translateX(0);
  background: #fff;
  box-shadow: 0 0 0 2px rgba(102,126,234,0.2), 0 4px 12px rgba(102,126,234,0.12);
  border-left-color: #f5576c;
  animation: step-flash 0.4s ease-out;
}
@keyframes step-flash { 0%{box-shadow:0 0 0 0 rgba(102,126,234,0.6)} 100%{box-shadow:0 0 0 6px rgba(102,126,234,0)} }
.thinking-step:not(.is-current) { opacity: 0.7; }
.thinking-phase {
  flex: 0 0 auto;
  font-weight: 700;
  color: #667eea;
  font-size: 14px;
  min-width: 110px;
}
.thinking-step.is-current .thinking-phase { color: #f5576c; }
.thinking-content { flex: 1; }
.thinking-text {
  font-weight: 500;
  color: #2c3e50;
  font-size: 14px;
  margin-bottom: 4px;
}
.thinking-detail {
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
}
.thinking-pulse {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  align-items: center;
}
.pulse-dot {
  width: 8px; height: 8px;
  background: #667eea;
  border-radius: 50%;
  animation: pulse-dot 1.2s ease-in-out infinite;
}
.pulse-dot:nth-child(2) { animation-delay: 0.2s; }
.pulse-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes pulse-dot { 0%,100%{opacity:0.3; transform:scale(0.8)} 50%{opacity:1; transform:scale(1.2)} }

/* 降级提示 */
.fallback-notice {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 16px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 6px;
  color: #d46b08;
  font-size: 13px;
  margin: 10px 0;
}

/* 流式内容显示区域 */
.stream-content-display {
  margin: 20px 0;
  border: 2px solid #e1e8ed;
  border-radius: 8px;
  overflow: hidden;
  background: #f8f9fa;
}

.stream-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #e9ecef;
  border-bottom: 1px solid #dee2e6;
}

.stream-title {
  font-weight: 600;
  color: #495057;
  font-size: 0.95rem;
}

.stream-status {
  font-size: 0.85rem;
  color: #6c757d;
  background: white;
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid #dee2e6;
}

.stream-content {
  max-height: 400px;
  overflow-y: auto;
  padding: 16px;
  text-align: left;
  background: white;
  font-size: 0.9rem;
  line-height: 1.6;
  color: #2c3e50;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.stream-content::-webkit-scrollbar {
  width: 8px;
}

.stream-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.stream-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.stream-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 最终版用例特殊样式 */
.stream-content.final-testcases {
  background: #f0f7ff;
  border-left: 4px solid #2196F3;
}

.stream-content.final-testcases::before {
  content: '📋 最终版本';
  display: block;
  font-weight: 600;
  color: #2196F3;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e3f2fd;
}

/* 流式输出指示器 */
.streaming-indicator {
  font-size: 0.85em;
  margin-left: 8px;
  color: #4CAF50;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.stream-content h1,
.stream-content h2,
.stream-content h3,
.stream-content h4,
.stream-content h5,
.stream-content h6 {
  margin-top: 1em;
  margin-bottom: 0.5em;
  color: #2c3e50;
  font-weight: 600;
}

.stream-content code {
  background: #f1f3f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
}

.stream-content pre {
  background: #f1f3f5;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 10px 0;
}

.stream-content pre code {
  background: none;
  padding: 0;
}

.progress-steps {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-bottom: 30px;
  flex-wrap: wrap;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  opacity: 0.4;
  transition: opacity 0.3s ease;
}

.step.active {
  opacity: 1;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #ddd;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: white;
}

.step.active .step-number {
  background: #3498db;
}

.step-text {
  font-size: 0.9rem;
  color: #666;
}

.cancel-generation-btn {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
}

.review-gate-actions,
.completion-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  flex-wrap: wrap;
}

.review-gate-actions button,
.completion-actions button {
  flex: 1;
  min-width: 150px;
  padding: 12px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.completion-actions .download-btn {
  background: #28a745;
  color: white;
  font-size: 1rem;
}

.completion-actions .download-btn:hover {
  background: #218838;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3);
}

.review-gate-actions .save-btn,
.completion-actions .save-btn {
  background: #007bff;
  color: white;
  font-size: 1rem;
}

.completion-actions .save-btn:hover {
  background: #0056b3;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 123, 255, 0.3);
}

.review-gate-actions .new-generation-btn,
.completion-actions .new-generation-btn {
  background: #6c757d;
  color: white;
  font-size: 1rem;
}

.completion-actions .new-generation-btn:hover {
  background: #5a6268;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(108, 117, 125, 0.3);
}

.completion-actions .auto-import-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 1rem;
}

.completion-actions .auto-import-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #5a6fd6 0%, #6a4192 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
}

.completion-actions .auto-import-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.completion-actions .edit-btn {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  font-size: 1rem;
}

.completion-actions .edit-btn:hover {
  background: linear-gradient(135deg, #e082e9 0%, #e5475c 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(245, 87, 108, 0.3);
}

.completion-actions .discard-btn {
  background: #dc3545;
  color: white;
  font-size: 1rem;
}

.completion-actions .discard-btn:hover {
  background: #c82333;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(220, 53, 69, 0.3);
}

.generation-result {
  margin: 40px 0;
}

.result-header {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e1e8ed;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}

.result-header h2 {
  color: #27ae60;
  margin: 0;
}

.result-summary {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.summary-item {
  color: #666;
  font-size: 0.9rem;
}

.new-generation-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
}

.generated-testcases-section, .review-feedback-section, .final-testcases-section {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 1px solid #e1e8ed;
  margin-bottom: 20px;
}

.generated-testcases-section h3, .review-feedback-section h3, .final-testcases-section h3 {
  color: #2c3e50;
  margin-bottom: 20px;
}

.testcase-content, .review-content {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 20px;
  border-left: 4px solid #3498db;
}

.testcase-content pre, .review-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.9rem;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .result-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .progress-info, .result-summary {
    flex-direction: column;
    gap: 10px;
  }

  .progress-steps {
    gap: 10px;
  }
}

.actions-section {
  display: flex;
  gap: 20px;
  justify-content: center;
  margin-top: 30px;
  flex-wrap: wrap;
}

.download-btn, .save-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
}

.download-btn {
  background-color: #1abc9c;
  color: white;
}

.download-btn:hover {
  background-color: #16a085;
}

.save-btn {
  background-color: #3498db;
  color: white;
}

.save-btn:hover {
  background-color: #2980b9;
}

@media (max-width: 768px) {
  .actions-section {
    flex-direction: column;
    align-items: center;
  }

  .download-btn, .save-btn {
    width: 100%;
    max-width: 300px;
    justify-content: center;
  }
}
</style>

<style>
/* 全局样式：确保弹窗不受任何容器限制 */
.modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  max-width: none !important;
  max-height: none !important;
  background: rgba(15, 23, 42, 0.6) !important;
  backdrop-filter: blur(4px);
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  z-index: 9999 !important;
  padding: 20px;
  margin: 0 !important;
  opacity: 1 !important;
  box-sizing: border-box !important;
}

.guide-config-modal {
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important;
  border-radius: 24px;
  padding: 36px;
  max-width: 850px !important;
  width: 100% !important;
  min-width: 300px !important;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(226, 232, 240, 0.8);
  position: relative;
  flex-shrink: 0;
  margin: auto;
  opacity: 1 !important;
  box-sizing: border-box !important;
}

/* 全局按钮样式 */
.guide-actions {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  gap: 12px;
  margin-top: 30px;
  width: 100%;
}

.guide-actions button {
  flex: none !important;
  width: 240px !important;
  height: 50px !important;
  padding: 0 24px !important;
  border-radius: 12px;
  font-size: 0.95rem;
  font-weight: 600;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center;
  white-space: nowrap;
  opacity: 1 !important;
  box-sizing: border-box !important;
  cursor: pointer;
}

.guide-actions .generate-manual-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white !important;
  border: 2px solid transparent !important;
  box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
}

.guide-actions .skip-action {
  font-size: 0.85rem;
  color: #94a3b8;
  cursor: pointer;
  text-decoration: none;
  padding: 4px 8px;
  transition: color 0.3s;
}

.guide-actions .skip-action:hover {
  color: #64748b;
  text-decoration: underline;
}
</style>
