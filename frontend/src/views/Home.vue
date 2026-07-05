<template>
  <div class="zx-home">
    <!-- 顶栏 -->
    <header class="home-topbar">
      <button class="brand" type="button" @click="router.push('/home')">
        <span class="brand-mark">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
          </svg>
        </span>
        <div class="brand-text">
          <strong>ZX 测试平台</strong>
          <small>智能软件测试工作台</small>
        </div>
      </button>

      <div class="topbar-center">
        <div class="search-box">
          <el-icon><Search /></el-icon>
          <input type="text" placeholder="搜索测试用例、项目..." />
        </div>
      </div>

      <div class="topbar-right">
        <el-button :icon="Bell" text class="notification-btn">
          <span class="notification-dot"></span>
        </el-button>
        <el-button :icon="Setting" text @click="router.push('/configuration/ai-model')">配置</el-button>
      </div>
    </header>

    <main class="home-shell">
      <!-- 工作区头部 -->
      <section class="workspace-header">
        <div class="header-content">
          <span class="eyebrow">
            <span class="eyebrow-dot"></span>
            测试工作台
          </span>
          <h1>质量工程控制台</h1>
          <p>按需求评审、用例设计、自动化执行、专项测试和报告闭环组织日常测试工作。</p>
        </div>
        <div class="primary-actions">
          <el-button type="primary" size="large" @click="router.push('/ai-generation/requirement-analysis')">
            <template #icon><el-icon><MagicStick /></el-icon></template>
            需求评审
          </el-button>
          <el-button size="large" @click="router.push('/ui-automation/dashboard')">
            <template #icon><el-icon><VideoPlay /></el-icon></template>
            自动化执行
          </el-button>
        </div>
      </section>

      <!-- 统计概览 -->
      <section class="stats-strip">
        <div v-for="(stat, idx) in statsData" :key="idx" class="stat-card" :class="stat.tone">
          <div class="stat-icon">
            <el-icon :size="22"><component :is="stat.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stat.value }}</span>
            <span class="stat-label">{{ stat.label }}</span>
          </div>
          <div class="stat-trend" v-if="stat.trend">
            <span :class="stat.trend > 0 ? 'trend-up' : 'trend-down'">
              {{ stat.trend > 0 ? '↑' : '↓' }} {{ Math.abs(stat.trend) }}%
            </span>
          </div>
        </div>
      </section>

      <!-- 主要内容区 -->
      <section class="console-grid">
        <div class="main-panel">
          <!-- 测试能力入口 -->
          <div class="panel-section">
            <div class="panel-head">
              <div>
                <h2>测试能力入口</h2>
                <p>选择测试类型后进入对应资产和执行页面</p>
              </div>
              <el-tag effect="plain" round>{{ moduleCards.length }} 个模块</el-tag>
            </div>
            <div class="module-grid">
              <article
                v-for="card in moduleCards"
                :key="card.path"
                class="module-card"
                :class="card.tone"
                @click="router.push(card.path)"
              >
                <div class="card-icon-wrap">
                  <div class="card-icon" :class="card.tone">
                    <el-icon :size="22"><component :is="card.icon" /></el-icon>
                  </div>
                </div>
                <div class="card-body">
                  <div class="card-title-row">
                    <h3>{{ card.title }}</h3>
                    <el-tag :type="card.tagType || 'info'" size="small" effect="plain" round>
                      {{ card.tag }}
                    </el-tag>
                  </div>
                  <p>{{ card.desc }}</p>
                </div>
                <div class="card-arrow">
                  <el-icon :size="18"><ArrowRight /></el-icon>
                </div>
              </article>
            </div>
          </div>
        </div>

        <!-- 侧边面板 -->
        <aside class="side-panel">
          <!-- 今日工作流 -->
          <section class="runbook-panel">
            <div class="panel-head">
              <h2>今日工作流</h2>
              <span class="date-badge">{{ currentDate }}</span>
            </div>
            <div class="runbook-list">
              <button
                v-for="item in runbook"
                :key="item.title"
                class="runbook-item"
                type="button"
                @click="router.push(item.path)"
              >
                <span class="runbook-dot" :class="item.tone"></span>
                <div class="runbook-content">
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.desc }}</p>
                </div>
                <el-icon class="runbook-arrow"><CaretRight /></el-icon>
              </button>
            </div>
          </section>

          <!-- 平台状态 -->
          <section class="status-panel">
            <div class="panel-head">
              <h2>平台状态</h2>
              <span class="status-indicator online">
                <span class="status-dot"></span>
                运行中
              </span>
            </div>
            <div class="status-grid">
              <div v-for="item in overview" :key="item.label" class="status-item">
                <span class="status-value">{{ item.value }}</span>
                <span class="status-label">{{ item.label }}</span>
              </div>
            </div>
          </section>

          <!-- 标准流程 -->
          <section class="workflow-panel">
            <div class="panel-head">
              <h2>标准测试流程</h2>
            </div>
            <div class="workflow-list">
              <div v-for="(step, idx) in workflow" :key="step.title" class="workflow-item">
                <div class="workflow-num">{{ String(idx + 1).padStart(2, '0') }}</div>
                <div class="workflow-content">
                  <strong>{{ step.title }}</strong>
                  <p>{{ step.desc }}</p>
                </div>
              </div>
            </div>
          </section>
        </aside>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight,
  CaretRight,
  Cellphone,
  DataAnalysis,
  Folder,
  FolderOpened,
  Link,
  MagicStick,
  Monitor,
  Odometer,
  Search,
  VideoPlay
} from '@element-plus/icons-vue'

