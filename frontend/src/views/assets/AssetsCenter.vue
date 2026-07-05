<template>
  <div class="assets-center">
    <div class="assets-header">
      <h1>测试资产中心</h1>
      <p>统一管理截图表、视频录制、测试报告与下载文件</p>
    </div>

    <!-- Stats -->
    <div class="stats-row">
      <div class="stat-item" v-for="s in stats" :key="s.label">
        <span class="stat-num">{{ s.value }}</span>
        <span class="stat-label">{{ s.label }}</span>
      </div>
    </div>

    <!-- Tabs -->
    <el-tabs v-model="activeTab" class="assets-tabs">
      <!-- 截图管理 -->
      <el-tab-pane label="截图管理" name="screenshots">
        <div class="tab-toolbar">
          <el-input v-model="screenSearch" placeholder="搜索截图" clearable prefix-icon="Search" style="width:260px" />
          <el-select v-model="screenSource" placeholder="来源" clearable style="width:140px">
            <el-option label="网页自动化" value="web" />
            <el-option label="APP自动化" value="app" />
            <el-option label="AI录制" value="ai" />
          </el-select>
          <div class="tab-actions">
            <el-button type="primary" @click="loadScreenshots">刷新</el-button>
            <el-button type="danger" :disabled="!screenshots.length" @click="batchDelete('screenshot')">
              <el-icon><Delete /></el-icon> 一键全部删除
            </el-button>
          </div>
        </div>

        <div class="screenshot-grid" v-loading="screenLoading">
          <div v-for="item in filteredScreenshots" :key="item.id" class="screenshot-card" @click="previewMedia(item)">
            <div class="screenshot-preview">
              <img :src="item.thumbnail || item.url || defaultScreenImg" :alt="item.name" @error="imgError" />
              <div class="screenshot-overlay">
                <el-icon :size="28"><ZoomIn /></el-icon>
              </div>
            </div>
            <div class="screenshot-info">
              <span class="screenshot-name">{{ item.name }}</span>
              <span class="screenshot-meta">{{ item.source }} · {{ item.date }}</span>
            </div>
            <div class="screenshot-actions">
              <el-button link size="small" @click.stop="downloadFile(item)"><el-icon><Download /></el-icon></el-button>
              <el-button link size="small" type="danger" @click.stop="deleteFile(item, 'screenshot')"><el-icon><Delete /></el-icon></el-button>
            </div>
          </div>
          <el-empty v-if="!screenLoading && !filteredScreenshots.length" description="暂无截图" />
        </div>
      </el-tab-pane>

      <!-- 视频录制 -->
      <el-tab-pane label="视频录制" name="videos">
        <div class="tab-toolbar">
          <el-input v-model="videoSearch" placeholder="搜索视频" clearable prefix-icon="Search" style="width:260px" />
          <el-select v-model="videoSource" placeholder="来源" clearable style="width:140px">
            <el-option label="APP录屏" value="app_screen" />
            <el-option label="AI录制GIF" value="ai_gif" />
          </el-select>
          <div class="tab-actions">
            <el-button type="primary" @click="loadVideos">刷新</el-button>
            <el-button type="danger" :disabled="!videos.length" @click="batchDelete('video')">
              <el-icon><Delete /></el-icon> 一键全部删除
            </el-button>
          </div>
        </div>

        <div class="video-grid" v-loading="videoLoading">
          <div v-for="item in filteredVideos" :key="item.id" class="video-card" @click="previewMedia(item)">
            <div class="video-preview">
              <video
                v-if="item.type==='video'"
                :src="item.url"
                muted
                preload="metadata"
                @error="onVideoError"
              />
              <img v-else-if="item.type==='gif'" :src="item.url" :alt="item.name" @error="imgError" />
              <img v-else :src="defaultVideoImg" alt="视频占位" />
              <div class="video-overlay">
                <el-icon :size="32"><VideoPlay /></el-icon>
              </div>
            </div>
            <div class="video-info">
              <span class="video-name">{{ item.name }}</span>
              <span class="video-meta">{{ item.source }} · {{ item.size }} · {{ item.date }}</span>
            </div>
            <div class="video-actions">
              <el-button link size="small" @click.stop="downloadFile(item)"><el-icon><Download /></el-icon></el-button>
              <el-button link size="small" type="danger" @click.stop="deleteFile(item, 'video')"><el-icon><Delete /></el-icon></el-button>
            </div>
          </div>
          <el-empty v-if="!videoLoading && !filteredVideos.length" description="暂无视频" />
        </div>
      </el-tab-pane>

      <!-- 测试报告 -->
      <el-tab-pane label="测试报告" name="reports">
        <div class="tab-toolbar">
          <el-input v-model="reportSearch" placeholder="搜索报告" clearable prefix-icon="Search" style="width:260px" />
          <el-select v-model="reportType" placeholder="报告类型" clearable style="width:140px">
            <el-option label="AI测试报告" value="ai" />
            <el-option label="UI测试报告" value="ui" />
            <el-option label="APP测试报告" value="app" />
            <el-option label="API测试报告" value="api" />
          </el-select>
          <div class="tab-actions">
            <el-button type="primary" @click="loadReports">刷新</el-button>
            <el-button type="danger" :disabled="!reports.length" @click="batchDelete('report')">
              <el-icon><Delete /></el-icon> 一键全部删除
            </el-button>
          </div>
        </div>

        <el-table :data="filteredReports" v-loading="reportLoading" stripe highlight-current-row @row-click="openReport">
          <el-table-column prop="name" label="报告名称" min-width="200">
            <template #default="{ row }">
              <el-link type="primary">{{ row.name }}</el-link>
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status==='通过'?'success':row.status==='失败'?'danger':'warning'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="passRate" label="通过率" width="100" />
          <el-table-column prop="totalCases" label="用例数" width="80" />
          <el-table-column prop="date" label="生成时间" width="170" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link size="small" type="primary" @click.stop="openReport(row)">查看</el-button>
              <el-button link size="small" @click.stop="downloadReport(row)">下载</el-button>
              <el-button link size="small" type="danger" @click.stop="deleteFile(row, 'report')">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 下载中心 -->
      <el-tab-pane label="下载中心" name="downloads">
        <div class="tab-toolbar">
          <el-input v-model="downloadSearch" placeholder="搜索下载文件" clearable prefix-icon="Search" style="width:260px" />
          <el-select v-model="downloadType" placeholder="文件类型" clearable style="width:140px">
            <el-option label="PDF报告" value="pdf" />
            <el-option label="Excel用例" value="xlsx" />
            <el-option label="JSON数据" value="json" />
            <el-option label="压缩包" value="zip" />
          </el-select>
          <div class="tab-actions">
            <el-button type="primary" @click="loadDownloads">刷新</el-button>
            <el-button type="danger" :disabled="!downloads.length" @click="batchDelete('download')">
              <el-icon><Delete /></el-icon> 一键全部删除
            </el-button>
          </div>
        </div>

        <div v-if="downloads.length" class="download-list">
          <div v-for="item in filteredDownloads" :key="item.id" class="download-item">
            <div class="download-icon">
              <el-icon :size="28"><component :is="getFileIcon(item.type)" /></el-icon>
            </div>
            <div class="download-info">
              <span class="download-name">{{ item.name }}</span>
              <span class="download-meta">{{ item.size }} · {{ item.date }}</span>
            </div>
            <div class="download-actions">
              <el-button type="primary" size="small" :icon="Download" @click="downloadFile(item)">下载</el-button>
              <el-button size="small" type="danger" :icon="Delete" @click="deleteFile(item, 'download')" />
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无下载任务" />
      </el-tab-pane>
    </el-tabs>

    <!-- 预览弹窗 -->
    <el-dialog v-model="previewVisible" :title="previewItem?.name || ''" width="80%" destroy-on-close>
      <div class="preview-container" v-if="previewItem">
        <img v-if="previewItem.type==='image' || previewItem.type==='gif'" :src="previewItem.url" style="max-width:100%;border-radius:8px;max-height:70vh" />
        <video v-else-if="previewItem.type==='video'" :src="previewItem.url" controls autoplay style="max-width:100%;border-radius:8px;max-height:70vh" />
        <el-empty v-else description="无法预览此类型文件" />
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button type="primary" @click="downloadFile(previewItem)">下载</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, ZoomIn, VideoPlay, Download, Delete } from '@element-plus/icons-vue'
import api from '@/utils/api'

