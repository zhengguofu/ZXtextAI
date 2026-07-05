from django.urls import path
from . import views

urlpatterns = [
    # 测试用例相关
    path('', views.TestCaseListCreateView.as_view(), name='testcase-list'),
    path('<int:pk>/', views.TestCaseDetailView.as_view(), name='testcase-detail'),
    # 批量删除测试用例
    path('batch-delete/', views.batch_delete_testcases, name='testcase-batch-delete'),
]