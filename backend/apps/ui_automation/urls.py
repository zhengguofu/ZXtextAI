from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .views import (
    UiProjectViewSet,
    LocatorStrategyViewSet,
    ElementGroupViewSet,
    ElementViewSet,
    TestScriptViewSet,
    PageObjectViewSet,
    ScriptStepViewSet,
    TestSuiteViewSet,
    TestExecutionViewSet,
    ScreenshotViewSet,
    TestCaseViewSet,
    TestCaseStepViewSet,
    TestCaseExecutionViewSet,
    UiScheduledTaskViewSet,
    AIExecutionRecordViewSet,
    AICaseViewSet,
    UiNotificationLogViewSet,
    OperationRecordViewSet,
    UiDashboardViewSet,
)
from .automation_views import (
    AutomationExecutionViewSet,
    ExecutionEvidenceViewSet,
    ExecutionLogViewSet,
)
from .views_config import EnvironmentConfigViewSet, EnvironmentAutoSetupViewSet, AIIntelligentModeConfigViewSet
from .asset_center_views import (
    list_assets,
    delete_asset,
    batch_delete_assets,
    clean_artifacts_directory,
    artifacts_stats,
)

router = DefaultRouter()
router.register(r'dashboard', UiDashboardViewSet, basename='dashboard')
router.register(r'projects', UiProjectViewSet)
router.register(r'locator-strategies', LocatorStrategyViewSet)
router.register(r'element-groups', ElementGroupViewSet)
router.register(r'elements', ElementViewSet)
router.register(r'test-scripts', TestScriptViewSet)
router.register(r'page-objects', PageObjectViewSet)
router.register(r'steps', ScriptStepViewSet)
router.register(r'test-suites', TestSuiteViewSet)
router.register(r'test-executions', TestExecutionViewSet)
router.register(r'screenshots', ScreenshotViewSet)
router.register(r'test-cases', TestCaseViewSet)
router.register(r'test-case-steps', TestCaseStepViewSet)
router.register(r'test-case-executions', TestCaseExecutionViewSet)
router.register(r'scheduled-tasks', UiScheduledTaskViewSet)
router.register(r'ai-execution-records', AIExecutionRecordViewSet)
router.register(r'ai-cases', AICaseViewSet, basename='ai-cases')
router.register(r'ai-case-generation', AICaseViewSet, basename='ai-case-generation')
router.register(r'notification-logs', UiNotificationLogViewSet)
router.register(r'operation-records', OperationRecordViewSet)

# 自动化执行API
router.register(r'automation-executions', AutomationExecutionViewSet, basename='automation-executions')
router.register(r'execution-evidences', ExecutionEvidenceViewSet, basename='execution-evidences')
router.register(r'execution-logs', ExecutionLogViewSet, basename='execution-logs')


# Configuration Center APIs
router.register(r'config/environment', EnvironmentConfigViewSet, basename='config-environment')
router.register(r'config/environment/auto-setup', EnvironmentAutoSetupViewSet, basename='config-environment-auto-setup')
router.register(r'config/ai-mode', AIIntelligentModeConfigViewSet, basename='config-ai-mode')
router.register(r'ai-models', AIIntelligentModeConfigViewSet, basename='ai-models')

urlpatterns = [
    path('', include(router.urls)),

    # 资产中心统一管理API
    path('assets/list/', list_assets, name='asset-list'),
    path('assets/delete/', delete_asset, name='asset-delete'),
    path('assets/batch_delete/', batch_delete_assets, name='asset-batch-delete'),
    path('assets/clean_artifacts/', clean_artifacts_directory, name='asset-clean-artifacts'),
    path('assets/artifacts_stats/', artifacts_stats, name='asset-artifacts-stats'),
]

# 添加媒体文件路由
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)