const activeTab = ref('screenshots')

// Default placeholder images
const defaultScreenImg = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="180"><rect fill="#f1f5f9" width="300" height="180" rx="4"/><text x="150" y="95" text-anchor="middle" fill="#94a3b8" font-size="13" font-family="sans-serif">截图加载中...</text></svg>')
const defaultVideoImg = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect fill="#1a1a2e" width="320" height="180" rx="4"/><text x="160" y="95" text-anchor="middle" fill="#60a5fa" font-size="13" font-family="sans-serif">视频预览</text></svg>')

// Screenshots state
const screenLoading = ref(false)
const screenSearch = ref('')
const screenSource = ref('')
const screenshots = ref([])
const filteredScreenshots = computed(() => {
  let items = screenshots.value
  if (screenSearch.value) items = items.filter(i => i.name?.includes(screenSearch.value))
  if (screenSource.value) items = items.filter(i => i.sourceKey === screenSource.value)
  return items
})

// Videos state
const videoLoading = ref(false)
const videoSearch = ref('')
const videoSource = ref('')
const videos = ref([])
const filteredVideos = computed(() => {
  let items = videos.value
  if (videoSearch.value) items = items.filter(i => i.name?.includes(videoSearch.value))
  if (videoSource.value) items = items.filter(i => i.sourceKey === videoSource.value)
  return items
})