const router = useRouter()

// Document 图标别名
const Document = FolderOpened

// 当前日期
const currentDate = computed(() => {
  const now = new Date()
  return `${now.getMonth() + 1}月${now.getDate()}日`
})

// 统计数据
const statsData = [
  { value: '12', label: '测试项目', trend: 8, icon: Folder, tone: 'blue' },
  { value: '156', label: '测试用例', trend: 12, icon: Document, tone: 'green' },
  { value: '89%', label: '通过率', trend: 3, icon: Odometer, tone: 'purple' },
  { value: '4', label: '进行中', trend: -2, icon: VideoPlay, tone: 'orange' }
]

const overview = [
  { value: '5+', label: '测试模块' },
  { value: '4类', label: '自动化对象' },
  { value: 'AI', label: '智能分析' },
  { value: '100%', label: '可追溯' }
]

const runbook = [
  { title: '上传需求并评审', desc: '先评审风险和表头，再生成真实测试用例', path: '/ai-generation/requirement-analysis', tone: 'blue' },
  { title: '一键执行自动化', desc: '网站、APP 按用例目标进入对应执行链路', path: '/ai-generation/generated-testcases', tone: 'green' },
  { title: '配置自动化 AI', desc: '文本/视觉模型可同时启用，后端自动选择可用模型', path: '/configuration/ai-mode', tone: 'purple' }
]

const moduleCards = [
  {
    title: '软测需求分析',
    desc: 'AI 驱动需求文档解析、测试点生成、用例编写与风险分析报告。',
    tag: 'AI 生成',
    tagType: 'info',
    path: '/ai-generation/requirement-analysis',
    icon: MagicStick,
    tone: 'blue'
  },
  {
    title: '接口自动化测试',
    desc: '管理 API 项目、环境变量、请求历史、定时任务与测试报告。',
    tag: 'API/WS',
    tagType: 'success',
    path: '/api-testing/dashboard',
    icon: Link,
    tone: 'green'
  },
  {
    title: '网页 UI 自动化',
    desc: 'Selenium / Playwright 驱动，元素管理、脚本编排、智能执行。',
    tag: 'Web UI',
    tagType: 'warning',
    path: '/ui-automation/dashboard',
    icon: Monitor,
    tone: 'purple'
  },
  {
    title: 'APP 自动化测试',
    desc: 'Android 设备管理、APK 安装、元素采集、场景编排执行。',
    tag: 'Mobile',
    tagType: 'danger',
    path: '/app-automation/dashboard',
    icon: Cellphone,
    tone: 'orange'
  },
  {
    title: '报告中心',
    desc: '汇总所有测试结果，生成质量报告、覆盖率分析与闭环追踪。',
    tag: 'Report',
    tagType: 'success',
    path: '/ai-generation/reports',
    icon: DataAnalysis,
    tone: 'slate'
  }
]

