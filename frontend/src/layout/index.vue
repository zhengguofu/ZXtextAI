<template>
  <div class="zx-layout" :class="{ 'sidebar-collapsed': collapsed }">
    <!-- 侧边栏 -->
    <aside class="zx-sidebar" :class="{ open: mobileOpen }">
      <!-- 品牌 -->
      <button class="sidebar-brand" type="button" @click="goHome">
        <span class="brand-logo">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
          </svg>
        </span>
        <div class="brand-text" v-show="!collapsed">
          <strong>ZX测试平台</strong>
          <small>智能软件测试</small>
        </div>
      </button>

      <!-- 折叠按钮 -->
      <button class="collapse-btn" type="button" @click="collapsed = !collapsed" :title="collapsed ? '展开侧栏' : '收起侧栏'">
        <el-icon :size="18"><component :is="collapsed ? Expand : Fold" /></el-icon>
      </button>

      <!-- 模块导航 -->
      <nav class="module-nav" v-show="!collapsed">
        <button
          v-for="module in modules"
          :key="module.key"
          type="button"
          class="module-btn"
          :class="{ active: currentModule === module.key }"
          @click="router.push(module.path)"
        >
          <el-icon :size="18"><component :is="module.icon" /></el-icon>
          <span>{{ module.label }}</span>
        </button>
      </nav>

      <!-- 折叠态图标菜单 -->
      <div class="mini-icons" v-show="collapsed">
        <button
          v-for="module in modules"
          :key="module.key"
          type="button"
          class="mini-btn"
          :class="{ active: currentModule === module.key }"
          :title="module.label"
          @click="router.push(module.path)"
        >
          <el-icon :size="20"><component :is="module.icon" /></el-icon>
        </button>
      </div>

      <!-- 平台信息（底部） -->
      <div class="sidebar-user" :class="{ compact: collapsed }">
        <div class="user-btn-static">
          <el-avatar :size="collapsed ? 32 : 34" :icon="UserFilled" />
          <div class="user-meta" v-show="!collapsed">
            <strong>管理员</strong>
            <small>v2.0 · 智能驱动</small>
          </div>
        </div>
      </div>
    </aside>

    <!-- 移动端遮罩 -->
    <div class="mobile-mask" v-if="mobileOpen" @click="mobileOpen = false" />

    <!-- 主区域 -->
    <section class="zx-main">
      <!-- 页面头部 -->
      <header class="zx-header">
        <div class="header-left">
          <el-button class="menu-trigger" :icon="Menu" text @click="mobileOpen = true" />
          <div class="header-info">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{ path: '/home' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item v-if="activeModule">{{ activeModule.label }}</el-breadcrumb-item>
              <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
            </el-breadcrumb>
            <h1>{{ currentTitle || activeModule?.label || '工作空间' }}</h1>
          </div>
        </div>

        <div class="header-center">
          <div class="search-box">
            <el-icon><Search /></el-icon>
            <input type="text" placeholder="搜索..." />
          </div>
        </div>

        <div class="header-right">
          <el-button class="chat-btn" :icon="ChatDotRound" text @click="router.push('/ai-generation/assistant')">
            助手
          </el-button>
          <el-button class="notification-btn" :icon="Bell" text @click="toggleNotification">
            <span class="notification-dot" v-if="notificationCount > 0"></span>
          </el-button>
          <!-- 通知面板 -->
          <div class="notification-panel" v-show="showNotification">
            <div class="notification-header">
              <h3>通知中心</h3>
              <button class="close-btn" @click="showNotification = false">
                <el-icon><Close /></el-icon>
              </button>
            </div>
            <div class="notification-body">
              <div class="notification-tabs">
                <button 
                  class="tab-btn" 
                  :class="{ active: activeNotificationTab === 'operations' }"
                  @click="activeNotificationTab = 'operations'"
                >
                  操作记录
                </button>
                <button 
                  class="tab-btn" 
                  :class="{ active: activeNotificationTab === 'logs' }"
                  @click="activeNotificationTab = 'logs'"
                >
                  系统日志
                </button>
              </div>
              <div class="notification-content">
                <div v-if="activeNotificationTab === 'operations'" class="notification-list">
                  <div v-for="item in operationLogs" :key="item.id" class="notification-item">
                    <el-icon class="item-icon" :size="18"><component :is="item.icon" /></el-icon>
                    <div class="item-content">
                      <p class="item-title">{{ item.title }}</p>
                      <p class="item-time">{{ item.time }}</p>
                    </div>
                    <button class="delete-btn" @click="deleteNotification('operations', item.id)">
                      <el-icon><Delete /></el-icon>
                    </button>
                  </div>
                  <div v-if="operationLogs.length === 0" class="empty-state">
                    <el-icon :size="32"><Bell /></el-icon>
                    <p>暂无操作记录</p>
                  </div>
                </div>
                <div v-if="activeNotificationTab === 'logs'" class="log-list">
                  <div v-for="(log, index) in systemLogs" :key="index" class="log-item" :class="log.level">
                    <span class="log-level">[{{ log.level.toUpperCase() }}]</span>
                    <span class="log-message">{{ log.message }}</span>
                    <span class="log-time">{{ log.time }}</span>
                    <button class="delete-btn" @click="deleteNotification('logs', index)">
                      <el-icon><Delete /></el-icon>
                    </button>
                  </div>
                  <div v-if="systemLogs.length === 0" class="empty-state">
                    <el-icon :size="32"><Document /></el-icon>
                    <p>暂无系统日志</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <el-button :icon="Setting" text @click="router.push('/configuration/ai-model')">
            配置
          </el-button>
        </div>
      </header>

      <!-- 模块功能条 -->
      <nav class="subnav-bar" v-if="activeMenus.length">
        <div class="subnav-scroll">
          <button
            v-for="item in activeMenus"
            :key="item.path"
            type="button"
            class="subnav-item"
            :class="{ active: isMenuActive(item.path) }"
            @click="router.push(item.path)"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
          </button>
        </div>
      </nav>

      <!-- 内容区域 -->
      <main class="content-wrap">
        <router-view v-slot="{ Component }">
          <keep-alive :include="cachedViews">
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Bell,
  Box,
  Cellphone,
  ChatDotRound,
  Cpu,
  DataAnalysis,
  Delete,
  Document,
  DocumentCopy,
  Expand,
  Fold,
  Folder,
  Link,
  MagicStick,
  Menu,
  Monitor,
  Odometer,
  PictureFilled,
  Search,
  Setting,
  Timer,
  UserFilled,
  VideoPlay,
  Close,
  CircleCheck,
  Warning,
  InfoFilled,
  Refresh
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const mobileOpen = ref(false)
// 保持组件状态 — 防止页面切换后自动化执行上下文丢失
const cachedViews = ['AITesting', 'AICaseList', 'AIExecutionRecords']

// 通知相关状态
const showNotification = ref(false)
const activeNotificationTab = ref('operations')
const notificationCount = ref(3)

const operationLogs = ref([
  { id: 1, icon: CircleCheck, title: '用例评审完成', time: '2分钟前' },
  { id: 2, icon: InfoFilled, title: 'AI模型配置更新', time: '15分钟前' },
  { id: 3, icon: Warning, title: '环境检测完成', time: '30分钟前' }
])

const systemLogs = ref([
  { level: 'info', message: '系统启动成功', time: '16:31' },
  { level: 'info', message: 'AI模型配置加载完成', time: '16:31' },
  { level: 'warning', message: '部分浏览器驱动未安装', time: '16:30' },
  { level: 'info', message: '数据库连接正常', time: '16:30' }
])

const toggleNotification = () => {
  showNotification.value = !showNotification.value
}

const deleteNotification = (type, id) => {
  if (type === 'operations') {
    operationLogs.value = operationLogs.value.filter(item => item.id !== id)
    notificationCount.value = operationLogs.value.length
  } else {
    systemLogs.value.splice(id, 1)
  }
}

watch(() => route.path, () => { 
  mobileOpen.value = false 
  showNotification.value = false
})

const modules = [
  { key: 'ai-generation', label: '需求分析', path: '/ai-generation/requirement-analysis', icon: MagicStick, group: '测试设计', desc: '需求评审、用例生成、用例库与测试报告' },
  { key: 'api-testing', label: '接口测试', path: '/api-testing/dashboard', icon: Link, group: '自动化执行', desc: '接口资产、环境变量、自动执行与报告' },
  { key: 'ui-automation', label: '网页自动化', path: '/ui-automation/dashboard', icon: Monitor, group: '自动化执行', desc: '网页元素、AI 浏览器执行与回放报告' },
  { key: 'app-automation', label: 'APP 自动化', path: '/app-automation/dashboard', icon: Cellphone, group: '移动测试', desc: '设备管理、APP 用例、套件与执行记录' },
  { key: 'toolbox', label: '工具集', path: '/toolbox', icon: Box, group: '辅助工具', desc: '测试工具、代码转换、常用工具集合' },
  { key: 'assets', label: '测试资产', path: '/assets', icon: PictureFilled, group: '测试管理', desc: '截图记录、视频回放、测试报告与文件下载' },
  { key: 'configuration', label: '配置中心', path: '/configuration/ai-model', icon: Setting, group: '系统设置', desc: 'AI 模型、环境、通知和执行配置' }
]

const menus = {
  'ai-generation': [
    { path: '/ai-generation/requirement-analysis', label: '需求分析', icon: MagicStick },
    { path: '/ai-generation/generated-testcases', label: '生成用例', icon: Document },
    { path: '/ai-generation/testcases', label: '用例库', icon: DocumentCopy },
    { path: '/ai-generation/executions', label: '执行计划', icon: VideoPlay },
    { path: '/ai-generation/reports', label: '测试报告', icon: DataAnalysis }
  ],
  'api-testing': [
    { path: '/api-testing/dashboard', label: '接口概览', icon: Odometer },
    { path: '/api-testing/interfaces', label: '接口管理', icon: Link },
    { path: '/api-testing/history', label: '请求历史', icon: Timer },
    { path: '/api-testing/environments', label: '环境管理', icon: Setting },
    { path: '/api-testing/automation', label: '自动化执行', icon: VideoPlay },
    { path: '/api-testing/scheduled-tasks', label: '定时任务', icon: DataAnalysis },
    { path: '/api-testing/reports', label: '接口报告', icon: Document },
  ],
  'ui-automation': [
    { path: '/ui-automation/dashboard', label: '网页概览', icon: Odometer },
    { path: '/ui-automation/full-auto', label: '全自动测试', icon: MagicStick },
    { path: '/ui-automation/case-based', label: '用例驱动测试', icon: Document },
    { path: '/ui-automation/execution-records', label: '执行记录', icon: Timer },
    { path: '/ui-automation/reports', label: '测试报告', icon: DataAnalysis },
    { path: '/ui-automation/assets', label: '截图&视频', icon: PictureFilled },
  ],
  'app-automation': [
    { path: '/app-automation/dashboard', label: 'APP 概览', icon: Odometer },
    { path: '/app-automation/devices', label: '手机设备', icon: Cellphone },
    { path: '/app-automation/devices/simulator', label: '手机模拟器', icon: Cellphone },
    { path: '/app-automation/test-cases', label: 'APP 用例', icon: Document },
    { path: '/app-automation/test-suites', label: '测试套件', icon: Folder },
    { path: '/app-automation/scene-builder', label: '用例编排', icon: MagicStick },
    { path: '/app-automation/elements', label: '元素管理', icon: Cpu },
    { path: '/app-automation/executions', label: '执行记录', icon: VideoPlay },
    { path: '/app-automation/scheduled-tasks', label: '定时任务', icon: Timer },
    { path: '/app-automation/reports', label: 'APP 报告', icon: DataAnalysis }
  ],
  assets: [
    { path: '/assets', label: '测试资产', icon: PictureFilled },
  ],
  configuration: [
    { path: '/configuration/ai-model', label: 'AI 模型配置', icon: Cpu },
    { path: '/configuration/prompt-config', label: '提示词配置', icon: Document },
    { path: '/configuration/generation-config', label: '生成规则', icon: MagicStick },
    { path: '/configuration/ui-env', label: '网页环境', icon: Monitor },
    { path: '/configuration/app-env', label: 'APP 环境', icon: Cellphone },
    { path: '/configuration/scheduled-task', label: '通知任务', icon: Timer },
    { path: '/configuration/dify', label: 'Dify 配置', icon: Setting }
  ]
}

const currentModule = computed(() => {
  const path = route.path
  
  const found = modules.find(m => path.startsWith(`/${m.key}`))
  return found?.key || 'ai-generation'
})

const activeModule = computed(() => modules.find(m => m.key === currentModule.value))
const activeMenus = computed(() => menus[currentModule.value] || [])
const currentTitle = computed(() =>
  activeMenus.value.find(i => i.path === route.path)?.label || route.meta?.title || ''
)

const isMenuActive = (path) => route.path === path || route.path.startsWith(`${path}/`)

watch(() => route.path, () => { mobileOpen.value = false })

const goHome = () => router.push('/home')
</script>

<style scoped lang="scss">
/* ============================================================
   Layout Grid
   ============================================================ */
.zx-layout {
  min-height: 100vh;
  display: grid;
  grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
  background: var(--color-bg);
  color: var(--color-text);
  transition: grid-template-columns 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &.sidebar-collapsed {
    grid-template-columns: var(--sidebar-collapsed) minmax(0, 1fr);
  }
}

/* ============================================================
   Sidebar
   ============================================================ */
.zx-sidebar {
  height: 100vh;
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  padding: 14px 10px;
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  overflow: hidden;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &.open {
    transform: translateX(0);
  }
}

.zx-sidebar::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(180deg, rgba(37, 99, 235, 0.12), transparent 28%),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04), transparent 50%);
}