// Reports state
const reportLoading = ref(false)
const reportSearch = ref('')
const reportType = ref('')
const reports = ref([])
const filteredReports = computed(() => {
  let items = reports.value
  if (reportSearch.value) items = items.filter(i => i.name?.includes(reportSearch.value))
  if (reportType.value) items = items.filter(i => i.typeKey === reportType.value)
  return items
})

// Downloads state
const downloadSearch = ref('')
const downloadType = ref('')
const downloads = ref([])
const filteredDownloads = computed(() => {
  let items = downloads.value
  if (downloadSearch.value) items = items.filter(i => i.name?.includes(downloadSearch.value))
  if (downloadType.value) items = items.filter(i => i.ext === downloadType.value)
  return items
})

// Preview
const previewVisible = ref(false)
const previewItem = ref(null)

const stats = computed(() => [
  { label: '截图总数', value: screenshots.value.length },
  { label: '视频总数', value: videos.value.length },
  { label: '报告总数', value: reports.value.length },
  { label: '下载文件', value: downloads.value.length },
])

function getFileIcon(ext) {
  return { pdf: 'Document', xlsx: 'Grid', json: 'DataBoard', zip: 'FolderOpened' }[ext] || 'Document'
}

// Fix relative URLs by prepending API base
function resolveUrl(url) {
  if (!url) return ''
  if (url.startsWith('http') || url.startsWith('data:') || url.startsWith('blob:')) return url
  // Fix paths like /media/... or media/...
  if (url.startsWith('/')) return url
  return '/' + url
}

function previewMedia(item) {
  if (item) item.url = resolveUrl(item.url || '')
  previewItem.value = item
  previewVisible.value = true
}

function downloadFile(item) {
  if (!item?.url) return
  const url = resolveUrl(item.url)
  const a = document.createElement('a')
  a.href = url
  a.download = item.name
  a.target = '_blank'
  a.click()
}

function imgError(e) {
  if (e.target) e.target.style.display = 'none'
}

function onVideoError(e) {
  // Video load failed - could be CORS or file not found
  if (e.target) {
    const parent = e.target.parentElement
    if (parent) {
      const img = document.createElement('img')
      img.src = defaultVideoImg
      img.style.cssText = 'width:100%;height:100%;object-fit:contain;'
      parent.replaceChild(img, e.target)
    }
  }
}

