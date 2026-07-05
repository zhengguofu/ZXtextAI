import { createRouter, createWebHistory, isNavigationFailure, NavigationFailureType } from 'vue-router'
import { trackPageView } from '@/utils/tracker'
import { reportError, purgeOrphanOverlays } from '@/utils/errorHandler'
import { ElMessage } from 'element-plus'

// 静态导入常用组件来避免动态导入问题
import Layout from '@/layout/index.vue'
import ProjectList from '@/views/projects/ProjectList.vue'
import Home from '@/views/Home.vue'
import DataFactory from '@/views/data-factory/DataFactory.vue'
import Toolbox from '@/views/Toolbox.vue'
import ApiDashboard from '@/views/api-testing/Dashboard.vue'
import ApiProjectManagement from '@/views/api-testing/ProjectManagement.vue'
import ApiInterfaceManagement from '@/views/api-testing/InterfaceManagement.vue'
import ApiAutomationTesting from '@/views/api-testing/AutomationTesting.vue'
import ApiRequestHistory from '@/views/api-testing/RequestHistory.vue'
import ApiEnvironmentManagement from '@/views/api-testing/EnvironmentManagement.vue'
import ApiReportView from '@/views/api-testing/ReportView.vue'
import ApiScheduledTasks from '@/views/api-testing/ScheduledTasks.vue'
import ApiAIServiceConfig from '@/views/api-testing/AIServiceConfig.vue'
import NotificationLogs from '@/views/notification/NotificationLogs.vue'
import UiDashboard from '@/views/ui-automation/dashboard/Dashboard.vue'
import UiReportList from '@/views/ui-automation/reports/ReportList.vue'
import UiAITesting from '@/views/ui-automation/ai/AITesting.vue'
import UiAICaseList from '@/views/ui-automation/ai/AICaseList.vue'
import UiAIExecutionRecords from '@/views/ui-automation/ai/AIExecutionRecords.vue'
import AssistantView from '@/views/assistant/AssistantView.vue'