const workflow = [
  { title: '录入需求', desc: '输入用户描述、上传需求文件或填写目标系统地址。' },
  { title: 'AI 智能分析', desc: '生成测试范围、风险点、功能用例、异常场景。' },
  { title: '自动执行验证', desc: '按接口、网页、APP 或智能浏览器模式执行测试。' },
  { title: '生成测试报告', desc: '沉淀执行记录、缺陷线索、覆盖情况与质量分析。' }
]
</script>

<style scoped lang="scss">
/* ============================================================
   首页布局 - 现代化企业级设计
   ============================================================ */
.zx-home {
  min-height: 100vh;
  background: var(--color-bg-gradient);
}

/* ============================================================
   顶部导航栏
   ============================================================ */
.home-topbar {
  height: var(--header-height);
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  border-bottom: 1px solid var(--border-color);
  background: var(--color-bg-card);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: var(--shadow-sm);
}

.brand {
  border: none;
  background: transparent;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  text-align: left;
  color: inherit;
  padding: 8px 12px;
  border-radius: var(--radius-lg);
  transition: all var(--transition-fast);

  &:hover {
    background: var(--color-bg-hover);
  }
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  display: grid;
  place-items: center;
  color: var(--color-text-inverse);
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.brand-text {
  strong {
    display: block;
    font-size: 16px;
    font-weight: 700;
    color: var(--color-text);
    line-height: 1.2;
  }
  small {
    display: block;
    margin-top: 2px;
    font-size: 12px;
    color: var(--color-text-muted);
    font-weight: 400;
  }
}

.topbar-center {
  flex: 1;
  max-width: 400px;
  display: flex;
  justify-content: center;
}

.search-box {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
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
    font-size: 14px;
    color: var(--color-text);
    outline: none;

    &::placeholder {
      color: var(--color-text-placeholder);
    }
  }
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.notification-btn {
  position: relative;
  padding: 8px !important;

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

.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  background: var(--color-bg-card);
  padding: 4px 12px 4px 4px;
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text-secondary);
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--color-primary-border);
    box-shadow: var(--shadow-sm);
  }

  .username {
    font-weight: 500;
  }
}

/* ============================================================
   主内容区域
   ============================================================ */
.home-shell {
  width: min(1440px, calc(100% - 48px));
  margin: 0 auto;
  padding: 32px 0 48px;
}

/* ============================================================
   工作区头部
   ============================================================ */
.workspace-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 0 24px;

  .header-content {
    flex: 1;
  }

  .eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--color-primary);
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 8px;

    .eyebrow-dot {
      width: 6px;
      height: 6px;
      background: var(--color-primary);
      border-radius: 50%;
      animation: pulse 2s infinite;
    }
  }

  h1 {
    margin: 0 0 10px;
    font-size: 32px;
    font-weight: 800;
    line-height: 1.2;
    color: var(--color-text);
    letter-spacing: -0.02em;
  }

  p {
    margin: 0;
    max-width: 580px;
    color: var(--color-text-secondary);
    font-size: 14px;
    line-height: 1.7;
  }
}

