<template>
  <div class="page-container">
    <!-- 数据概览 -->
    <div class="stats-section">
      <el-row :gutter="16">
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-icon bg-blue"><el-icon><Folder /></el-icon></div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.project_count || '-' }}</div>
              <div class="stat-label">{{ $t('uiAutomation.dashboard.uiTestProjects') }}</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-icon bg-green"><el-icon><Document /></el-icon></div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.test_case_count || '-' }}</div>
              <div class="stat-label">{{ $t('uiAutomation.dashboard.testCases') }}</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-icon bg-purple"><el-icon><Collection /></el-icon></div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.suite_count || '-' }}</div>
              <div class="stat-label">{{ $t('uiAutomation.dashboard.testSuites') }}</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-icon bg-orange"><el-icon><RefreshRight /></el-icon></div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.execution_count || '-' }}</div>
              <div class="stat-label">{{ $t('uiAutomation.dashboard.testExecutions') }}</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 快速入口 -->
    <div class="section-header">快速入口</div>
    <div class="quick-grid">
      <div class="quick-card" @click="router.push('/ui-automation/full-auto')">
        <div class="quick-icon accent-blue"><el-icon :size="24"><MagicStick /></el-icon></div>
        <span>全自动测试</span>
        <small>AI 自动执行网页任务</small>
      </div>
      <div class="quick-card" @click="router.push('/ui-automation/case-based')">
        <div class="quick-icon accent-green"><el-icon :size="24"><Document /></el-icon></div>
        <span>用例驱动测试</span>
        <small>运行已有 AI 用例</small>
      </div>
      <div class="quick-card" @click="router.push('/ui-automation/execution-records')">
        <div class="quick-icon accent-amber"><el-icon :size="24"><Timer /></el-icon></div>
        <span>执行记录</span>
        <small>查看历史执行结果</small>
      </div>
      <div class="quick-card" @click="router.push('/ui-automation/reports')">
        <div class="quick-icon accent-indigo"><el-icon :size="24"><DataAnalysis /></el-icon></div>
        <span>测试报告</span>
        <small>查看分析报告</small>
      </div>
      <div class="quick-card" @click="router.push('/ui-automation/assets')">
        <div class="quick-icon accent-rose"><el-icon :size="24"><PictureFilled /></el-icon></div>
        <span>截图&amp;视频</span>
        <small>管理执行截图和回放</small>
      </div>
    </div>

    <!-- 最近执行 -->
    <div class="section-header">最近执行</div>
    <div class="recent-section" v-loading="loading">
      <template v-if="recentRecords.length">
        <div class="recent-list">
          <div v-for="rec in recentRecords" :key="rec.id" class="recent-item" @click="router.push('/ui-automation/execution-records')">
            <el-tag :type="statusType(rec.status)" size="small" effect="dark">{{ statusLabel(rec.status) }}</el-tag>
            <span class="recent-name">{{ rec.case_name || '未命名任务' }}</span>
            <span class="recent-time">{{ formatTime(rec.start_time || rec.created_at) }}</span>
          </div>
        </div>
      </template>
      <el-empty v-else description="暂无执行记录，去运行一个测试吧" :image-size="80">
        <el-button type="primary" @click="router.push('/ui-automation/full-auto')">开始测试</el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  Document, Collection, RefreshRight,
  MagicStick, Folder, Timer, DataAnalysis, PictureFilled
} from '@element-plus/icons-vue'
import {
  getDashboardStats,
  getAIExecutionRecords
} from '@/api/ui_automation'

const router = useRouter()
const { t } = useI18n()
const loading = ref(false)
const stats = reactive({
  project_count: null,
  test_case_count: null,
  suite_count: null,
  execution_count: null
})
const recentRecords = ref([])

const statusType = (s) => {
  if (s === 'running') return 'warning'
  if (s === 'passed' || s === 'completed') return 'success'
  if (s === 'failed' || s === 'error') return 'danger'
  return 'info'
}
const statusLabel = (s) => {
  const map = { running: '运行中', passed: '通过', completed: '完成', failed: '失败', error: '错误', stopped: '已停止' }
  return map[s] || s || '-'
}
const formatTime = (str) => {
  if (!str) return ''
  const d = new Date(str)
  const now = new Date()
  const diff = Math.floor((now - d) / 60000)
  if (diff < 1) return '刚刚'
  if (diff < 60) return `${diff}分钟前`
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const loadData = async () => {
  loading.value = true
  try {
    const [statsRes, recRes] = await Promise.all([
      getDashboardStats(),
      getAIExecutionRecords({ page_size: 5, ordering: '-start_time' })
    ])
    if (statsRes?.data) {
      stats.project_count = statsRes.data.project_count ?? null
      stats.test_case_count = statsRes.data.test_case_count ?? null
      stats.suite_count = statsRes.data.suite_count ?? null
      stats.execution_count = statsRes.data.execution_count ?? null
    }
    recentRecords.value = recRes?.data?.results || recRes?.data || []
  } catch {
    // 静默失败，显示空状态
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadData() })
</script>

<style scoped>
.page-container { padding: 0; }

/* --- Stats --- */
.stats-section { margin-bottom: 24px; }
.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  background: var(--color-bg-card);
  box-shadow: var(--shadow-sm);
}
.stat-icon {
  width: 48px; height: 48px;
  border-radius: var(--radius-md);
  display: grid; place-items: center;
  color: #fff; font-size: 22px;
  flex-shrink: 0;
}
.stat-icon.bg-blue { background: var(--color-primary); }
.stat-icon.bg-green { background: var(--color-success); }
.stat-icon.bg-purple { background: var(--color-info); }
.stat-icon.bg-orange { background: var(--color-warning); }
.stat-info { min-width: 0; }
.stat-value { font-size: 26px; font-weight: 800; color: var(--color-text); line-height: 1.2; }
.stat-label { font-size: 12px; color: var(--color-text-secondary); margin-top: 2px; }

/* --- Section Header --- */
.section-header {
  font-size: 15px; font-weight: 700; color: var(--color-text);
  margin: 28px 0 14px;
}

/* --- Quick Grid --- */
.quick-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.quick-card {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 20px 12px 16px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color-light);
  background: var(--color-bg-card);
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}
.quick-card:hover {
  border-color: var(--color-primary-border);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.quick-icon {
  width: 44px; height: 44px; border-radius: var(--radius-md);
  display: grid; place-items: center; color: #fff;
}
.quick-icon.accent-blue { background: var(--color-primary); }
.quick-icon.accent-green { background: var(--color-success); }
.quick-icon.accent-purple { background: var(--color-info); }
.quick-icon.accent-amber { background: var(--color-warning); }
.quick-icon.accent-indigo { background: var(--color-accent); }
.quick-icon.accent-rose { background: var(--color-danger); }
.quick-card > span { font-size: 14px; font-weight: 600; color: var(--color-text); }
.quick-card > small { font-size: 11px; color: var(--color-text-muted); }

/* --- Recent Section --- */
.recent-section {
  min-height: 100px;
}
.recent-list {
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color-light);
  overflow: hidden;
}
.recent-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color-light);
  cursor: pointer;
  transition: background 0.15s ease;
}
.recent-item:last-child { border-bottom: none; }
.recent-item:hover { background: var(--color-bg-hover); }
.recent-name { flex: 1; font-size: 14px; color: var(--color-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recent-time { font-size: 12px; color: var(--color-text-muted); white-space: nowrap; }

/* --- Responsive --- */
@media (max-width: 1024px) {
  .quick-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 640px) {
  .quick-grid { grid-template-columns: repeat(2, 1fr); }
  .stat-value { font-size: 20px; }
}
</style>