/** @type {import('vue-router').RouteRecordRaw[]} */
const routes = [
    // ============================================================
    // 根路由重定向
    // ============================================================
    {
        path: '/',
        redirect: to => ({ path: '/home', query: to.query })
    },

    // ============================================================
    // 独立页面（无 Layout 侧栏）
    // ============================================================
    {
        path: '/home',
        name: 'Home',
        component: Home
    },
    {
        path: '/ai-generation/assistant',
        name: 'Assistant',
        component: AssistantView
    },
    {
        path: '/data-factory',
        name: 'DataFactory',
        component: DataFactory
    },
    {
        path: '/toolbox',
        name: 'Toolbox',
        component: Toolbox
    },

    // ============================================================
    // 统一 Layout — 所有模块共享同一个 Layout 实例
    // 这样 keep-alive 可以跨模块保留 AI 任务状态和 WebSocket 连接
    // ============================================================
    {
        path: '/',
        component: Layout,
        children: [
            // ---- 模块根路径重定向 ----
            { path: 'ai-generation', redirect: '/ai-generation/requirement-analysis' },
            { path: 'api-testing', redirect: '/api-testing/dashboard' },
            { path: 'ui-automation', redirect: '/ui-automation/dashboard' },
            { path: 'app-automation', redirect: '/app-automation/dashboard' },
            { path: 'assets', redirect: '/assets/' },
            { path: 'configuration', redirect: '/configuration/ai-model' },

            // ========== 需求分析 (ai-generation) ==========
            {
                path: 'ai-generation/requirement-analysis',
                name: 'RequirementAnalysis',
                component: () => import('@/views/requirement-analysis/RequirementAnalysisView.vue')
            },
            {
                path: 'ai-generation/projects',
                name: 'Projects',
                component: ProjectList
            },
            {
                path: 'ai-generation/projects/:id',
                name: 'ProjectDetail',
                component: () => import('@/views/projects/ProjectDetail.vue')
            },
            {
                path: 'ai-generation/testcases',
                name: 'TestCases',
                component: () => import('@/views/testcases/TestCaseList.vue')
            },
            {
                path: 'ai-generation/testcases/create',
                name: 'CreateTestCase',
                component: () => import('@/views/testcases/TestCaseForm.vue')
            },
            {
                path: 'ai-generation/testcases/:id',
                name: 'TestCaseDetail',
                component: () => import('@/views/testcases/TestCaseDetail.vue')
            },
            {
                path: 'ai-generation/testcases/:id/edit',
                name: 'EditTestCase',
                component: () => import('@/views/testcases/TestCaseEdit.vue')
            },
            {
                path: 'ai-generation/versions',
                name: 'Versions',
                component: () => import('@/views/versions/VersionList.vue')
            },
            {
                path: 'ai-generation/reviews',
                name: 'Reviews',
                component: () => import('@/views/reviews/ReviewList.vue')
            },
            {
                path: 'ai-generation/reviews/create',
                name: 'CreateReview',
                component: () => import('@/views/reviews/ReviewForm.vue')
            },
            {
                path: 'ai-generation/reviews/:id',
                name: 'ReviewDetail',
                component: () => import('@/views/reviews/ReviewDetail.vue')
            },
            {
                path: 'ai-generation/reviews/:id/edit',
                name: 'EditReview',
                component: () => import('@/views/reviews/ReviewForm.vue')
            },
            {
                path: 'ai-generation/review-templates',
                name: 'ReviewTemplates',
                component: () => import('@/views/reviews/ReviewTemplateList.vue')
            },
            {
                path: 'ai-generation/testsuites',
                name: 'TestSuites',
                component: () => import('@/views/testsuites/TestSuiteList.vue')
            },
            {
                path: 'ai-generation/executions',
                name: 'Executions',
                component: () => import('@/views/executions/ExecutionListView.vue')
            },
            {
                path: 'ai-generation/executions/:id',
                name: 'ExecutionDetail',
                component: () => import('@/views/executions/ExecutionDetailView.vue')
            },
            {
                path: 'ai-generation/reports',
                name: 'AiTestReport',
                component: () => import('@/views/reports/AiTestReport.vue')
            },
            {
                path: 'ai-generation/generated-testcases',
                name: 'GeneratedTestCases',
                component: () => import('@/views/requirement-analysis/GeneratedTestCaseList.vue')
            },
            {
                path: 'ai-generation/task-detail/:taskId',
                name: 'TaskDetail',
                component: () => import('@/views/requirement-analysis/TaskDetail.vue')
            },
            {
                path: 'ai-generation/profile',
                name: 'Profile',
                component: () => import('@/views/profile/UserProfile.vue')
            },

            // ========== 接口测试 (api-testing) ==========
            {
                path: 'api-testing/dashboard',
                name: 'ApiDashboard',
                component: ApiDashboard
            },
            {
                path: 'api-testing/projects',
                name: 'ApiProjects',
                component: ApiProjectManagement
            },
            {
                path: 'api-testing/interfaces',
                name: 'ApiInterfaces',
                component: ApiInterfaceManagement
            },
            {
                path: 'api-testing/automation',
                name: 'ApiAutomation',
                component: ApiAutomationTesting
            },
            {
                path: 'api-testing/history',
                name: 'ApiHistory',
                component: ApiRequestHistory
            },
            {
                path: 'api-testing/environments',
                name: 'ApiEnvironments',
                component: ApiEnvironmentManagement
            },
            {
                path: 'api-testing/reports',
                name: 'ApiReports',
                component: ApiReportView
            },
            {
                path: 'api-testing/scheduled-tasks',
                name: 'ApiScheduledTasks',
                component: ApiScheduledTasks
            },
            {
                path: 'api-testing/ai-service-config',
                name: 'ApiAIServiceConfig',
                component: ApiAIServiceConfig
            },
            {
                path: 'api-testing/notification-logs',
                name: 'ApiNotificationLogs',
                component: NotificationLogs
            },

            // ========== 网页自动化 (ui-automation) ==========
            {
                path: 'ui-automation/dashboard',
                name: 'UiDashboard',
                component: UiDashboard
            },
            {
                path: 'ui-automation/full-auto',
                name: 'UiFullAuto',
                component: UiAITesting,
                meta: { title: '全程自动化' }
            },
            {
                path: 'ui-automation/case-based',
                name: 'UiCaseBased',
                component: UiAICaseList,
                meta: { title: '用例驱动测试' }
            },
            {
                path: 'ui-automation/execution-records',
                name: 'UiExecutionRecords',
                component: UiAIExecutionRecords,
                meta: { title: '执行记录' }
            },
            {
                path: 'ui-automation/reports',
                name: 'UiReports',
                component: UiReportList,
                meta: { title: '测试报告' }
            },
            {
                path: 'ui-automation/assets',
                name: 'UiAssets',
                component: () => import('@/views/assets/AssetsCenter.vue'),
                meta: { title: '截图&视频' }
            },

            // ========== 测试资产 ==========
            {
                path: 'assets/',
                name: 'AssetsCenter',
                component: () => import('@/views/assets/AssetsCenter.vue')
            },

            // ========== 配置中心 ==========
            {
                path: 'configuration',
                component: () => import('@/views/configuration/ConfigurationCenter.vue'),
                children: [
                    {
                        path: '',
                        redirect: '/configuration/ai-model'
                    },
                    {
                        path: 'ai-model',
                        name: 'ConfigAIModel',
                        component: () => import('@/views/requirement-analysis/AIModelConfig.vue')
                    },
                    {
                        path: 'prompt-config',
                        name: 'ConfigPromptConfig',
                        component: () => import('@/views/requirement-analysis/PromptConfig.vue')
                    },
                    {
                        path: 'generation-config',
                        name: 'ConfigGenerationConfig',
                        component: () => import('@/views/requirement-analysis/GenerationConfigView.vue')
                    },
                    {
                        path: 'ui-env',
                        name: 'ConfigUIEnv',
                        component: () => import('@/views/configuration/UIEnvironmentConfig.vue')
                    },
                    {
                        path: 'app-env',
                        name: 'ConfigAppEnv',
                        component: () => import('@/views/app-automation/settings/AppSettings.vue')
                    },

                    {
                        path: 'scheduled-task',
                        name: 'ConfigScheduledTask',
                        component: () => import('@/views/ui-automation/notification/NotificationConfigs.vue')
                    },
                    {
                        path: 'dify',
                        name: 'DifyConfig',
                        component: () => import('@/views/configuration/DifyConfig.vue')
                    }
                ]
            },

            // ========== APP自动化测试 ==========
            {
                path: 'app-automation/dashboard',
                name: 'AppAutomationDashboard',
                component: () => import('@/views/app-automation/dashboard/Dashboard.vue')
            },
            {
                path: 'app-automation/projects',
                name: 'AppProjectList',
                component: () => import('@/views/app-automation/projects/ProjectList.vue')
            },
            {
                path: 'app-automation/devices',
                name: 'AppDeviceList',
                component: () => import('@/views/app-automation/devices/DeviceList.vue')
            },
            {
                path: 'app-automation/devices/simulator',
                name: 'AppDeviceSimulator',
                component: () => import('@/views/app-automation/devices/DeviceSimulator.vue'),
                meta: { title: '手机模拟器' }
            },
            {
                path: 'app-automation/packages',
                name: 'AppPackageList',
                component: () => import('@/views/app-automation/packages/PackageList.vue')
            },
            {
                path: 'app-automation/elements',
                name: 'AppElementList',
                component: () => import('@/views/app-automation/elements/ElementList.vue')
            },
            {
                path: 'app-automation/scene-builder',
                name: 'AppSceneBuilder',
                component: () => import('@/views/app-automation/test-cases/SceneBuilder.vue'),
                meta: { title: '用例编排' }
            },
            {
                path: 'app-automation/test-cases',
                name: 'AppTestCaseList',
                component: () => import('@/views/app-automation/test-cases/TestCaseList.vue')
            },
            {
                path: 'app-automation/test-suites',
                name: 'AppTestSuiteList',
                component: () => import('@/views/app-automation/suites/SuiteList.vue')
            },
            {
                path: 'app-automation/scheduled-tasks',
                name: 'AppScheduledTasks',
                component: () => import('@/views/app-automation/scheduled-tasks/ScheduledTasks.vue')
            },
            {
                path: 'app-automation/notification-logs',
                name: 'AppNotificationLogs',
                component: () => import('@/views/app-automation/notification/NotificationLogs.vue')
            },
            {
                path: 'app-automation/executions',
                name: 'AppExecutionList',
                component: () => import('@/views/app-automation/executions/ExecutionList.vue')
            },
            {
                path: 'app-automation/reports',
                name: 'AppReportList',
                component: () => import('@/views/app-automation/reports/ReportList.vue')
            },
        ]
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// ============================================================
// 路由级稳定性守护
// ------------------------------------------------------------
// 修复的核心问题：某些页面出错后其他按钮点击无响应/不跳转
// 关键手段：
// 1. beforeEach 触发时先清理泄漏遮罩（"卡死感"最常见来源）
// 2. router.onError 兜底动态导入失败、组件挂载异常
// 3. isNavigationFailure 甄别"重复导航/被取消"这些无害失败
// 4. 页面切换后强制解锁 body 滚动，避免弹窗残留锁死
// ============================================================

router.beforeEach((to, from, next) => {
    // 切换路由前，先清理上个页面可能残留的遮罩/加载态
    try {
        purgeOrphanOverlays()
    } catch (e) {
        reportError('router-before-purge', e)
    }
    next()
})

router.afterEach((to, from, failure) => {
    // 埋点
    try {
        trackPageView(to, from)
    } catch (e) {
        reportError('tracker', e)
    }

    // 二次兜底：切换完成后再清理一次
    try {
        purgeOrphanOverlays()
        // 强制解锁 body（防止 ElDialog 关闭时残留 el-popup-parent--hidden）
        document.body.classList.remove('el-popup-parent--hidden')
        if (!document.querySelector('.el-overlay, .el-dialog')) {
            document.body.style.overflow = ''
            document.body.style.paddingRight = ''
        }
    } catch (e) {
        reportError('router-after-purge', e)
    }

    // 处理导航失败：重复导航等无害情况静默忽略，其他记录日志
    if (failure) {
        const isHarmless =
            isNavigationFailure(failure, NavigationFailureType.duplicated) ||
            isNavigationFailure(failure, NavigationFailureType.cancelled) ||
            isNavigationFailure(failure, NavigationFailureType.aborted)

        if (!isHarmless) {
            reportError('router-navigation-fail', failure, {
                from: from.fullPath,
                to: to.fullPath,
            })
        }
    }
})

// 路由级异常兜底：动态 import() 组件加载失败（chunk 缺失、网络断）
router.onError((err, to) => {
    reportError('router-error', err, { to: to?.fullPath })
    purgeOrphanOverlays()

    // 常见场景：新版本部署后旧页面加载缺失 chunk
    const msg = err?.message || ''
    if (
        /Failed to fetch dynamically imported module/i.test(msg) ||
        /Loading chunk .* failed/i.test(msg) ||
        /Importing a module script failed/i.test(msg)
    ) {
        ElMessage.warning('检测到页面资源已更新，即将刷新以加载最新版本')
        // 稍作延迟让用户看到提示
        setTimeout(() => {
            window.location.href = to?.fullPath || window.location.pathname
        }, 1200)
        return
    }

    // 其他错误：温和提示，不阻塞用户
    ElMessage.error('页面加载异常，请稍后重试或返回首页')
})

export default router