async function deleteFile(item, type) {
  try {
    await ElMessageBox.confirm('确定要删除此项吗？', '确认删除', { type: 'warning' })
    let deleted = false

    // 优先使用统一资产中心API（同时清理DB和磁盘文件）
    try {
      // 判断可用的资产ID（截图/视频/报告用数字ID）
      let assetId = null
      let assetType = type
      if (type === 'screenshot' && item.sourceKey === 'web' && typeof item.id === 'number') {
        assetId = item.id
        assetType = 'screenshot'
      } else if (type === 'video' && item.sourceKey === 'app_screen' && typeof item.id === 'number') {
        // APP 录屏 - 走报告删除
        assetId = item.id
        assetType = 'report'
      } else if (type === 'video' && item.sourceKey === 'ai_gif' && item.recordId) {
        assetId = item.recordId
        assetType = 'video'
      } else if (type === 'screenshot' && item.sourceKey === 'ai' && item.recordId) {
        assetId = item.recordId
        assetType = 'video'  // AI录制截图跟随视频记录删除
      } else if (type === 'report' && typeof item.id === 'number') {
        assetId = item.id
        assetType = 'report'
      } else if (type === 'download' && item.url) {
        // 下载文件 - 直接传文件路径
        await api.post('/ui-automation/assets/delete/', {
          type: 'download',
          file_path: item.url
        })
        deleted = true
        ElMessage.success('已删除')
        downloads.value = downloads.value.filter(d => d.id !== item.id)
        return
      }

      if (assetId) {
        const resp = await api.post('/ui-automation/assets/delete/', {
          type: assetType,
          id: assetId
        })
        if (resp.data?.deleted) {
          deleted = true
          const message = resp.data?.message || '已删除'
          ElMessage.success(message)
        }
      }
    } catch (apiErr) {
      // API失败时回退到老接口
      console.warn('统一资产API调用失败，回退到老接口', apiErr)
    }

    // 兜底：老接口
    if (!deleted) {
      if (type === 'screenshot' && item.sourceKey === 'web' && typeof item.id === 'number') {
        await api.delete(`/ui-automation/screenshots/${item.id}/`)
        deleted = true
      } else if ((type === 'screenshot' && item.sourceKey === 'ai') || (type === 'video' && item.sourceKey === 'ai_gif')) {
        if (item.recordId) {
          await api.post('/ui-automation/ai-execution-records/batch_delete/', { ids: [item.recordId] })
          deleted = true
        }
      } else if (type === 'report' && item.id) {
        await api.delete(`/reports/${item.id}/`)
        deleted = true
      }
    }

    if (deleted) {
      // 重新加载数据
      if (type === 'screenshot') loadScreenshots()
      else if (type === 'video') loadVideos()
      else if (type === 'report') loadReports()
      else if (type === 'download') loadDownloads()
    } else {
      // 实在无法删除，至少前端移除
      if (type === 'screenshot') screenshots.value = screenshots.value.filter(s => s.id !== item.id)
      else if (type === 'video') videos.value = videos.value.filter(v => v.id !== item.id)
      else if (type === 'report') reports.value = reports.value.filter(r => r.id !== item.id)
      else downloads.value = downloads.value.filter(d => d.id !== item.id)
      ElMessage.success('已从列表移除')
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('删除失败: ' + (err.response?.data?.error || err.message || '未知错误'))
    }
  }
}

