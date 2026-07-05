<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('testcase.title') }}</h1>
      <div class="header-actions">
        <el-button
          v-if="selectedTestCases.length > 0"
          type="danger"
          @click="batchDeleteTestCases"
          :disabled="isDeleting">
          <el-icon><Delete /></el-icon>
          {{ $t('testcase.batchDelete') }} ({{ selectedTestCases.length }})
        </el-button>
        <el-button type="success" @click="exportToExcel">
          <el-icon><Download /></el-icon>
          {{ $t('testcase.exportExcel') }}
        </el-button>
        <el-button type="primary" @click="$router.push('/ai-generation/testcases/create')">
          <el-icon><Plus /></el-icon>
          {{ $t('testcase.newCase') }}
        </el-button>
      </div>
    </div>
    
    <div class="card-container">
      <div class="filter-bar">
        <el-row :gutter="20">
          <el-col :span="5">
            <el-input
              v-model="searchText"
              :placeholder="$t('testcase.searchPlaceholder')"
              clearable
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="4">
            <el-select v-model="projectFilter" :placeholder="$t('testcase.relatedProject')" clearable @change="handleFilter">
              <el-option
                v-for="project in projects"
                :key="project.id"
                :label="project.name"
                :value="project.id"
              />
            </el-select>
          </el-col>
          <el-col :span="3">
            <el-select v-model="priorityFilter" :placeholder="$t('testcase.priorityFilter')" clearable @change="handleFilter">
              <el-option :label="$t('testcase.low')" value="low" />
              <el-option :label="$t('testcase.medium')" value="medium" />
              <el-option :label="$t('testcase.high')" value="high" />
              <el-option :label="$t('testcase.critical')" value="critical" />
            </el-select>
          </el-col>
        </el-row>
      </div>
      
      <div class="table-container">
        <el-table 
          ref="tableRef"
          :data="testcases" 
          v-loading="loading" 
          style="width: 100%"
          height="100%"
          :row-key="(row) => row.id"
          :default-sort="{ prop: 'created_at', order: 'descending' }"
          @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="55" :selectable="isSelectable" />
          <el-table-column type="index" :label="$t('testcase.serialNumber')" width="80" :index="getSerialNumber" />
          <el-table-column prop="title" :label="$t('testcase.caseTitle')" min-width="250">
            <template #default="{ row }">
              <el-link @click="goToTestCase(row.id)" type="primary">
                {{ row.title }}
              </el-link>
            </template>
          </el-table-column>
          <el-table-column prop="project.name" :label="$t('testcase.relatedProject')" width="150">
            <template #default="{ row }">
              {{ row.project?.name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="versions" :label="$t('testcase.relatedVersions')" width="200">
            <template #default="{ row }">
              <div v-if="row.versions && row.versions.length > 0" class="version-tags">
                <el-tag 
                  v-for="version in row.versions.slice(0, 2)" 
                  :key="version.id" 
                  size="small" 
                  :type="version.is_baseline ? 'warning' : 'info'"
                  class="version-tag"
                >
                  {{ version.name }}
                </el-tag>
                <el-tooltip v-if="row.versions.length > 2" :content="getVersionsTooltip(row.versions)">
                  <el-tag size="small" type="info" class="version-tag">
                    +{{ row.versions.length - 2 }}
                  </el-tag>
                </el-tooltip>
              </div>
              <span v-else class="no-version">{{ $t('testcase.noVersion') }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="priority" :label="$t('testcase.priority')" width="100">
            <template #default="{ row }">
              <el-tag :class="`priority-tag ${row.priority}`">{{ getPriorityText(row.priority) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="test_type" :label="$t('testcase.testType')" width="120">
            <template #default="{ row }">
              {{ getTypeText(row.test_type) }}
            </template>
          </el-table-column>
          <el-table-column prop="author.username" :label="$t('testcase.author')" width="120" />
          <el-table-column prop="created_at" :label="$t('testcase.createdAt')" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('project.actions')" width="150" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="editTestCase(row)">{{ $t('common.edit') }}</el-button>
              <el-button size="small" type="danger" @click="deleteTestCase(row)">{{ $t('common.delete') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <div class="pagination-container">
        <div class="select-all-info" v-if="total > 0">
          <label class="el-checkbox">
            <input type="checkbox" v-model="selectAll" @change="handleSelectAll" />
            <span class="el-checkbox__label">全选 ({{ total }} 条)</span>
          </label>
          <span v-if="selectedTestCases.length > 0" class="selected-info">
            已选择 {{ selectedTestCases.length }} 条，跨页选择已自动保存
          </span>
        </div>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[15, 25, 35, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Download, Delete } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'
import * as XLSX from 'xlsx'

const { t } = useI18n()
const router = useRouter()
const loading = ref(false)
const testcases = ref([])
const projects = ref([])
const currentPage = ref(1)
const pageSize = ref(15)
const total = ref(0)
const searchText = ref('')
const projectFilter = ref('')
const priorityFilter = ref('')
const selectedTestCases = ref([])
const isDeleting = ref(false)
const tableRef = ref(null)
const selectAll = ref(false)
const allSelectedIds = ref(new Set())

const fetchTestCases = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchText.value,
      project: projectFilter.value,
      priority: priorityFilter.value
    }
    const response = await api.get('/testcases/', { params })
    testcases.value = response.data.results || []
    total.value = response.data.count || 0
    
    // 页面切换后恢复选中状态
    nextTick(() => {
      if (tableRef.value) {
        testcases.value.forEach(item => {
          if (allSelectedIds.value.has(item.id)) {
            tableRef.value.toggleRowSelection(item, true)
          }
        })
      }
    })
  } catch (error) {
    ElMessage.error(t('testcase.fetchListFailed'))
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  allSelectedIds.value.clear()
  selectAll.value = false
  fetchTestCases()
}

const handleFilter = () => {
  currentPage.value = 1
  allSelectedIds.value.clear()
  selectAll.value = false
  fetchTestCases()
}

const handlePageChange = () => {
  fetchTestCases()
}

const handleSizeChange = () => {
  currentPage.value = 1
  fetchTestCases()
}

const goToTestCase = (id) => {
  router.push(`/ai-generation/testcases/${id}`)
}

const editTestCase = (testcase) => {
  router.push(`/ai-generation/testcases/${testcase.id}/edit`)
}

const deleteTestCase = async (testcase) => {
  try {
    await ElMessageBox.confirm(t('testcase.deleteConfirm'), t('common.warning'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    })
    
    await api.delete(`/testcases/${testcase.id}/`)
    ElMessage.success(t('testcase.deleteSuccess'))
    fetchTestCases()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('testcase.deleteFailed'))
    }
  }
}

// 处理选择变化（支持跨页选择）
const handleSelectionChange = (selection) => {
  selectedTestCases.value = selection
  
  // 更新全局选中ID集合
  const currentPageIds = new Set(testcases.value.map(item => item.id))
  
  // 从全局集合中移除当前页未选中的项
  currentPageIds.forEach(id => {
    const isSelected = selection.some(item => item.id === id)
    if (!isSelected) {
      allSelectedIds.value.delete(id)
    }
  })
  
  // 添加当前页选中的项到全局集合
  selection.forEach(item => {
    allSelectedIds.value.add(item.id)
  })
  
  // 更新全选状态
  selectAll.value = allSelectedIds.value.size === total.value && total.value > 0
}

// 判断行是否可选（用于保持跨页选中状态）
const isSelectable = (row) => {
  return true
}

// 全选/取消全选
const handleSelectAll = async (event) => {
  if (event.target.checked) {
    // 全选：需要获取所有数据的ID
    if (total.value <= pageSize.value) {
      // 当前页就是全部数据
      testcases.value.forEach(item => {
        allSelectedIds.value.add(item.id)
      })
    } else {
      // 需要分批获取所有数据的ID
      try {
        const allIds = await fetchAllIds()
        allIds.forEach(id => {
          allSelectedIds.value.add(id)
        })
      } catch (error) {
        console.error('Fetch all IDs failed:', error)
        ElMessage.error('获取全部数据失败')
        event.target.checked = false
        return
      }
    }
    
    // 选中当前页的所有行
    nextTick(() => {
      if (tableRef.value) {
        testcases.value.forEach(item => {
          tableRef.value.toggleRowSelection(item, true)
        })
      }
    })
  } else {
    // 取消全选
    allSelectedIds.value.clear()
    nextTick(() => {
      if (tableRef.value) {
        tableRef.value.clearSelection()
      }
    })
  }
  
  // 更新选中列表显示
  selectedTestCases.value = testcases.value.filter(item => allSelectedIds.value.has(item.id))
}

// 分批获取所有数据的ID（用于全选功能）
const fetchAllIds = async () => {
  const allIds = []
  let page = 1
  const pageSizeForFetch = 100
  
  while (true) {
    const params = {
      page: page,
      page_size: pageSizeForFetch,
      search: searchText.value,
      project: projectFilter.value,
      priority: priorityFilter.value
    }
    
    const response = await api.get('/testcases/', { params })
    const results = response.data.results || []
    
    if (results.length === 0) break
    
    results.forEach(item => {
      if (item.id) {
        allIds.push(item.id)
      }
    })
    
    if (results.length < pageSizeForFetch) break
    page++
  }
  
  return allIds
}

// 获取序号
const getSerialNumber = (index) => {
  return (currentPage.value - 1) * pageSize.value + index + 1
}

// 批量删除（支持跨页选择）
const batchDeleteTestCases = async () => {
  if (allSelectedIds.value.size === 0) {
    ElMessage.warning(t('testcase.selectFirst'))
    return
  }

  try {
    await ElMessageBox.confirm(
      t('testcase.batchDeleteConfirm', { count: allSelectedIds.value.size }),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )

    isDeleting.value = true
    const ids = Array.from(allSelectedIds.value)
    
    try {
      // 使用批量删除接口
      await api.post('/testcases/batch-delete/', { ids })
      ElMessage.success(t('testcase.batchDeleteSuccess', { successCount: ids.length }))
    } catch (batchError) {
      // 如果批量删除失败，尝试逐个删除
      let successCount = 0
      let failCount = 0
      
      for (const id of ids) {
        try {
          await api.delete(`/testcases/${id}/`)
          successCount++
        } catch (error) {
          console.error(`Delete test case ${id} failed:`, error)
          failCount++
        }
      }

      if (successCount > 0) {
        if (failCount > 0) {
          ElMessage.success(t('testcase.batchDeletePartialSuccess', { successCount, failCount }))
        } else {
          ElMessage.success(t('testcase.batchDeleteSuccess', { successCount }))
        }
      } else {
        ElMessage.error(t('testcase.batchDeleteFailed'))
      }
    }

    // 清空选择并重新加载列表
    allSelectedIds.value.clear()
    selectAll.value = false
    selectedTestCases.value = []
    fetchTestCases()

  } catch (error) {
    if (error !== 'cancel') {
      console.error('Batch delete failed:', error)
      ElMessage.error(t('testcase.batchDeleteError') + ': ' + (error.message || t('common.error')))
    }
  } finally {
    isDeleting.value = false
  }
}

const getPriorityText = (priority) => {
  const textMap = {
    low: t('testcase.low'),
    medium: t('testcase.medium'),
    high: t('testcase.high'),
    critical: t('testcase.critical')
  }
  return textMap[priority] || priority
}

const getTypeText = (type) => {
  const textMap = {
    functional: t('testcase.functional'),
    integration: t('testcase.integration'),
    api: t('testcase.api'),
    ui: t('testcase.ui'),
    performance: t('testcase.performance'),
    security: t('testcase.security')
  }
  return textMap[type] || '-'
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

const getVersionsTooltip = (versions) => {
  return versions.map(v => v.name + (v.is_baseline ? ' (' + t('testcase.baseline') + ')' : '')).join('、')
}

// 将HTML的<br>标签转换为换行符（用于Excel导出）
const convertBrToNewline = (text) => {
  if (!text) return ''
  return text.replace(/<br\s*\/?>/gi, '\n')
}

const exportToExcel = async () => {
  try {
    loading.value = true

    // 确定要导出的数据
    let testCasesToExport = []

    if (selectedTestCases.value.length > 0) {
      // 如果有勾选，导出勾选的数据
      testCasesToExport = selectedTestCases.value
    } else {
      // 如果没有勾选，分页获取所有数据
      const pageSize = 100  // 使用后端允许的最大值
      let page = 1
      let hasMore = true
      let allData = []

      while (hasMore) {
        const response = await api.get('/testcases/', {
          params: {
            page: page,
            page_size: pageSize,
            search: searchText.value,
            project: projectFilter.value,
            priority: priorityFilter.value
          }
        })

        const results = response.data.results || []
        allData.push(...results)

        // 检查是否还有更多数据
        // 如果返回的数据少于pageSize，说明已经是最后一页
        if (results.length < pageSize) {
          hasMore = false
        } else {
          page++
        }
      }

      testCasesToExport = allData
    }

    if (testCasesToExport.length === 0) {
      ElMessage.warning(t('testcase.noDataToExport'))
      loading.value = false
      return
    }

    // 创建工作簿
    const workbook = XLSX.utils.book_new()

    // 准备Excel数据
    const worksheetData = [
      [t('testcase.excelNumber'), t('testcase.excelTitle'), t('testcase.excelProject'), t('testcase.excelVersions'), t('testcase.excelPreconditions'), t('testcase.excelSteps'), t('testcase.excelExpectedResult'), t('testcase.excelPriority'), t('testcase.excelTestType'), t('testcase.excelAuthor'), t('testcase.excelCreatedAt')]
    ]

    testCasesToExport.forEach((testcase, index) => {
      const versions = testcase.versions && testcase.versions.length > 0
        ? testcase.versions.map(v => v.name + (v.is_baseline ? '(' + t('testcase.baseline') + ')' : '')).join('、')
        : t('testcase.noVersion')

      worksheetData.push([
        `TC${String(index + 1).padStart(3, '0')}`,
        testcase.title || '',
        testcase.project?.name || '',
        versions,
        convertBrToNewline(testcase.preconditions || ''),
        convertBrToNewline(testcase.steps || ''),
        convertBrToNewline(testcase.expected_result || ''),
        getPriorityText(testcase.priority),
        getTypeText(testcase.test_type),
        testcase.author?.username || '',
        formatDate(testcase.created_at)
      ])
    })
    
    // 创建工作表
    const worksheet = XLSX.utils.aoa_to_sheet(worksheetData)
    
    // 设置列宽
    const colWidths = [
      { wch: 15 }, // Test case number
      { wch: 30 }, // Case title
      { wch: 20 }, // Related project
      { wch: 25 }, // Related versions
      { wch: 30 }, // Preconditions
      { wch: 40 }, // Steps
      { wch: 30 }, // Expected result
      { wch: 10 }, // Priority
      { wch: 15 }, // Test type
      { wch: 15 }, // Author
      { wch: 20 }  // Created at
    ]
    worksheet['!cols'] = colWidths
    
    // 设置表头样式
    for (let col = 0; col < worksheetData[0].length; col++) {
      const cellAddress = XLSX.utils.encode_cell({ r: 0, c: col })
      if (!worksheet[cellAddress]) continue
      worksheet[cellAddress].s = {
        font: { bold: true },
        alignment: { horizontal: 'center', vertical: 'center', wrapText: true }
      }
    }
    
    // 设置其他行的样式
    for (let row = 1; row < worksheetData.length; row++) {
      for (let col = 0; col < worksheetData[row].length; col++) {
        const cellAddress = XLSX.utils.encode_cell({ r: row, c: col })
        if (worksheet[cellAddress]) {
          worksheet[cellAddress].s = {
            alignment: { vertical: 'top', wrapText: true }
          }
        }
      }
    }

    // Add worksheet to workbook
    XLSX.utils.book_append_sheet(workbook, worksheet, t('testcase.excelSheetName'))

    // Generate filename
    const fileName = t('testcase.excelFileName', { date: new Date().toISOString().slice(0, 10) })

    // Export file
    XLSX.writeFile(workbook, fileName)

    ElMessage.success(t('testcase.exportSuccess'))
  } catch (error) {
    console.error('Export test cases failed:', error)
    ElMessage.error(t('testcase.exportFailed') + ': ' + (error.message || t('common.error')))
  } finally {
    loading.value = false
  }
}

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error(t('testcase.fetchProjectsFailed'))
  }
}

onMounted(() => {
  fetchProjects()
  fetchTestCases()
})
</script>

<style lang="scss" scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-shrink: 0;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.card-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.filter-bar {
  padding: 20px;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}

.table-container {
  flex: 1;
  overflow: hidden;
  padding: 0 20px;
  
  :deep(.el-table) {
    height: 100% !important;
  }
  
  :deep(.el-table__body-wrapper) {
    overflow-y: auto !important;
  }
}

.pagination-container {
  padding: 15px 20px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 15px;
}

.select-all-info {
  display: flex;
  align-items: center;
  gap: 15px;
  
  .el-checkbox {
    display: flex;
    align-items: center;
    gap: 6px;
    
    input[type="checkbox"] {
      width: 18px;
      height: 18px;
      cursor: pointer;
    }
    
    .el-checkbox__label {
      font-size: 14px;
      color: #606266;
      cursor: pointer;
    }
  }
  
  .selected-info {
    font-size: 13px;
    color: #409eff;
    background: #ecf5ff;
    padding: 4px 12px;
    border-radius: 4px;
  }
}

.priority-tag {
  &.low { color: #67c23a; }
  &.medium { color: #e6a23c; }
  &.high { color: #f56c6c; }
  &.critical { color: #f56c6c; font-weight: bold; }
}

.version-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  
  .version-tag {
    margin: 0;
  }
}

.no-version {
  color: #909399;
  font-size: 12px;
  font-style: italic;
}

@media (max-width: 1200px) {
  .page-container {
    height: auto;
    min-height: 100vh;
    overflow-y: auto;
  }
  
  .card-container {
    min-height: 600px;
  }
  
  .table-container {
    min-height: 400px;
  }
}

@media (max-width: 768px) {
  .page-container {
    padding: 10px;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }
  
  .header-actions {
    width: 100%;
  }
  
  .filter-bar {
    padding: 15px;
  }
  
  .pagination-container {
    padding: 15px;
  }
}

.step-content {
  min-height: 200px;
}

.preview-info {
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;

  p {
    margin: 5px 0;
  }
}
</style>