.zx-sidebar > * {
  position: relative;
}

.sidebar-brand {
  height: 56px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--sidebar-bg-elevated);
  color: var(--color-text-inverse);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;

  &:hover {
    background: rgba(255, 255, 255, 0.09);
  }
}

.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-lg);
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 15px;
  color: var(--color-text-inverse);
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
  flex-shrink: 0;
}

.brand-text {
  overflow: hidden;

  strong {
    display: block;
    font-size: 15px;
    font-weight: 700;
    line-height: 1.2;
    white-space: nowrap;
    letter-spacing: -0.01em;
  }

  small {
    display: block;
    font-size: 11px;
    color: var(--sidebar-text);
    font-weight: 400;
    letter-spacing: 0.03em;
    margin-top: 2px;
  }
}

/* 折叠按钮 */
.collapse-btn {
  position: absolute;
  top: 56px;
  right: -14px;
  z-index: 5;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid var(--border-color);
  background: var(--color-bg-card);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  box-shadow: var(--shadow-md);
  transition: all 0.2s ease;

  &:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
    box-shadow: var(--shadow-lg);
    transform: scale(1.05);
  }
}

/* ============================================================
   Module Navigation
   ============================================================ */
.module-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 16px 0 0;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.3) transparent;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.3);
    border-radius: 2px;
  }
}