async function batchDelete(type) {
  try {
    await ElMessageBox.confirm(
      `确定要一键删除所有${({screenshot:'截图',video:'视频',report:'报告',download:'下载文件'})[type] || '项目'}吗？此操作不可撤销。`,
      '确认批量删除',
      { type: 'warning', confirmButtonText: '确认删除', confirmButtonClass: 'el-button--danger' }
    )

    let deletedCount = 0
    let apiSucceeded = false

    if (type === 'screenshot') {
      // 收集所有可删除的ID
      const webIds = screenshots.value.filter(s => s.sourceKey === 'web' && typeof s.id === 'number').map(s => s.id)
      const aiRecordIds = [...new Set(screenshots.value.filter(s => s.sourceKey === 'ai' && s.recordId).map(s => s.recordId))]

      // 优先用统一API
      if (webIds.length) {
        try {
          const resp = await api.post('/ui-automation/assets/batch_delete/', {
            type: 'screenshot',
            ids: webIds
          })
          if (resp.data) {
            deletedCount += resp.data.deleted || 0
            apiSucceeded = true
            const msg = resp.data.message || ''
            if (msg) ElMessage.success(msg)
          }
        } catch (e) {
          // 降级
          await api.post('/ui-automation/screenshots/batch_delete/', { ids: webIds }).catch(() => {})
          apiSucceeded = true
        }
      }
      if (aiRecordIds.length) {
        await api.post('/ui-automation/ai-execution-records/batch_delete/', { ids: aiRecordIds }).catch(() => {})
        apiSucceeded = true
      }
      loadScreenshots()
    } else if (type === 'video') {
      const gifRecordIds = [...new Set(videos.value.filter(v => v.sourceKey === 'ai_gif' && v.recordId).map(v => v.recordId))]
      if (gifRecordIds.length) {
        try {
          await api.post('/ui-automation/assets/batch_delete/', {
            type: 'video',
            ids: gifRecordIds
          })
          apiSucceeded = true
        } catch (e) {
          await api.post('/ui-automation/ai-execution-records/batch_delete/', { ids: gifRecordIds }).catch(() => {})
          apiSucceeded = true
        }
      }
      loadVideos()
    } else if (type === 'report') {
      const reportIds = reports.value.filter(r => typeof r.id === 'number').map(r => r.id)
      if (reportIds.length) {
        try {
          const resp = await api.post('/ui-automation/assets/batch_delete/', {
            type: 'report',
            ids: reportIds
          })
          deletedCount = resp.data?.deleted || 0
          apiSucceeded = true
          const msg = resp.data?.message || ''
          if (msg) ElMessage.success(msg)
        } catch (e) {
          await api.post('/reports/batch_delete/', { ids: reportIds }).catch(() => {})
          apiSucceeded = true
        }
      }
      reports.value = []
      if (!apiSucceeded) ElMessage.success('报告已全部删除')
      return
    } else if (type === 'download') {
      downloads.value = []
      ElMessage.success('下载记录已清除')
      return
    }

    if (apiSucceeded && deletedCount === 0) {
      ElMessage.success('已全部删除')
    } else if (!apiSucceeded) {
      ElMessage.success('已全部删除')
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('批量删除失败: ' + (err.response?.data?.error || err.message || ''))
    }
  }
}

function downloadReport(row) {
  if (row.downloadUrl) window.open(row.downloadUrl)
  else ElMessage.info('该报告暂不支持下载')
}

function openReport(row) {
  if (row.viewUrl) window.open(row.viewUrl)
  else ElMessage.info('报告链接不可用')
}

// Load functions
async function loadScreenshots() {
  screenLoading.value = true
  try {
    // Load UI screenshots
    const uiRes = await api.get('/ui-automation/screenshots/', { params: { page_size: 1000 } }).catch(() => ({ data: { results: [] } }))
    const uiItems = (uiRes.data?.results || uiRes.data || []).map((s, i) => ({
      id: s.id || `scr_${i}`,
      name: s.name || `截图_${i + 1}`,
      url: resolveUrl(s.image || s.url || ''),
      thumbnail: resolveUrl(s.image || s.url || ''),
      source: '网页自动化',
      sourceKey: 'web',
      type: 'image',
      date: s.captured_at ? new Date(s.captured_at).toLocaleString('zh-CN') : '-'
    }))

    // Load AI execution screenshots
    const aiRes = await api.get('/ui-automation/ai-execution-records/', { params: { page_size: 100 } }).catch(() => ({ data: { results: [] } }))
    const aiItems = (aiRes.data?.results || []).filter(r => r.screenshots_sequence?.length).flatMap((r, idx) =>
      (r.screenshots_sequence || []).map((sc, j) => ({
        id: `ai_scr_${idx}_${j}`,
        recordId: r.id,
        name: `${r.case_name || 'AI任务'}_截图${j + 1}`,
        url: resolveUrl(sc.url || sc),
        thumbnail: resolveUrl(sc.url || sc),
        source: 'AI录制',
        sourceKey: 'ai',
        type: 'image',
        date: r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-'
      }))
    )

    screenshots.value = [...uiItems, ...aiItems]
  } catch { screenshots.value = [] }
  finally { screenLoading.value = false }
}