.primary-actions {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

/* ============================================================
   统计概览
   ============================================================ */
.stats-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: var(--color-bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-fast);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
  }

  &:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
  }

  &.blue::before { background: var(--color-tone-blue); }
  &.green::before { background: var(--color-tone-green); }
  &.purple::before { background: var(--color-tone-purple); }
  &.orange::before { background: var(--color-tone-orange); }

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: var(--radius-lg);
    display: grid;
    place-items: center;
    flex-shrink: 0;

    &.blue { background: var(--color-tone-blue-bg); color: var(--color-tone-blue); }
    &.green { background: var(--color-tone-green-bg); color: var(--color-tone-green); }
    &.purple { background: var(--color-tone-purple-bg); color: var(--color-tone-purple); }
    &.orange { background: var(--color-tone-orange-bg); color: var(--color-tone-orange); }
  }

  .stat-info {
    flex: 1;
    min-width: 0;
  }

  .stat-value {
    display: block;
    font-size: 26px;
    font-weight: 800;
    color: var(--color-text);
    line-height: 1.1;
    letter-spacing: -0.01em;
  }

  .stat-label {
    display: block;
    margin-top: 4px;
    font-size: 13px;
    color: var(--color-text-secondary);
    font-weight: 500;
  }

  .stat-trend {
    font-size: 12px;
    font-weight: 600;

    .trend-up { color: var(--color-success); }
    .trend-down { color: var(--color-danger); }
  }
}

/* ============================================================
   主网格布局
   ============================================================ */
.console-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 24px;
  align-items: start;
}

/* ============================================================
   主面板
   ============================================================ */
.main-panel {
  background: var(--color-bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.panel-section {
  padding: 20px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;

  h2 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: var(--color-text);
  }

  p {
    margin: 4px 0 0;
    font-size: 13px;
    color: var(--color-text-muted);
  }
}

/* ============================================================
   模块卡片网格
   ============================================================ */
.module-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.module-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--color-bg-card) 0%, var(--color-bg-surface) 100%);
  cursor: pointer;
  transition: all var(--transition-normal);
  position: relative;

  &:hover {
    border-color: var(--color-primary-border);
    box-shadow: var(--shadow-md);
    transform: translateY(-3px);

    .card-arrow {
      opacity: 1;
      transform: translateX(0);
    }
  }

  &.blue:hover { border-color: var(--color-tone-blue-border); }
  &.green:hover { border-color: var(--color-tone-green-border); }
  &.purple:hover { border-color: var(--color-tone-purple-border); }
  &.orange:hover { border-color: var(--color-tone-orange-border); }
  &.cyan:hover { border-color: var(--color-tone-cyan-border); }
  &.yellow:hover { border-color: var(--color-tone-yellow-border); }
  &.red:hover { border-color: var(--color-tone-red-border); }
  &.slate:hover { border-color: var(--color-tone-slate-border); }
}

.card-icon-wrap {
  flex-shrink: 0;
}

.card-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-lg);
  display: grid;
  place-items: center;
  box-shadow: var(--shadow-xs);

  &.blue { background: var(--color-tone-blue-bg); color: var(--color-tone-blue); }
  &.green { background: var(--color-tone-green-bg); color: var(--color-tone-green); }
  &.purple { background: var(--color-tone-purple-bg); color: var(--color-tone-purple); }
  &.orange { background: var(--color-tone-orange-bg); color: var(--color-tone-orange); }
  &.cyan { background: var(--color-tone-cyan-bg); color: var(--color-tone-cyan); }
  &.yellow { background: var(--color-tone-yellow-bg); color: var(--color-tone-yellow); }
  &.red { background: var(--color-tone-red-bg); color: var(--color-tone-red); }
  &.slate { background: var(--color-tone-slate-bg); color: var(--color-tone-slate); }
}

.card-body {
  flex: 1;
  min-width: 0;
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;

  h3 {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    color: var(--color-text);
  }
}