.module-btn {
  height: 40px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--sidebar-text);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 11px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;

  &:hover {
    color: var(--color-text-inverse);
    background: var(--sidebar-bg-hover);
  }

  &.active {
    color: var(--color-text-inverse);
    background: var(--sidebar-bg-active);
    font-weight: 600;
    box-shadow: inset 3px 0 0 var(--color-primary-light);
  }

  .el-icon {
    flex-shrink: 0;
    font-size: 17px;
  }
}

/* 折叠态图标菜单 */
.mini-icons {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  overflow-y: auto;
}

.mini-btn {
  width: 44px;
  height: 44px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--sidebar-text);
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: all 0.2s ease;

  &:hover {
    color: var(--color-text-inverse);
    background: var(--sidebar-bg-hover);
    transform: scale(1.08);
  }

  &.active {
    color: var(--color-text-inverse);
    background: var(--sidebar-bg-active);
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
  }

  .el-icon {
    font-size: 19px;
  }
}

/* ============================================================
   Sidebar User
   ============================================================ */
.sidebar-user {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--sidebar-border);
  flex-shrink: 0;

  &.compact {
    border-top: none;
    padding-top: 8px;
  }
}

.user-btn-static {
  width: 100%;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.055);
  color: var(--sidebar-text);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
}

.user-meta {
  flex: 1;
  min-width: 0;
  text-align: left;
  overflow: hidden;

  strong {
    display: block;
    font-size: 13px;
    color: var(--color-text-inverse);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-weight: 600;
  }

  small {
    display: block;
    font-size: 11px;
    color: var(--sidebar-text);
    margin-top: 2px;
  }
}

