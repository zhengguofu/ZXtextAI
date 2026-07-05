<template>
  <div class="ai-config-page">
    <!-- 顶部模式切换 -->
    <div class="mode-bar">
      <div class="mode-info">
        <h2>AI 模型配置</h2>
        <span class="mode-desc">统一管理 AI 模型配置，支持自动选择最优模型</span>
      </div>
      <div class="mode-switch">
        <span class="mode-label" :class="{ on: autoMode }">Auto 智能选择</span>
        <el-switch
          v-model="autoMode"
          active-text="Auto"
          inactive-text="手动"
          :active-value="true"
          :inactive-value="false"
          size="large"
          inline-prompt
          @change="saveAutoMode"
        />
        <span v-if="autoMode" class="auto-flag">已开启 · 系统自动选择最快模型</span>
        <span v-else class="auto-flag manual">已关闭 · 请手动选择启用的模型</span>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button type="primary" :icon="Plus" @click="openAdd">添加模型</el-button>
        <el-button :icon="Refresh" @click="loadConfigs" :loading="loading">刷新</el-button>
      </div>
      <div class="toolbar-right">
        <el-button type="warning" :icon="Connection" @click="autoSpeedTest" :loading="speedTesting">
          全局测速
        </el-button>
      </div>
    </div>

    <!-- 模型列表 -->
    <div class="model-list" v-loading="loading">
      <div
        v-for="config in configs"
        :key="config.id"
        class="model-card"
        :class="{
          active: config.is_active,
          selected: selectedModelId === config.id,
          'speed-best': config.speed_ms > 0 && config.speed_ms === fastestSpeed,
          'speed-testing': singleTestingId === config.id,
          builtin: config.is_builtin
        }"
        @click="!autoMode && selectModel(config)"
      >
        <div class="model-card-header">
          <div class="model-name">
            <span v-if="!autoMode" class="select-radio" :class="{ checked: selectedModelId === config.id }">
              <el-icon v-if="selectedModelId === config.id"><CircleCheckFilled /></el-icon>
              <span v-else class="radio-circle"></span>
            </span>
            <span>{{ config.name }}</span>
            <el-tag v-if="config.is_builtin" size="small" type="warning" effect="dark">内置</el-tag>
            <el-tag v-if="config.speed_ms > 0 && config.speed_ms === fastestSpeed" size="small" type="success" effect="dark">
              <el-icon><TrendCharts /></el-icon> 最快
            </el-tag>
          </div>
          <div class="model-status">
            <template v-if="autoMode">
              <el-switch v-model="config.is_active" :disabled="true" size="small" />
              <span class="auto-mode-hint">Auto</span>
            </template>
            <template v-else>
              <el-button v-if="config.is_active" type="success" size="small" disabled plain>
                <el-icon><CircleCheck /></el-icon> 已启用
              </el-button>
              <el-button v-else-if="selectedModelId === config.id" type="primary" size="small" :loading="enablingId === config.id" @click.stop="enableModel(config)">
                <el-icon><Check /></el-icon> 启用此模型
              </el-button>
              <span v-else class="not-selected-hint">点击卡片选中</span>
            </template>
          </div>
        </div>
        
        <div class="model-card-body">
          <div class="model-info">
            <span class="info-item">
              <el-icon><Cpu /></el-icon>
              {{ config.model_name }}
            </span>
            <span class="info-item">
              <el-icon><Link /></el-icon>
              {{ config.base_url }}
            </span>
            <span v-if="config.speed_ms > 0" class="info-item speed">
              <el-icon><Timer /></el-icon>
              {{ config.speed_ms }}ms
            </span>
            <span v-else class="info-item speed">
              <el-icon><Timer /></el-icon>
              未测试
            </span>
          </div>
        </div>

        <div class="model-card-footer">
          <el-button
            size="small"
            :icon="Connection"
            type="success"
            plain
            @click.stop="speedTestSingle(config)"
            :loading="singleTestingId === config.id"
          >
            测速
          </el-button>
          <el-button
            v-if="!config.is_builtin"
            size="small"
            :icon="Edit"
            text
            @click.stop="editConfig(config)"
          >
            编辑
          </el-button>
          <el-button
            v-if="!config.is_builtin"
            size="small"
            :icon="Delete"
            text
            type="danger"
            @click.stop="deleteConfig(config.id)"
          >
            删除
          </el-button>
        </div>
      </div>
      
      <div v-if="configs.length === 0" class="empty-state">
        <el-empty description="暂无模型配置" :image-size="100" />
      </div>
    </div>

    <!-- 添加/编辑弹窗 -->
    <el-dialog v-model="showDialog" :title="editConfigItem ? '编辑模型' : '添加模型'" width="600px">
      <!-- 预设供应商选择 -->
      <div v-if="!editConfigItem" class="provider-select-section">
        <h4 class="provider-title">选择预设供应商</h4>
        <div class="provider-grid">
          <div
            v-for="provider in presetProviders"
            :key="provider.id"
            class="provider-card"
            :class="{ active: selectedProvider?.id === provider.id, custom: provider.id === 'custom' }"
            @click="selectProvider(provider)"
          >
            <span class="provider-icon">{{ provider.icon }}</span>
            <span class="provider-name">{{ provider.name }}</span>
            <span class="provider-desc">{{ provider.description }}</span>
          </div>
        </div>
      </div>

      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="配置名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入配置名称" />
        </el-form-item>
        
        <!-- 项目采用统一 AI 模型，不再选择角色 -->
        
        <!-- 当选择自定义配置时显示完整表单 -->
        <template v-if="selectedProvider?.id === 'custom' || editConfigItem">
          <el-form-item label="模型类型">
            <el-select v-model="formData.model_type" placeholder="请选择模型类型">
              <el-option label="DeepSeek" value="deepseek" />
              <el-option label="通义千问" value="qwen" />
              <el-option label="智谱" value="zhipu" />
              <el-option label="硅基流动" value="siliconflow" />
              <el-option label="其他" value="other" />
            </el-select>
          </el-form-item>
          <el-form-item label="API Base URL" prop="base_url">
            <el-input v-model="formData.base_url" placeholder="https://api.example.com/v1" />
          </el-form-item>
          <el-form-item label="模型名称" prop="model_name">
            <el-input v-model="formData.model_name" placeholder="如：gpt-4o" />
          </el-form-item>
        </template>
        
        <!-- 当选择预设供应商时显示模型选择 -->
        <template v-else-if="selectedProvider && selectedProvider.models.length > 0">
          <el-form-item label="选择模型">
            <el-select v-model="formData.model_name" placeholder="请选择模型">
              <el-option 
                v-for="model in selectedProvider.models" 
                :key="model.name" 
                :label="model.display_name" 
                :value="model.name" 
              />
            </el-select>
          </el-form-item>
          <el-form-item label="API Base URL">
            <el-input v-model="formData.base_url" :disabled="true" />
          </el-form-item>
          <el-form-item label="模型类型">
            <el-input v-model="formData.model_type" :disabled="true" />
          </el-form-item>
        </template>

        <el-form-item label="API Key" prop="api_key">
          <el-input v-model="formData.api_key" type="password" :placeholder="apiKeyPlaceholder" />
          <span v-if="selectedProvider" class="api-key-help">{{ selectedProvider.api_key_help }}</span>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh, Connection, Edit, Delete, Cpu, Link, Timer, TrendCharts, CircleCheckFilled, CircleCheck, Check } from '@element-plus/icons-vue'