.module-card p {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.card-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  color: var(--color-text-muted);
  opacity: 0;
  transform: translateX(-8px);
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

/* ============================================================
   侧边面板
   ============================================================ */
.side-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.runbook-panel,
.status-panel,
.workflow-panel {
  background: var(--color-bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.runbook-panel,
.status-panel {
  .panel-head {
    padding: 18px 20px;
    border-bottom: 1px solid var(--border-color-light);
    margin-bottom: 0;
  }
}

.workflow-panel .panel-head {
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-color-light);
}

.date-badge {
  font-size: 12px;
  color: var(--color-text-muted);
  background: var(--color-bg-surface);
  padding: 4px 10px;
  border-radius: var(--radius-full);
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;

  &.online { color: var(--color-success); }
  &.offline { color: var(--color-danger); }

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse 2s infinite;
  }
}

/* ============================================================
   工作流列表
   ============================================================ */
.runbook-list {
  padding: 12px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.runbook-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-lg);
  background: var(--color-bg-card);
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    border-color: var(--color-primary-border);
    background: var(--color-primary-bg);

    .runbook-arrow {
      opacity: 1;
      transform: translateX(0);
    }
  }

  .runbook-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;

    &.blue { background: var(--color-tone-blue); }
    &.green { background: var(--color-tone-green); }
    &.purple { background: var(--color-tone-purple); }
  }

  .runbook-content {
    flex: 1;
    min-width: 0;

    strong {
      display: block;
      font-size: 13px;
      font-weight: 600;
      color: var(--color-text);
      margin-bottom: 2px;
    }

    p {
      margin: 0;
      font-size: 12px;
      color: var(--color-text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }

  .runbook-arrow {
    color: var(--color-text-muted);
    opacity: 0;
    transform: translateX(-4px);
    transition: all var(--transition-fast);
    flex-shrink: 0;
  }
}

/* ============================================================
   状态网格
   ============================================================ */
.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 16px 20px;
}

.status-item {
  padding: 14px;
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
  border: 1px solid var(--border-color-light);
  text-align: center;

  .status-value {
    display: block;
    font-size: 22px;
    font-weight: 800;
    color: var(--color-text);
    line-height: 1.1;
  }

  .status-label {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: var(--color-text-muted);
    font-weight: 500;
  }
}

/* ============================================================
   标准流程
   ============================================================ */
.workflow-list {
  padding: 12px 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.workflow-item {
  display: flex;
  gap: 14px;
  padding: 12px 0;
  position: relative;

  &:not(:last-child)::after {
    content: '';
    position: absolute;
    left: 15px;
    top: 44px;
    bottom: -12px;
    width: 2px;
    background: var(--border-color-light);
  }

  &:last-child::after {
    display: none;
  }
}

.workflow-num {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-primary-bg);
  color: var(--color-primary);
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 800;
  flex-shrink: 0;
  border: 2px solid var(--color-primary-border);
}

.workflow-content {
  flex: 1;
  padding-top: 4px;

  strong {
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: var(--color-text);
    margin-bottom: 2px;
  }

  p {
    margin: 0;
    font-size: 12px;
    color: var(--color-text-muted);
    line-height: 1.5;
  }
}

/* ============================================================
   颜色辅助类
   ============================================================ */
.blue   { color: var(--color-tone-blue); }
.green  { color: var(--color-tone-green); }
.purple { color: var(--color-tone-purple); }
.orange { color: var(--color-tone-orange); }
.cyan   { color: var(--color-tone-cyan); }
.yellow { color: var(--color-tone-yellow); }
.red    { color: var(--color-tone-red); }
.slate  { color: var(--color-tone-slate); }

/* ============================================================
   响应式布局
   ============================================================ */
@media (max-width: 1200px) {
  .console-grid {
    grid-template-columns: 1fr;
  }

  .side-panel {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .stats-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .module-grid {
    grid-template-columns: 1fr;
  }

  .workspace-header {
    flex-direction: column;

    h1 {
      font-size: 26px;
    }
  }

  .primary-actions {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 720px) {
  .home-topbar {
    padding: 0 14px;
  }

  .topbar-center {
    display: none;
  }

  .home-shell {
    width: calc(100% - 24px);
    padding: 16px 0 32px;
  }

  .stats-strip {
    grid-template-columns: 1fr;
  }

  .side-panel {
    grid-template-columns: 1fr;
  }

  .workspace-header {
    padding: 16px 0;

    h1 {
      font-size: 22px;
    }

    p {
      font-size: 13px;
    }
  }
}
</style>
