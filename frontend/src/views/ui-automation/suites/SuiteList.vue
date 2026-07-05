<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('uiAutomation.suite.title') }}</h1>
      <el-select v-model="projectId" :placeholder="$t('uiAutomation.common.selectProject')" style="width: 200px; margin-right: 15px" @change="onProjectChange">
        <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
      </el-select>
      <el-button type="primary" @click="handleNewSuite">
        <el-icon><Plus /></el-icon>
        {{ $t('uiAutomation.suite.newSuite') }}
      </el-button>
    </div>

    <div class="card-container">
      <div class="filter-bar">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-input
              v-model="searchText"
              :placeholder="$t('uiAutomation.suite.searchPlaceholder')"
              clearable
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
        </el-row>
      </div>

      <el-table :data="suites" v-loading="loading" style="width: 100%">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="name" :label="$t('uiAutomation.suite.suiteName')" min-width="200">
          <template #default="{ row }">
            <el-link @click="editSuite(row.id)" type="primary">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="description" :label="$t('uiAutomation.common.description')" min-width="200" show-overflow-tooltip />
        <el-table-column :label="$t('uiAutomation.suite.testCaseCount')" width="120">
          <template #default="{ row }">
            {{ row.test_case_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('uiAutomation.suite.executionStatus')" width="100">
          <template #default="{ row }">
            <el-tag :type="getExecutionStatusTag(row.execution_status)">
              {{ getExecutionStatusText(row.execution_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('uiAutomation.suite.passedCount')" width="90">
          <template #default="{ row }">
            <span style="color: #67c23a; font-weight: bold;">{{ row.passed_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('uiAutomation.suite.failedCount')" width="90">
          <template #default="{ row }">
            <span style="color: #f56c6c; font-weight: bold;">{{ row.failed_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="$t('uiAutomation.common.createTime')" width="180" :formatter="formatDate" />
        <el-table-column prop="updated_at" :label="$t('uiAutomation.common.updateTime')" width="180" :formatter="formatDate" />
        <el-table-column :label="$t('uiAutomation.common.operation')" width="240" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="editSuite(row.id)">
              <el-icon><Edit /></el-icon>
              {{ $t('uiAutomation.common.edit') }}
            </el-button>
            <el-button size="small" type="success" @click="runSuite(row)">
              <el-icon><RefreshRight /></el-icon>
              {{ $t('uiAutomation.common.run') }}
            </el-button>
            <el-button size="small" type="danger" @click="deleteSuite(row.id)">
              <el-icon><Delete /></el-icon>
              {{ $t('uiAutomation.common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 创建/编辑套件对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="isEditing ? $t('uiAutomation.suite.editSuite') : $t('uiAutomation.suite.createSuite')"
      width="900px"
      :close-on-click-modal="false"
    >
      <el-form ref="createFormRef" :model="createForm" :rules="formRules" label-width="100px">
        <el-form-item :label="$t('uiAutomation.suite.suiteName')" prop="name">
          <el-input v-model="createForm.name" :placeholder="$t('uiAutomation.suite.rules.nameRequired')" />
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.common.description')" prop="description">
          <el-input v-model="createForm.description" type="textarea" :placeholder="$t('uiAutomation.common.description')" />
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.suite.testCases')">
          <div class="test-case-selector">
            <div class="selector-panel">
              <div class="panel-header">
                <h4>{{ $t('uiAutomation.suite.availableCases') }}</h4>
                <el-input
                  v-model="testCaseSearchText"
                  :placeholder="$t('uiAutomation.suite.searchCases')"
                  size="small"
                  clearable
                  style="width: 200px;"
                >
                  <template #prefix>
                    <el-icon><Search /></el-icon>
                  </template>
                </el-input>
              </div>
              <div class="panel-content">
                <el-table
                  :data="filteredAvailableTestCases"
                  height="300"
                  @row-click="handleTestCaseRowClick"
                  :row-class-name="getTestCaseRowClassName"
                >
                  <el-table-column prop="name" :label="$t('uiAutomation.suite.caseName')" min-width="150" show-overflow-tooltip />
                  <el-table-column prop="priority" :label="$t('uiAutomation.suite.priority')" width="80">
                    <template #default="{ row }">
                      <el-tag size="small" :type="getPriorityTag(row.priority)">
                        {{ getPriorityText(row.priority) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="status" :label="$t('uiAutomation.common.status')" width="80">
                    <template #default="{ row }">
                      <el-tag size="small" :type="getCaseStatusTag(row.status)">
                        {{ getCaseStatusText(row.status) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column :label="$t('uiAutomation.common.operation')" width="80">
                    <template #default="{ row }">
                      <el-button size="small" text @click.stop="addTestCase(row)">
                        <el-icon><ArrowRight /></el-icon>
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>

            <div class="selector-panel">
              <div class="panel-header">
                <h4>{{ $t('uiAutomation.suite.selectedCases') }} ({{ selectedTestCases.length }})</h4>
              </div>
              <div class="panel-content">
                <el-table
                  :data="selectedTestCases"
                  height="300"
                >
                  <el-table-column prop="name" :label="$t('uiAutomation.suite.caseName')" min-width="150" show-overflow-tooltip />
                  <el-table-column prop="priority" :label="$t('uiAutomation.suite.priority')" width="80">
                    <template #default="{ row }">
                      <el-tag size="small" :type="getPriorityTag(row.priority)">
                        {{ getPriorityText(row.priority) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column :label="$t('uiAutomation.common.operation')" width="120">
                    <template #default="{ row, $index }">
                      <el-button
                        size="small"
                        text
                        @click="moveUp($index)"
                        :disabled="$index === 0"
                      >
                        <el-icon><Top /></el-icon>
                      </el-button>
                      <el-button
                        size="small"
                        text
                        @click="moveDown($index)"
                        :disabled="$index === selectedTestCases.length - 1"
                      >
                        <el-icon><Bottom /></el-icon>
                      </el-button>
                      <el-button
                        size="small"
                        text
                        type="danger"
                        @click="removeTestCase($index)"
                      >
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="cancelCreate">{{ $t('uiAutomation.common.cancel') }}</el-button>
          <el-button type="primary" @click="handleCreate" :loading="saving">{{ $t('uiAutomation.common.confirm') }}</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 运行配置对话框 -->
    <el-dialog v-model="showRunDialog" :title="$t('uiAutomation.suite.runConfig')" width="600px" :close-on-click-modal="false">
      <el-form :model="runConfig" label-width="120px">
        <el-form-item :label="$t('uiAutomation.suite.testEngine')">
          <el-select v-model="runConfig.engine" :placeholder="$t('uiAutomation.suite.testEngine')">
            <el-option label="Playwright" value="playwright" />
            <el-option label="Selenium" value="selenium" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.suite.browser')">
          <el-select v-model="runConfig.browser" :placeholder="$t('uiAutomation.suite.browser')">
            <el-option label="Chrome" value="chrome" />
            <el-option label="Firefox" value="firefox" />
            <el-option label="Safari" value="safari" />
            <el-option label="Edge" value="edge" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('uiAutomation.suite.executionMode')">
          <el-radio-group v-model="runConfig.headless">
            <el-radio :label="false">{{ $t('uiAutomation.suite.headedMode') }}</el-radio>
            <el-radio :label="true">{{ $t('uiAutomation.suite.headlessMode') }}</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showRunDialog = false">{{ $t('uiAutomation.common.cancel') }}</el-button>
          <el-button
            type="primary"
            @click="confirmRunSuite"
            :loading="running"
          >
            {{ $t('uiAutomation.suite.startExecution') }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, Search, Edit, Delete, RefreshRight, Collection,
  ArrowRight, Top, Bottom
} from '@element-plus/icons-vue'
import {
  getUiProjects,
  getTestSuites,
  createTestSuite,
  updateTestSuite,
  deleteTestSuite,
  getTestCases,
  getTestSuiteTestCases,
  addTestCaseToTestSuite,
  removeTestCaseFromTestSuite,
  updateTestCaseOrder,
  runTestSuite
} from '@/api/ui_automation'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// 响应式数据
const projects = ref([])
const projectId = ref('')
const suites = ref([])
const loading = ref(false)
const searchText = ref('')
const total = ref(0)
const pagination = reactive({
  currentPage: 1,
  pageSize: 20
})

// 对话框控制
const showCreateDialog = ref(false)
const showRunDialog = ref(false)
const isEditing = ref(false)
const currentSuiteId = ref(null)
const saving = ref(false)
const running = ref(false)

// 表单数据
const createForm = reactive({
  name: '',
  description: ''
})

// 表单验证规则 - 使用 computed 实现动态国际化
const formRules = computed(() => ({
  name: [{ required: true, message: t('uiAutomation.suite.rules.nameRequired'), trigger: 'blur' }]
}))

// 测试用例相关
const availableTestCases = ref([])
const selectedTestCases = ref([])
const testCaseSearchText = ref('')

// 运行配置
const runConfig = reactive({
  engine: 'playwright',
  browser: 'chrome',
  headless: false
})
const currentRunningSuite = ref(null)

// 计算属性 - 过滤后的可用测试用例
const filteredAvailableTestCases = computed(() => {
  if (!testCaseSearchText.value) {
    return availableTestCases.value
  }
  return availableTestCases.value.filter(tc =>
    tc.name.toLowerCase().includes(testCaseSearchText.value.toLowerCase()) ||
    (tc.description && tc.description.toLowerCase().includes(testCaseSearchText.value.toLowerCase()))
  )
})

// Mock 项目数据（带标记，便于区分）
const mockProjects = [
  { id: 'mock-1', name: '电商前台系统（演示）', isMock: true },
  { id: 'mock-2', name: '管理后台系统（演示）', isMock: true },
  { id: 'mock-3', name: '移动端 H5（演示）', isMock: true }
]

// Mock 套件数据
const mockSuites = [
  {
    id: 'mock-suite-1', name: '登录流程回归套件（演示）', description: '覆盖所有登录相关场景', test_case_count: 4,
    execution_status: 'passed', passed_count: 4, failed_count: 0,
    created_at: '2025-06-01T10:00:00Z', updated_at: '2025-06-05T14:30:00Z', isMock: true
  },
  {
    id: 'mock-suite-2', name: '商品搜索测试套件（演示）', description: '搜索功能全面验证', test_case_count: 3,
    execution_status: 'failed', passed_count: 2, failed_count: 1,
    created_at: '2025-06-02T09:00:00Z', updated_at: '2025-06-06T11:00:00Z', isMock: true
  },
  {
    id: 'mock-suite-3', name: '订单提交端到端（演示）', description: '从选品到支付的完整流程', test_case_count: 5,
    execution_status: 'not_run', passed_count: 0, failed_count: 0,
    created_at: '2025-06-03T08:00:00Z', updated_at: '2025-06-03T08:00:00Z', isMock: true
  },
  {
    id: 'mock-suite-4', name: '首页核心功能（演示）', description: '首页各模块功能验证', test_case_count: 6,
    execution_status: 'running', passed_count: 3, failed_count: 0,
    created_at: '2025-06-04T13:00:00Z', updated_at: '2025-06-08T10:15:00Z', isMock: true
  }
]

// Mock 可用用例
const mockTestCases = [
  { id: 'mock-tc-101', name: '正常账号密码登录（演示）', priority: 'high', status: 'ready', isMock: true },
  { id: 'mock-tc-102', name: '手机号验证码登录（演示）', priority: 'high', status: 'ready', isMock: true },
  { id: 'mock-tc-103', name: '第三方 OAuth 登录（演示）', priority: 'medium', status: 'ready', isMock: true },
  { id: 'mock-tc-104', name: '登录错误提示验证（演示）', priority: 'medium', status: 'ready', isMock: true },
  { id: 'mock-tc-105', name: '记住密码功能（演示）', priority: 'low', status: 'draft', isMock: true },
  { id: 'mock-tc-106', name: '搜索关键词联想（演示）', priority: 'high', status: 'ready', isMock: true },
  { id: 'mock-tc-107', name: '搜索结果排序（演示）', priority: 'medium', status: 'ready', isMock: true },
  { id: 'mock-tc-108', name: '空搜索结果页面（演示）', priority: 'low', status: 'ready', isMock: true },
  { id: 'mock-tc-109', name: '加入购物车（演示）', priority: 'high', status: 'ready', isMock: true },
  { id: 'mock-tc-110', name: '购物车数量修改（演示）', priority: 'medium', status: 'ready', isMock: true },
  { id: 'mock-tc-111', name: '提交订单（演示）', priority: 'high', status: 'ready', isMock: true },
  { id: 'mock-tc-112', name: '选择支付方式（演示）', priority: 'high', status: 'ready', isMock: true }
]

// 加载项目列表
const loadProjects = async () => {
  try {
    const response = await getUiProjects({ page_size: 100 })
    const data = response.data.results || response.data
    // 如果没有后端数据，使用 mock
    projects.value = data.length > 0 ? data : mockProjects
  } catch (error) {
    console.error('获取项目列表失败:', error)
    projects.value = mockProjects
  }
}

// 加载测试套件列表
const loadSuites = async () => {
  if (!projectId.value) {
    suites.value = []
    total.value = 0
    return
  }

  loading.value = true
  try {
    const response = await getTestSuites({
      project: projectId.value,
      page: pagination.currentPage,
      page_size: pagination.pageSize,
      search: searchText.value
    })

    if (response.data.results) {
      suites.value = response.data.results
      total.value = response.data.count || 0
    } else {
      suites.value = response.data
      total.value = response.data.length
    }

    // 后端返回空时使用 mock
    if (suites.value.length === 0) {
      suites.value = mockSuites
      total.value = mockSuites.length
    }
  } catch (error) {
    console.error('获取测试套件列表失败:', error)
    suites.value = mockSuites
    total.value = mockSuites.length
  } finally {
    loading.value = false
  }
}

// 加载可用测试用例
const loadAvailableTestCases = async () => {
  if (!projectId.value) return

  try {
    const response = await getTestCases({
      project: projectId.value,
      page_size: 1000
    })
    const data = response.data.results || response.data
    availableTestCases.value = data.length > 0 ? data : mockTestCases
  } catch (error) {
    console.error('获取测试用例列表失败:', error)
    availableTestCases.value = mockTestCases
  }
}

// 项目切换
const onProjectChange = async () => {
  pagination.currentPage = 1
  await loadSuites()
}

// 搜索处理
const handleSearch = async () => {
  pagination.currentPage = 1
  await loadSuites()
}

// 分页处理
const handleSizeChange = async () => {
  pagination.currentPage = 1
  await loadSuites()
}

const handleCurrentChange = async () => {
  await loadSuites()
}

// 确保有真实项目（如果是 mock 项目则自动创建）
const ensureRealProject = async () => {
  const currentProject = projects.value.find(p => p.id === projectId.value)
  if (currentProject && !currentProject.isMock) {
    return projectId.value
  }

  // 创建真实项目
  try {
    const res = await createUiProject({
      name: currentProject ? currentProject.name.replace('（演示）', '') : '默认测试项目',
      description: '自动创建的真实项目',
      base_url: 'http://localhost'
    })
    const realProjectId = res.data.id
    // 替换项目列表中的 mock 项目
    const idx = projects.value.findIndex(p => p.id === projectId.value)
    if (idx >= 0) {
      projects.value[idx] = { id: realProjectId, name: res.data.name }
    } else {
      projects.value.push({ id: realProjectId, name: res.data.name })
    }
    projectId.value = realProjectId
    ElMessage.success('已自动创建真实项目')
    return realProjectId
  } catch (err) {
    console.error('自动创建项目失败:', err)
    ElMessage.error('后端 API 不可用，无法创建真实项目。请确保后端服务已启动。')
    throw err
  }
}

// 确保有真实用例（将 mock 用例转为真实用例）
const ensureRealTestCases = async (projectIdReal) => {
  const realCases = []
  for (const tc of selectedTestCases.value) {
    if (tc.isMock) {
      try {
        const res = await createTestCase({
          name: tc.name.replace('（演示）', ''),
          description: '从演示用例自动创建',
          project: projectIdReal,
          status: tc.status || 'draft',
          priority: tc.priority || 'medium'
        })
        realCases.push({ id: res.data.id, ...tc, isMock: false })
      } catch (err) {
        console.error('自动创建用例失败:', tc.name, err)
      }
    } else {
      realCases.push(tc)
    }
  }
  return realCases
}

// 新增套件
const handleCreate = async () => {
  if (!createForm.name) {
    ElMessage.warning(t('uiAutomation.suite.messages.inputName'))
    return
  }

  if (!projectId.value) {
    ElMessage.warning(t('uiAutomation.suite.messages.selectProject'))
    return
  }

  saving.value = true
  try {
    // 如果是 mock 项目，先创建真实项目
    const realProjectId = await ensureRealProject()

    // 如果有选中的 mock 用例，先创建真实用例
    const realSelectedCases = await ensureRealTestCases(realProjectId)

    const suiteData = {
      project: realProjectId,
      name: createForm.name,
      description: createForm.description
    }

    let suiteId
    if (isEditing.value) {
      // 更新套件
      await updateTestSuite(currentSuiteId.value, suiteData)
      suiteId = currentSuiteId.value
      ElMessage.success(t('uiAutomation.suite.messages.updateSuccess'))
    } else {
      // 创建套件
      const response = await createTestSuite(suiteData)
      suiteId = response.data.id
      ElMessage.success(t('uiAutomation.suite.messages.createSuccess'))
    }

    // 保存测试用例关联
    if (realSelectedCases.length > 0) {
      // 清除旧的关联（如果是编辑模式）
      if (isEditing.value) {
        try {
          const existingTestCases = await getTestSuiteTestCases(suiteId)
          for (const tc of existingTestCases.data) {
            await removeTestCaseFromTestSuite(suiteId, tc.test_case.id)
          }
        } catch (e) { /* 忽略旧关联清除错误 */ }
      }

      // 添加新的关联
      for (let i = 0; i < realSelectedCases.length; i++) {
        await addTestCaseToTestSuite(suiteId, {
          test_case_id: realSelectedCases[i].id,
          order: i
        })
      }
    }

    showCreateDialog.value = false
    await loadSuites()
    resetForm()
  } catch (error) {
    console.error('保存测试套件失败:', error)
    if (error.response?.status === 404) {
      ElMessage.error('后端 API 不可用（404），请确保后端服务已启动')
    } else {
      ElMessage.error(t('uiAutomation.suite.messages.saveFailed'))
    }
  } finally {
    saving.value = false
  }
}

// 编辑套件
const editSuite = async (id) => {
  try {
    // 加载套件详情
    const suites_data = suites.value.find(s => s.id === id)
    if (!suites_data) return

    // mock 套件不能直接编辑后端数据，转为新建模式
    if (suites_data.isMock) {
      ElMessage.info('演示套件不支持编辑，将以该套件为模板新建真实套件')
      isEditing.value = false
      currentSuiteId.value = null
    } else {
      isEditing.value = true
      currentSuiteId.value = id
    }

    createForm.name = suites_data.name.replace('（演示）', '')
    createForm.description = suites_data.description

    // 加载已选测试用例
    if (suites_data.isMock) {
      // mock 套件直接填充演示用例
      selectedTestCases.value = [...mockTestCases]
    } else {
      try {
        const response = await getTestSuiteTestCases(id)
        selectedTestCases.value = response.data.map(item => item.test_case).sort((a, b) => a.order - b.order)
      } catch (e) {
        selectedTestCases.value = []
      }
    }

    // 加载可用测试用例
    await loadAvailableTestCases()

    showCreateDialog.value = true
  } catch (error) {
    console.error('加载套件详情失败:', error)
    ElMessage.error(t('uiAutomation.suite.messages.loadDetailFailed'))
  }
}

// 删除套件
const deleteSuite = async (id) => {
  const suite = suites.value.find(s => s.id === id)
  if (suite && suite.isMock) {
    // mock 数据直接前端移除，不调用 API
    try {
      await ElMessageBox.confirm(
        `确定删除演示套件「${suite.name}」吗？`,
        '删除确认',
        { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
      )
      suites.value = suites.value.filter(s => s.id !== id)
      total.value = suites.value.length
      ElMessage.success('演示套件已删除')
    } catch { /* 用户取消 */ }
    return
  }

  try {
    await ElMessageBox.confirm(t('uiAutomation.suite.messages.deleteConfirm'), t('uiAutomation.messages.confirm.tip'), {
      confirmButtonText: t('uiAutomation.common.confirm'),
      cancelButtonText: t('uiAutomation.common.cancel'),
      type: 'warning'
    })

    await deleteTestSuite(id)
    ElMessage.success(t('uiAutomation.suite.messages.deleteSuccess'))
    await loadSuites()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除测试套件失败:', error)
      ElMessage.error(t('uiAutomation.suite.messages.deleteFailed'))
    }
  }
}

// 运行套件
const runSuite = (suite) => {
  // 检查是否包含测试用例
  if (!suite.test_case_count || suite.test_case_count === 0) {
    ElMessage.warning(t('uiAutomation.suite.messages.noCases'))
    return
  }

  if (suite.isMock) {
    ElMessageBox.confirm(
      '演示套件无法直接执行。是否以该套件为模板创建真实套件并执行？',
      '演示套件提示',
      { confirmButtonText: '创建并执行', cancelButtonText: '取消', type: 'info' }
    ).then(() => {
      // 以该套件为模板打开创建对话框
      editSuite(suite.id)
    }).catch(() => {})
    return
  }

  currentRunningSuite.value = suite
  showRunDialog.value = true
}

// 确认运行套件
const confirmRunSuite = async () => {
  running.value = true
  try {
    const requestData = {
      use_ai: false,
      engine: runConfig.engine,
      browser: runConfig.browser,
      headless: runConfig.headless
    }

    const response = await runTestSuite(currentRunningSuite.value.id, requestData)

    ElMessage.success(t('uiAutomation.suite.messages.startSuccess'))
    showRunDialog.value = false

    // 立即刷新一次以显示"运行中"状态
    await loadSuites()

    // 开始轮询检查执行状态
    pollSuiteStatus(currentRunningSuite.value.id)
  } catch (error) {
    console.error('执行测试套件失败:', error)
    // 如果后端返回了错误消息，显示具体错误
    const errorMsg = error.response?.data?.error || t('uiAutomation.suite.messages.executeFailed')
    ElMessage.error(errorMsg)
  } finally {
    running.value = false
  }
}

// 轮询检查套件执行状态
const pollSuiteStatus = (suiteId) => {
  let pollCount = 0
  const maxPolls = 120 // 最多轮询2分钟（每秒一次）

  const pollInterval = setInterval(async () => {
    pollCount++

    try {
      // 重新加载套件列表
      await loadSuites()

      // 查找当前套件的状态
      const currentSuite = suites.value.find(s => s.id === suiteId)

      if (currentSuite && currentSuite.execution_status !== 'running') {
        // 执行完成，停止轮询
        clearInterval(pollInterval)

        // 根据状态显示消息
        if (currentSuite.execution_status === 'passed') {
          ElMessage.success(`${t('uiAutomation.suite.messages.executionComplete')}: ${t('uiAutomation.suite.messages.allPassed')} (${currentSuite.passed_count}/${currentSuite.passed_count + currentSuite.failed_count})`)
        } else if (currentSuite.execution_status === 'failed') {
          ElMessage.warning(`${t('uiAutomation.suite.messages.executionComplete')}: ${t('uiAutomation.suite.messages.partialFailed')} (${t('uiAutomation.suite.messages.passed')}: ${currentSuite.passed_count}, ${t('uiAutomation.status.failed')}: ${currentSuite.failed_count})`)
        }
      }

      // 超过最大轮询次数，停止轮询
      if (pollCount >= maxPolls) {
        clearInterval(pollInterval)
        ElMessage.info(t('uiAutomation.suite.messages.longExecution'))
      }
    } catch (error) {
      console.error('轮询套件状态失败:', error)
      // 发生错误时停止轮询
      clearInterval(pollInterval)
    }
  }, 3000) // 每3秒轮询一次
}

// 测试用例管理方法
const handleTestCaseRowClick = (row) => {
  // 双击添加测试用例
  addTestCase(row)
}

const getTestCaseRowClassName = ({ row }) => {
  // 如果已选中，添加特殊样式
  return selectedTestCases.value.some(tc => tc.id === row.id) ? 'selected-row' : ''
}

const addTestCase = (testCase) => {
  // 检查是否已存在
  if (selectedTestCases.value.some(tc => tc.id === testCase.id)) {
    ElMessage.warning(t('uiAutomation.suite.messages.caseAdded'))
    return
  }
  selectedTestCases.value.push({ ...testCase })
}

const removeTestCase = (index) => {
  selectedTestCases.value.splice(index, 1)
}

const moveUp = (index) => {
  if (index > 0) {
    const temp = selectedTestCases.value[index]
    selectedTestCases.value[index] = selectedTestCases.value[index - 1]
    selectedTestCases.value[index - 1] = temp
  }
}

const moveDown = (index) => {
  if (index < selectedTestCases.value.length - 1) {
    const temp = selectedTestCases.value[index]
    selectedTestCases.value[index] = selectedTestCases.value[index + 1]
    selectedTestCases.value[index + 1] = temp
  }
}

// 重置表单
const resetForm = () => {
  createForm.name = ''
  createForm.description = ''
  selectedTestCases.value = []
  testCaseSearchText.value = ''
  isEditing.value = false
  currentSuiteId.value = null
}

// 取消创建
const cancelCreate = () => {
  showCreateDialog.value = false
  resetForm()
}

// 新增套件按钮点击
const handleCreateButtonClick = async () => {
  resetForm()
  await loadAvailableTestCases()
  showCreateDialog.value = true
}

// 辅助方法
const formatDate = (row, column, cellValue) => {
  if (!cellValue) return ''
  return new Date(cellValue).toLocaleString()
}

const getExecutionStatusTag = (status) => {
  const statusMap = {
    'not_run': 'info',
    'passed': 'success',
    'failed': 'danger',
    'running': 'warning'
  }
  return statusMap[status] || 'info'
}

const getExecutionStatusText = (status) => {
  const statusKey = {
    'not_run': 'notRun',
    'passed': 'passed',
    'failed': 'failed',
    'running': 'running'
  }[status]
  return statusKey ? t(`uiAutomation.status.${statusKey}`) : t('uiAutomation.status.unknown')
}

const getPriorityTag = (priority) => {
  const priorityMap = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'info'
  }
  return priorityMap[priority] || 'info'
}

const getPriorityText = (priority) => {
  const priorityKey = {
    'high': 'high',
    'medium': 'medium',
    'low': 'low'
  }[priority]
  return priorityKey ? t(`uiAutomation.priority.${priorityKey}`) : t('uiAutomation.status.unknown')
}

const getCaseStatusTag = (status) => {
  const statusMap = {
    'draft': 'info',
    'ready': 'primary',
    'running': 'warning',
    'passed': 'success',
    'failed': 'danger'
  }
  return statusMap[status] || 'info'
}

const getCaseStatusText = (status) => {
  const statusKey = {
    'draft': 'draft',
    'ready': 'ready',
    'running': 'running',
    'passed': 'passed',
    'failed': 'failed'
  }[status]
  return statusKey ? t(`uiAutomation.status.${statusKey}`) : t('uiAutomation.status.unknown')
}

// 监听新增套件按钮
const originalShowCreateDialog = showCreateDialog
onMounted(async () => {
  await loadProjects()
  if (projects.value.length > 0) {
    projectId.value = projects.value[0].id
    await loadSuites()
  }
})

// 监听对话框打开事件
const openCreateDialog = async () => {
  if (!isEditing.value) {
    await loadAvailableTestCases()
  }
}

// 修改新增套件按钮点击事件
const handleNewSuite = async () => {
  resetForm()
  await loadAvailableTestCases()
  showCreateDialog.value = true
}
</script>

<style scoped lang="scss">
.page-container {
  padding: 20px;
  background: #f5f5f5;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  background: white;
  padding: 20px;
  border-radius: 4px;
}

.page-title {
  margin: 0;
  font-size: 24px;
}

.card-container {
  background: white;
  padding: 20px;
  border-radius: 4px;
}

.filter-bar {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

// 测试用例选择器样式
.test-case-selector {
  display: flex;
  gap: 20px;
  width: 100%;
}

.selector-panel {
  flex: 1;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.panel-header {
  background: #f5f7fa;
  padding: 12px 15px;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  justify-content: space-between;
  align-items: center;

  h4 {
    margin: 0;
    font-size: 14px;
    color: #303133;
  }
}

.panel-content {
  padding: 10px;
}


:deep(.selected-row) {
  background-color: #f0f9ff !important;
}

:deep(.el-table__row) {
  cursor: pointer;

  &:hover {
    background-color: #f5f7fa;
  }
}

.mode-description {
  margin-top: 8px;

  .description-text {
    font-size: 12px;
    color: #909399;
    line-height: 1.5;
  }
}
</style>