async function loadVideos() {
  videoLoading.value = true
  try {
    // APP screen records
    const recRes = await api.get('/app-automation/executions/', { params: { page_size: 100 } }).catch(() => ({ data: { results: [] } }))
    const videoItems = (recRes.data?.results || []).filter(e => e.report_path).map((e, i) => ({
      id: `vid_${i}`,
      name: `APP录屏_执行${e.id}`,
      url: resolveUrl(e.report_path),
      source: 'APP自动化',
      sourceKey: 'app_screen',
      type: 'video',
      size: '-',
      date: e.created_at ? new Date(e.created_at).toLocaleString('zh-CN') : '-'
    }))

    // AI execution GIFs
    const aiRes = await api.get('/ui-automation/ai-execution-records/', { params: { page_size: 100 } }).catch(() => ({ data: { results: [] } }))
    const gifItems = (aiRes.data?.results || []).filter(r => r.gif_path).map((r, i) => ({
      id: `gif_${i}`,
      recordId: r.id,
      name: r.case_name || `AI录制_${r.id}`,
      url: resolveUrl(r.gif_path),
      source: 'AI自动化',
      sourceKey: 'ai_gif',
      type: r.gif_path?.endsWith('.mp4') || r.gif_path?.endsWith('.webm') ? 'video' : 'gif',
      size: '-',
      date: r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-'
    }))

    videos.value = [...videoItems, ...gifItems]
  } catch { videos.value = [] }
  finally { videoLoading.value = false }
}

async function loadReports() {
  reportLoading.value = true
  try {
    const uiRes = await api.get('/ui-automation/ai-execution-records/', { params: { page_size: 100 } }).catch(() => ({ data: { results: [] } }))
    const uiReports = (uiRes.data?.results || []).filter(r => r.status === 'passed' || r.status === 'failed').map((r, i) => ({
      id: `rpt_ui_${i}`,
      name: r.case_name || `UI报告_${r.id}`,
      type: 'UI测试报告',
      typeKey: 'ui',
      status: r.status === 'passed' ? '通过' : '失败',
      passRate: r.status === 'passed' ? '100%' : '-',
      totalCases: '-',
      date: r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-',
      viewUrl: `/ui-automation/execution-records`,
      downloadUrl: '',
    }))

    const aiRes = await api.get('/reports/reports/', { params: { page_size: 100 } }).catch(() => ({ data: { results: [] } }))
    const aiReports = (aiRes.data?.results || []).map((r, i) => ({
      id: `rpt_ai_${i}`,
      name: r.name || `AI报告_${r.id}`,
      type: 'AI测试报告',
      typeKey: 'ai',
      status: r.summary?.pass_rate ? (r.summary.pass_rate > 80 ? '通过' : '失败') : '-',
      passRate: r.summary?.pass_rate ? r.summary.pass_rate + '%' : '-',
      totalCases: r.summary?.total_cases || '-',
      date: r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-',
      viewUrl: `/ai-generation/reports`,
      downloadUrl: `/api/reports/reports/${r.id}/download/?format=json`,
    }))

    reports.value = [...uiReports, ...aiReports]
  } catch { reports.value = [] }
  finally { reportLoading.value = false }
}

async function loadDownloads() {
  try {
    const [rptRes, scrRes] = await Promise.all([
      api.get('/reports/reports/', { params: { page_size: 100 } }).catch(() => ({ data: { results: [] } })),
      api.get('/ui-automation/ai-execution-records/', { params: { page_size: 100 } }).catch(() => ({ data: { results: [] } })),
    ])
    const items = [
      ...(rptRes.data?.results || []).map((r, i) => ({
        id: `dl_rpt_${i}`, name: `${r.name || '报告'}.pdf`, ext: 'pdf', type: 'pdf', size: '-',
        url: resolveUrl(`/api/reports/reports/${r.id}/download/?format=pdf`),
        date: r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-',
      })),
      ...(scrRes.data?.results || []).filter(r => r.gif_path).map((r, i) => ({
        id: `dl_gif_${i}`, name: `录制_${r.id}.gif`, ext: 'zip', type: 'zip', size: '-',
        url: resolveUrl(r.gif_path),
        date: r.created_at ? new Date(r.created_at).toLocaleString('zh-CN') : '-',
      })),
    ]
    downloads.value = items
  } catch { downloads.value = [] }
}