import api from '@/utils/api'

const loading = ref(false)
const speedTesting = ref(false)
const singleTestingId = ref(null)
const showDialog = ref(false)
const submitting = ref(false)
const autoMode = ref(true)
const configs = ref([])
const editConfigItem = ref(null)
const selectedModelId = ref(null)  // 手动模式下当前选中的模型ID
const enablingId = ref(null)         // 正在启用中的模型ID
const formRef = ref(null)
const presetProviders = ref([])
const selectedProvider = ref(null)

const formData = reactive({
  name: '',
  model_type: 'other',
  base_url: '',
  model_name: '',
  api_key: ''
})

const formRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  base_url: [{ required: true, message: '请输入 API Base URL', trigger: 'blur' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  api_key: [{ required: true, message: '请输入 API Key', trigger: 'blur' }]
}

const formatErrorMessage = (error) => {
  if (!error?.response) {
    return error?.message || '网络错误，请稍后重试'
  }
  const data = error.response.data
  if (typeof data === 'string') {
    return data
  }
  // DRF 验证错误通常以字段名为 key 返回数组
  const fieldErrors = []
  for (const [field, messages] of Object.entries(data)) {
    if (Array.isArray(messages)) {
      fieldErrors.push(`${field}: ${messages.join('；')}`)
    } else if (typeof messages === 'string') {
      fieldErrors.push(`${field}: ${messages}`)
    } else {
      fieldErrors.push(`${field}: ${JSON.stringify(messages)}`)
    }
  }
  return fieldErrors.length ? fieldErrors.join('\n') : (data.error || data.detail || error.message || '请求失败')
}

const apiKeyPlaceholder = computed(() => {
  return selectedProvider.value?.api_key_help || '请输入 API Key'
})

const fastestSpeed = computed(() => {
  const speeds = configs.value.filter(c => c.speed_ms > 0).map(c => c.speed_ms)
  return speeds.length ? Math.min(...speeds) : 0
})

const loadConfigs = async () => {
  loading.value = true
  try {
    const res = await api.get('/requirement-analysis/ai-models/', { params: { page_size: 100 } })
    configs.value = res.data?.results || res.data || []
    // 手动模式下默认选中第一个已启用的模型
    if (!autoMode.value && configs.value.length > 0) {
      const ac = configs.value.find(c => c.is_active)
      selectedModelId.value = ac ? ac.id : configs.value[0].id
    }
  } catch (err) {
    ElMessage.error('加载配置失败: ' + (err.response?.data?.error || err.message))
  } finally {
    loading.value = false
  }
}

const loadPresetProviders = async () => {
  try {
    const res = await api.get('/requirement-analysis/ai-models/preset_providers/')
    presetProviders.value = res.data || []
  } catch (err) {
    console.error('加载预设供应商失败:', err)
  }
}

const saveAutoMode = async () => {
  try {
    await api.post('/requirement-analysis/ai-models/set_auto_mode/', { auto_mode: autoMode.value })
    ElMessage.success(autoMode.value ? '已开启自动选择模式' : '已切换为手动选择模式')
  } catch (err) {
    ElMessage.error('保存失败: ' + (err.response?.data?.error || err.message))
  }
}

const toggleActive = async (config) => {
  try {
    await api.patch(`/requirement-analysis/ai-models/${config.id}/`, { is_active: config.is_active })
    ElMessage.success(config.is_active ? '已启用' : '已禁用')
  } catch (err) {
    config.is_active = !config.is_active
    ElMessage.error('操作失败: ' + (err.response?.data?.error || err.message))
  }
}

const speedTestSingle = async (config) => {
  singleTestingId.value = config.id
  try {
    const res = await api.post(`/requirement-analysis/ai-models/${config.id}/speed_test/`)
    config.speed_ms = res.data.speed_ms
    ElMessage.success(`测速完成: ${res.data.speed_ms}ms`)
  } catch (err) {
    ElMessage.error('测速失败: ' + (err.response?.data?.message || err.message))
  } finally {
    singleTestingId.value = null
  }
}

const autoSpeedTest = async () => {
  speedTesting.value = true
  try {
    const res = await api.post('/requirement-analysis/ai-models/auto_speed_test/')
    configs.value.forEach(c => {
      const result = res.data.results.find(r => r.id === c.id)
      if (result) c.speed_ms = result.speed_ms
    })
    ElMessage.success('全局测速完成')
  } catch (err) {
    ElMessage.error('全局测速失败: ' + (err.response?.data?.error || err.message))
  } finally {
    speedTesting.value = false
  }
}

const selectProvider = (provider) => {
  selectedProvider.value = provider
  formData.model_type = provider.model_type
  formData.base_url = provider.base_url
  if (provider.models.length > 0) {
    formData.model_name = provider.models[0].name
  }
}

const openAdd = async () => {
  editConfigItem.value = null
  Object.assign(formData, {
    name: '',
    model_type: 'other',
    base_url: '',
    model_name: '',
    api_key: ''
  })
  await loadPresetProviders()
  // 默认选择"自定义配置"，让用户直接填写完整表单
  const customProvider = presetProviders.value.find(p => p.id === 'custom')
  if (customProvider) {
    selectProvider(customProvider)
  } else {
    selectedProvider.value = null
  }
  showDialog.value = true
}

const editConfig = (config) => {
  editConfigItem.value = config
  selectedProvider.value = null
  Object.assign(formData, {
    name: config.name,
    model_type: config.model_type,
    base_url: config.base_url,
    model_name: config.model_name,
    api_key: ''
  })
  showDialog.value = true
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate()
  submitting.value = true

  // 补齐后端模型默认值，避免 400
  const payload = {
    ...formData,
    role: 'ai_tester', // 项目统一使用 ai_tester 角色
    max_tokens: formData.max_tokens || 4096,
    temperature: formData.temperature || 0.7,
    top_p: formData.top_p || 0.9
  }
  // 新建时默认启用；编辑时保留原状态
  if (!editConfigItem.value) {
    payload.is_active = true
  }

  try {
    if (editConfigItem.value) {
      await api.put(`/requirement-analysis/ai-models/${editConfigItem.value.id}/`, payload)
      ElMessage.success('修改成功')
    } else {
      await api.post('/requirement-analysis/ai-models/', payload)
      ElMessage.success('添加成功')
    }
    showDialog.value = false
    loadConfigs()
  } catch (err) {
    ElMessage.error(formatErrorMessage(err))
  } finally {
    submitting.value = false
  }
}

const deleteConfig = async (id) => {
  try {
    await api.delete(`/requirement-analysis/ai-models/${id}/`)
    configs.value = configs.value.filter(c => c.id !== id)
    ElMessage.success('删除成功')
  } catch (err) {
    ElMessage.error('删除失败: ' + (err.response?.data?.error || err.message))
  }
}

const selectModel = (config) => {
  if (autoMode.value) return
  selectedModelId.value = config.id
}

const enableModel = async (config) => {
  if (autoMode.value) return
  enablingId.value = config.id
  try {
    for (const c of configs.value) {
      if (c.id !== config.id && c.is_active) {
        await api.patch(`/requirement-analysis/ai-models/${c.id}/`, { is_active: false })
        c.is_active = false
      }
    }
    await api.patch(`/requirement-analysis/ai-models/${config.id}/`, { is_active: true })
    config.is_active = true
    selectedModelId.value = config.id
    ElMessage.success(`已启用模型: ${config.name}`)
  } catch (err) {
    ElMessage.error('启用失败: ' + (err.response?.data?.error || err.message))
  } finally {
    enablingId.value = null
  }
}

onMounted(() => {
  loadConfigs()
})
</script>

<style lang="scss" scoped>
.ai-config-page {
  padding: 20px;
}

.mode-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  margin-bottom: 20px;
  
  .mode-info {
    h2 {
      color: #fff;
      margin: 0 0 8px 0;
      font-size: 20px;
      font-weight: 600;
    }
    .mode-desc {
      color: rgba(255, 255, 255, 0.8);
      font-size: 14px;
    }
  }
  
  .mode-switch {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .mode-label {
      color: rgba(255, 255, 255, 0.7);
      font-size: 14px;
      
      &.on {
        color: #fff;
        font-weight: 600;
      }
    }
    
    .auto-flag {
      color: rgba(255, 255, 255, 0.8);
      font-size: 13px;
      padding: 4px 12px;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 20px;
      
      &.manual {
        background: rgba(255, 193, 7, 0.3);
      }
    }
  }
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.model-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.model-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  transition: all 0.3s ease;
  
  &:hover {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
    transform: translateY(-2px);
  }
  
  &.active {
    border-left: 4px solid #67C23A;
  }
  
  &.speed-best {
    border-top: 4px solid #409EFF;
  }
  
  &.builtin {
    background: linear-gradient(180deg, #fffbf5 0%, #fff 100%);
  }
  
  &.speed-testing {
    opacity: 0.7;
  }
}

.model-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  
  .model-name {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 600;
    color: #303133;
  }
}