.user-arrow {
  color: var(--sidebar-text);
  font-size: 12px;
  transition: transform 0.2s ease;
}

.user-btn:hover .user-arrow {
  transform: rotate(180deg);
}

/* ============================================================
   Main Area
   ============================================================ */
.zx-main {
  min-width: 0;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(246, 248, 251, 0) 180px),
    var(--color-bg);
}

/* ============================================================
   Header
   ============================================================ */
.zx-header {
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 0 var(--spacing-xl);
  border-bottom: 1px solid var(--border-color);
  background: var(--color-bg-card);
  position: sticky;
  top: 0;
  z-index: 8;
  box-shadow: var(--shadow-sm);
}

.header-left {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
}

.header-center {
  flex: 1;
  max-width: 320px;
  display: flex;
  justify-content: center;
}

.search-box {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  background: var(--color-bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  transition: all var(--transition-fast);

  &:focus-within {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px var(--color-primary-bg);
  }

  .el-icon {
    color: var(--color-text-muted);
    flex-shrink: 0;
  }

  input {
    flex: 1;
    border: none;
    background: transparent;
    font-size: 13px;
    color: var(--color-text);
    outline: none;

    &::placeholder {
      color: var(--color-text-placeholder);
    }
  }
}

.header-info {
  min-width: 0;

  :deep(.el-breadcrumb) {
    margin-bottom: 3px;

    .el-breadcrumb__item {
      font-size: 12px;
      color: var(--color-text-muted);

      .el-breadcrumb__inner {
        transition: color 0.2s ease;

        &:hover {
          color: var(--color-primary);
        }
      }
    }
  }

  h1 {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
    line-height: 1.3;
    color: var(--color-text);
    letter-spacing: -0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.menu-trigger {
  display: none;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.notification-btn {
  position: relative;
  padding: 8px 10px !important;

  .notification-dot {
    position: absolute;
    top: 6px;
    right: 6px;
    width: 8px;
    height: 8px;
    background: var(--color-danger);
    border-radius: 50%;
    border: 2px solid var(--color-bg-card);
  }
}

/* 通知面板 */
.notification-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 8px;
  width: 380px;
  background: var(--color-bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  z-index: 100;
  overflow: hidden;
  animation: fadeSlideIn 0.2s ease;

  &::before {
    content: '';
    position: absolute;
    top: -6px;
    right: 16px;
    width: 12px;
    height: 12px;
    background: var(--color-bg-card);
    border-left: 1px solid var(--border-color);
    border-top: 1px solid var(--border-color);
    transform: rotate(45deg);
  }
}

@keyframes fadeSlideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.notification-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-color);

  h3 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: var(--color-text);
  }

  .close-btn {
    border: none;
    background: transparent;
    color: var(--color-text-muted);
    cursor: pointer;
    padding: 4px;
    border-radius: var(--radius-sm);
    transition: all 0.2s ease;

    &:hover {
      background: var(--color-bg-surface);
      color: var(--color-text);
    }
  }
}

.notification-body {
  max-height: 400px;
  display: flex;
  flex-direction: column;
}

.notification-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color);

  .tab-btn {
    flex: 1;
    border: none;
    background: transparent;
    color: var(--color-text-secondary);
    padding: 12px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    border-bottom: 2px solid transparent;

    &:hover {
      color: var(--color-primary);
    }

    &.active {
      color: var(--color-primary);
      border-bottom-color: var(--color-primary);
      background: var(--color-primary-bg);
    }
  }
}