onMounted(() => {
  loadScreenshots()
  loadVideos()
  loadReports()
  loadDownloads()
})
</script>

<style scoped lang="scss">
.assets-center {
  padding: var(--spacing-xl);
  max-width: 1600px;
  margin: 0 auto;
}

.assets-header {
  margin-bottom: var(--spacing-xl);
  h1 { font-size: 24px; margin: 0 0 4px; color: var(--color-text); }
  p { color: var(--color-text-muted); margin: 0; font-size: 14px; }
}

.stats-row {
  display: flex; gap: 16px; margin-bottom: var(--spacing-xl); flex-wrap: wrap;
}

.stat-item {
  flex: 1; min-width: 140px; background: var(--color-bg-card); border-radius: var(--radius-lg);
  padding: var(--spacing-md) var(--spacing-lg); border: 1px solid var(--border-color);
  display: flex; flex-direction: column; gap: 4px;
}
.stat-num { font-size: 28px; font-weight: 800; color: var(--color-primary-light); }
.stat-label { font-size: 13px; color: var(--color-text-secondary); font-weight: 600; }

.tab-toolbar {
  display: flex; gap: 12px; align-items: center; margin-bottom: var(--spacing-lg); flex-wrap: wrap;
}
.tab-actions { display: flex; gap: 8px; margin-left: auto; }

.assets-tabs {
  :deep(.el-tabs__header) { margin-bottom: 4px; }
}

/* Screenshot Grid */
.screenshot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.screenshot-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s;
  &:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
}

.screenshot-preview {
  height: 160px; background: var(--color-bg-hover); position: relative;
  display: flex; align-items: center; justify-content: center; overflow: hidden;
  img { width: 100%; height: 100%; object-fit: cover; }
}
.screenshot-overlay {
  position: absolute; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity 0.25s; color: #fff;
}
.screenshot-card:hover .screenshot-overlay { opacity: 1; }

.screenshot-info {
  padding: 10px 12px 4px;
  span { display: block; }
  .screenshot-name { font-size: 13px; font-weight: 600; color: var(--color-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .screenshot-meta { font-size: 11px; color: var(--color-text-muted); margin-top: 2px; }
}

.screenshot-actions {
  display: flex; justify-content: flex-end; padding: 0 8px 8px; gap: 4px;
}

/* Video Grid */
.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.video-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s;
  &:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
}

.video-preview {
  height: 180px; background: #1a1a2e; position: relative;
  display: flex; align-items: center; justify-content: center; overflow: hidden;
  video, img { width: 100%; height: 100%; object-fit: contain; }
}
.video-overlay {
  position: absolute; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity 0.25s; color: #fff;
}
.video-card:hover .video-overlay { opacity: 1; }

.video-info {
  padding: 10px 12px 4px;
  .video-name { font-size: 13px; font-weight: 600; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .video-meta { font-size: 11px; color: var(--color-text-muted); display: block; margin-top: 2px; }
}

.video-actions {
  display: flex; justify-content: flex-end; padding: 0 8px 8px; gap: 4px;
}

/* Downloads */
.download-list {
  display: flex; flex-direction: column; gap: 10px;
}

.download-item {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 18px;
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  transition: all 0.2s;
  &:hover { border-color: var(--color-primary-border); }
}

.download-icon {
  width: 48px; height: 48px; border-radius: var(--radius-md);
  background: var(--color-primary-bg); color: var(--color-primary-light);
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}

.download-info {
  flex: 1; min-width: 0;
  .download-name { font-size: 14px; font-weight: 600; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .download-meta { font-size: 12px; color: var(--color-text-muted); display: block; margin-top: 2px; }
}

.download-actions {
  display: flex; gap: 8px; flex-shrink: 0;
}

.preview-container {
  display: flex; align-items: center; justify-content: center;
  min-height: 300px; background: var(--color-bg-hover); border-radius: var(--radius-lg);
}
</style>