.model-card-body {
  padding: 16px 20px;
  
  .model-info {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    
    .info-item {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 13px;
      color: #606266;
      
      &.speed {
        color: #67C23A;
        font-weight: 500;
      }
    }
  }
}

.model-card-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  background: #fafafa;
}

.empty-state {
  grid-column: 1 / -1;
  padding: 60px 0;
}

/* 预设供应商选择样式 */
.provider-select-section {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e8e8e8;
  
  .provider-title {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 12px;
  }
  
  .provider-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 12px;
  }
  
  .provider-card {
    padding: 12px;
    border-radius: 8px;
    border: 2px solid #e8e8e8;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: center;
    
    &:hover {
      border-color: #409EFF;
      background: #f5f7fa;
    }
    
    &.active {
      border-color: #409EFF;
      background: #ecf5ff;
    }
    
    &.custom {
      background: #fafafa;
    }
    
    .provider-icon {
      font-size: 24px;
      display: block;
      margin-bottom: 8px;
    }
    
    .provider-name {
      font-size: 13px;
      font-weight: 500;
      color: #303133;
      display: block;
      margin-bottom: 4px;
    }
    
    .provider-desc {
      font-size: 11px;
      color: #909399;
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

/* 选中状态 & 手动模式交互 */
.model-card.selected {
  border: 2px solid #409EFF;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.15);
}

.select-radio {
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  
  .el-icon {
    color: #409EFF;
    font-size: 20px;
  }
  
  .radio-circle {
    width: 18px;
    height: 18px;
    border: 2px solid #c0c4cc;
    border-radius: 50%;
    display: inline-block;
  }
  
  &.checked .radio-circle {
    border-color: #409EFF;
    background: #409EFF;
  }
}

.auto-mode-hint {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}

.not-selected-hint {
  font-size: 12px;
  color: #c0c4cc;
}

.api-key-help {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
  display: block;
}
</style>