.notification-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: var(--color-bg-surface);
  }

  .item-icon {
    flex-shrink: 0;
    margin-top: 2px;
  }

  .item-content {
    flex: 1;
    min-width: 0;

    .item-title {
      margin: 0;
      font-size: 13px;
      font-weight: 500;
      color: var(--color-text);
      line-height: 1.4;
    }

    .item-time {
      margin: 4px 0 0;
      font-size: 11px;
      color: var(--color-text-muted);
    }
  }
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.log-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  font-size: 12px;
  line-height: 1.4;

  .log-level {
    flex-shrink: 0;
    font-weight: 600;
  }

  .log-message {
    flex: 1;
    min-width: 0;
    color: var(--color-text-secondary);
  }

  .log-time {
    flex-shrink: 0;
    color: var(--color-text-muted);
  }

  &.info .log-level {
    color: var(--color-primary);
  }

  &.warning .log-level {
    color: var(--color-warning);
  }

  &.error .log-level {
    color: var(--color-danger);
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  color: var(--color-text-muted);

  p {
    margin: 12px 0 0;
    font-size: 13px;
  }
}

/* ============================================================
   Sub Navigation
   ============================================================ */
.subnav-bar {
  position: sticky;
  top: var(--header-height);
  z-index: 7;
  min-width: 0;
  padding: 10px var(--spacing-xl);
  border-bottom: 1px solid var(--border-color);
  background: var(--color-subnav-bg);
  backdrop-filter: blur(14px);
}

.subnav-scroll {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.subnav-item {
  height: 32px;
  flex: 0 0 auto;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-secondary);
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    color: var(--color-primary);
    background: var(--color-bg-card);
    border-color: var(--border-color);
  }

  &.active {
    color: var(--color-primary-dark);
    background: var(--color-bg-card);
    border-color: var(--color-primary-border);
    box-shadow: 0 4px 10px rgba(37, 99, 235, 0.08);
  }

  .el-icon {
    font-size: 15px;
  }
}

/* ============================================================
   Content
   ============================================================ */
.content-wrap {
  min-width: 0;
  flex: 1;
  padding: 22px var(--spacing-xl) var(--spacing-xl);
  overflow: visible;
}

/* ============================================================
   Transitions
   ============================================================ */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* ============================================================
   Mobile & Responsive
   ============================================================ */
.mobile-mask {
  display: none;
}

@media (max-width: 1080px) {
  .collapse-btn {
    display: none;
  }

  .header-center {
    display: none;
  }
}

@media (max-width: 980px) {
  .zx-layout {
    grid-template-columns: 1fr;
  }

  .zx-sidebar {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 30;
    width: 280px;
    transform: translateX(-100%);
    box-shadow: var(--shadow-xl);
  }

  .mobile-mask {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 20;
    background: rgba(15, 23, 42, 0.5);
    backdrop-filter: blur(4px);
  }

  .menu-trigger {
    display: inline-flex;
  }
}

@media (max-width: 720px) {
  .zx-header {
    padding: 0 14px;
    height: auto;
    min-height: 56px;
    gap: 12px;
  }

  .header-right .ai-chat-btn span {
    display: none;
  }

  .header-info h1 {
    font-size: 16px;
  }

  .content-wrap {
    padding: 14px;
  }
}
</style>
