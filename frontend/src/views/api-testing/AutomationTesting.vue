<template>
  <div class="automation-testing">
    <div class="header">
      <div class="header-left">
        <h3>{{ $t('apiTesting.automation.title') }}</h3>
        <span class="subtitle">管理和执行自动化测试套件</span>
      </div>
      <div class="header-actions">
        <el-button @click="showTestPlanDialog = true" class="plan-btn">
          <el-icon><Calendar /></el-icon>
          测试计划
        </el-button>
        <el-button type="primary" @click="showCreateSuiteDialog = true">
          <el-icon><Plus /></el-icon>
          {{ $t('apiTesting.automation.createSuite') }}
        </el-button>
      </div>
    </div>

    <div class="content-layout">
      <!-- 左侧面板 -->
      <div class="sidebar">
        <div class="project-selector">
          <div class="selector-header">
            <el-icon><OfficeBuilding /></el-icon>
            <span>项目</span>
          </div>
          <el-select
            v-model="selectedProject"
            :placeholder="$t('apiTesting.common.selectProject')"
            @change="onProjectChange"
            class="project-select"
          >
            <el-option
              v-for="project in httpProjects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </div>
        
        <!-- 环境选择 -->
        <div class="environment-selector">
          <div class="selector-header">
            <el-icon><Setting /></el-icon>
            <span>环境</span>
          </div>
          <el-select
            v-model="selectedEnvironment"
            :placeholder="t('apiTesting.automation.selectEnvironment')"
            clearable
            class="env-select"
          >
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </div>

        <div class="suite-list">
          <div class="list-header">
            <span>{{ $t('apiTesting.automation.testSuites') }}</span>
            <div class="list-actions">
              <el-button size="small" text @click="loadTestSuites">
                <el-icon><Refresh /></el-icon>
              </el-button>
              <el-button size="small" text @click="batchDeleteSuites" :disabled="selectedSuites.length === 0">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          
          <el-scrollbar height="calc(100vh - 420px)">
            <div
              v-for="suite in testSuites"
              :key="suite.id"
              class="suite-item"
              :class="{ active: selectedSuite?.id === suite.id, selected: selectedSuites.includes(suite.id) }"
              @click="selectSuite(suite)"
              @click.stop="toggleSuiteSelection(suite.id)"
            >
              <div class="suite-checkbox">
                <el-checkbox v-model="suite.selected" @change="handleSuiteCheckbox(suite)" />
              </div>
              <div class="suite-info">
                <div class="suite-name-row">
                  <el-icon class="suite-icon"><Files /></el-icon>
                  <span class="suite-name">{{ suite.name }}</span>
                  <el-tag v-if="suite.status === 'RUNNING'" size="mini" type="warning">运行中</el-tag>
                </div>
                <div class="suite-meta">
                  <span>{{ suite.suite_requests?.length || 0 }} 个请求</span>
                  <span class="meta-divider">|</span>
                  <span>{{ formatDate(suite.created_at) }}</span>
                </div>
                <div class="suite-stats">
                  <span class="stat passed">{{ getSuitePassRate(suite) }}% 通过</span>
                </div>
              </div>
              <el-dropdown @command="handleSuiteAction" trigger="click">
                <el-button size="small" text class="action-btn">
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :command="{ action: 'run', suite }">{{ $t('apiTesting.automation.run') }}</el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'edit', suite }">{{ $t('apiTesting.common.edit') }}</el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'duplicate', suite }">{{ $t('apiTesting.common.copy') }}</el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'export', suite }">导出</el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'delete', suite }" divided>{{ $t('apiTesting.common.delete') }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </el-scrollbar>
        </div>
      </div>

      <!-- 右侧主内容 -->
      <div class="main-content">
        <div v-if="!selectedSuite" class="empty-state">
          <div class="empty-icon">
            <el-icon><Grid /></el-icon>
          </div>
          <h3>选择一个测试套件</h3>
          <p>从左侧列表选择或创建新的测试套件开始测试</p>
        </div>
        
        <div v-else class="suite-detail">
          <!-- 套件信息和操作栏 -->
          <div class="suite-header">
            <div class="suite-title-section">
              <div class="suite-icon-wrapper">
                <el-icon class="suite-icon-lg"><Files /></el-icon>
              </div>
              <div class="suite-info-main">
                <h2>{{ selectedSuite.name }}</h2>
                <p class="suite-desc">{{ selectedSuite.description || '暂无描述' }}</p>
              </div>
            </div>
            <div class="suite-actions-bar">
              <el-button type="success" @click="runTestSuite(selectedSuite)" :loading="running" class="run-btn">
                <el-icon><Play /></el-icon>
                运行测试
              </el-button>
              <el-button @click="editSuite(selectedSuite)">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button @click="exportSuite(selectedSuite)">
                <el-icon><Download /></el-icon>
                导出
              </el-button>
              <el-dropdown @command="handleQuickAction">
                <el-button>
                  <el-icon><MoreFilled /></el-icon>
                  更多
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="run-all">运行全部请求</el-dropdown-item>
                    <el-dropdown-item command="run-failed">仅运行失败的请求</el-dropdown-item>
                    <el-dropdown-item command="clear-history">清除执行历史</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>

          <!-- 统计卡片 -->
          <div class="stats-cards">
            <div class="stat-card">
              <div class="stat-icon requests">
                <el-icon><List /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ selectedSuite.suite_requests?.length || 0 }}</div>
                <div class="stat-label">测试请求</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon assertions">
                <el-icon><CircleCheck /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ totalAssertions }}</div>
                <div class="stat-label">断言总数</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon passed">
                <el-icon><Star /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ lastPassRate }}%</div>
                <div class="stat-label">上次通过率</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon executions">
                <el-icon><Clock /></el-icon>
              </div>
              <div class="stat-content">
                <div class="stat-value">{{ executions.length }}</div>
                <div class="stat-label">执行次数</div>
              </div>
            </div>
          </div>

          <!-- 标签页 -->
          <el-tabs v-model="activeTab" class="main-tabs">
            <!-- 请求列表 -->
            <el-tab-pane label="测试请求" name="requests">
              <div class="tab-content">
                <div class="tab-header">
                  <h4>{{ $t('apiTesting.automation.testRequests') }}</h4>
                  <div class="tab-actions">
                    <el-button size="small" @click="showAddRequest">
                      <el-icon><Plus /></el-icon>
                      {{ $t('apiTesting.automation.addRequest') }}
                    </el-button>
                    <el-button size="small" @click="batchEnableRequests" :disabled="selectedRequests.length === 0">
                      <el-icon><Check /></el-icon>
                      批量启用
                    </el-button>
                    <el-button size="small" @click="batchDisableRequests" :disabled="selectedRequests.length === 0">
                      <el-icon><Close /></el-icon>
                      批量禁用
                    </el-button>
                  </div>
                </div>
                
                <el-table 
                  :data="selectedSuite.suite_requests" 
                  style="width: 100%"
                  :row-key="(row) => row.id"
                  @selection-change="handleRequestSelectionChange"
                >
                  <el-table-column type="selection" width="55" />
                  <el-table-column type="index" label="#" width="50" />
                  <el-table-column prop="request.name" :label="$t('apiTesting.automation.requestName')" min-width="200">
                    <template #default="scope">
                      <div class="request-name-cell">
                        <el-icon><Document /></el-icon>
                        <span>{{ scope.row.request.name }}</span>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column prop="request.method" :label="$t('apiTesting.automation.method')" width="80">
                    <template #default="scope">
                      <el-tag :type="getMethodType(scope.row.request.method)" size="small">
                        {{ scope.row.request.method }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="request.url" label="URL" min-width="300" show-overflow-tooltip />
                  <el-table-column prop="enabled" :label="$t('apiTesting.automation.enabled')" width="80">
                    <template #default="scope">
                      <el-switch
                        v-model="scope.row.enabled"
                        @change="updateRequestEnabled(scope.row)"
                      />
                    </template>
                  </el-table-column>
                  <el-table-column :label="$t('apiTesting.automation.assertions')" width="100">
                    <template #default="scope">
                      <el-tag size="small" type="info">
                        {{ scope.row.assertions?.length || 0 }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column :label="$t('apiTesting.automation.delay')" width="80">
                    <template #default="scope">
                      {{ scope.row.delay || 0 }}ms
                    </template>
                  </el-table-column>
                  <el-table-column :label="$t('apiTesting.common.operation')" width="180">
                    <template #default="scope">
                      <el-button link type="primary" @click="editRequestOrder(scope.row)" size="small">
                        <el-icon><ArrowUp /></el-icon>
                        排序
                      </el-button>
                      <el-button link type="primary" @click="editAssertions(scope.row)" size="small">
                        <el-icon><Edit /></el-icon>
                        断言
                      </el-button>
                      <el-button link type="danger" @click="removeRequest(scope.row)" size="small">
                        <el-icon><Delete /></el-icon>
                        删除
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-tab-pane>

            <!-- 执行历史 -->
            <el-tab-pane label="执行历史" name="history">
              <div class="tab-content">
                <div class="tab-header">
                  <h4>{{ $t('apiTesting.automation.executionHistory') }}</h4>
                  <el-button size="small" @click="loadExecutions">
                    <el-icon><Refresh /></el-icon>
                    {{ $t('apiTesting.automation.refresh') }}
                  </el-button>
                </div>

                <el-table :data="executions" v-loading="executionsLoading" :row-key="(row) => row.id">
                  <el-table-column prop="status" :label="$t('apiTesting.common.status')" width="100">
                    <template #default="scope">
                      <el-tag :type="getStatusType(scope.row.status)">
                        {{ getStatusText(scope.row.status) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="total_requests" :label="$t('apiTesting.automation.totalRequests')" width="80" />
                  <el-table-column :label="$t('apiTesting.automation.passRate')" width="100">
                    <template #default="scope">
                      <div class="pass-rate-cell">
                        <div class="pass-rate-bar">
                          <div 
                            class="pass-rate-fill" 
                            :style="{ width: getPassRate(scope.row) + '%' }"
                            :class="getPassRateClass(scope.row)"
                          ></div>
                        </div>
                        <span class="pass-rate-text" :class="getPassRateClass(scope.row)">
                          {{ getPassRate(scope.row) }}%
                        </span>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column :label="$t('apiTesting.automation.responseTime')" width="120">
                    <template #default="scope">
                      {{ getAverageExecutionTime(scope.row) }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="executed_by.username" :label="$t('apiTesting.automation.executor')" width="100" />
                  <el-table-column prop="created_at" :label="$t('apiTesting.automation.executionTime')" width="160">
                    <template #default="scope">
                      {{ formatDate(scope.row.created_at) }}
                    </template>
                  </el-table-column>
                  <el-table-column :label="$t('apiTesting.common.operation')" width="150">
                    <template #default="scope">
                      <el-button link type="primary" @click="viewExecutionDetail(scope.row)" size="small">
                        <el-icon><View /></el-icon>
                        详情
                      </el-button>
                      <el-button link type="success" @click="replayExecution(scope.row)" size="small">
                        <el-icon><Refresh /></el-icon>
                        重放
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-tab-pane>

            <!-- 测试报告 -->
            <el-tab-pane label="测试报告" name="report">
              <div class="tab-content">
                <div v-if="!latestExecution" class="no-report">
                  <el-empty description="暂无测试报告，请先运行测试套件" />
                </div>
                <div v-else class="report-content">
                  <div class="report-header">
                    <div class="report-title">
                      <h4>测试报告</h4>
                      <span class="report-date">{{ formatDate(latestExecution.created_at) }}</span>
                    </div>
                    <div class="report-actions">
                      <el-button @click="exportReport">
                        <el-icon><Download /></el-icon>
                        导出报告
                      </el-button>
                    </div>
                  </div>
                  
                  <div class="report-summary">
                    <div class="summary-row">
                      <div class="summary-item total">
                        <div class="summary-value">{{ latestExecution.total_requests }}</div>
                        <div class="summary-label">总请求数</div>
                      </div>
                      <div class="summary-item passed">
                        <div class="summary-value">{{ latestExecution.passed_requests }}</div>
                        <div class="summary-label">通过</div>
                      </div>
                      <div class="summary-item failed">
                        <div class="summary-value">{{ latestExecution.failed_requests }}</div>
                        <div class="summary-label">失败</div>
                      </div>
                      <div class="summary-item rate">
                        <div class="summary-value">{{ getPassRate(latestExecution) }}%</div>
                        <div class="summary-label">通过率</div>
                      </div>
                      <div class="summary-item time">
                        <div class="summary-value">{{ getExecutionDuration(latestExecution) }}</div>
                        <div class="summary-label">总耗时</div>
                      </div>
                    </div>
                    
                    <div class="chart-section">
                      <div class="chart-title">执行结果分布</div>
                      <div class="pie-chart">
                        <div 
                          class="pie-slice passed" 
                          :style="{ transform: `rotate(0deg)`, clipPath: getPassClipPath(latestExecution) }"
                        ></div>
                        <div 
                          class="pie-slice failed" 
                          :style="{ transform: `rotate(${getPassAngle(latestExecution)}deg)` }"
                        ></div>
                        <div class="pie-center">
                          <div class="pie-value">{{ getPassRate(latestExecution) }}%</div>
                          <div class="pie-label">通过率</div>
                        </div>
                      </div>
                      <div class="chart-legend">
                        <div class="legend-item">
                          <span class="legend-color passed"></span>
                          <span>通过 {{ latestExecution.passed_requests }}</span>
                        </div>
                        <div class="legend-item">
                          <span class="legend-color failed"></span>
                          <span>失败 {{ latestExecution.failed_requests }}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="report-details">
                    <h5>执行详情</h5>
                    <div class="results-list">
                      <div 
                        v-for="(result, index) in formatExecutionResults(latestExecution.results)" 
                        :key="index"
                        class="result-item"
                        :class="{ passed: result.passed, failed: !result.passed }"
                      >
                        <div class="result-header">
                          <div class="result-index">{{ index + 1 }}</div>
                          <div class="result-info">
                            <span class="result-name">{{ result.name }}</span>
                            <el-tag :type="getMethodType(result.method)" size="small">{{ result.method }}</el-tag>
                          </div>
                          <div class="result-status">
                            <el-icon v-if="result.passed" class="success-icon"><CircleCheck /></el-icon>
                            <el-icon v-else class="error-icon"><CircleClose /></el-icon>
                            <span>{{ result.passed ? '通过' : '失败' }}</span>
                          </div>
                        </div>
                        <div class="result-url">{{ result.url }}</div>
                        <div class="result-meta">
                          <span>状态码: {{ result.status_code }}</span>
                          <span>耗时: {{ result.response_time?.toFixed(0) }}ms</span>
                        </div>
                        <div v-if="!result.passed && result.error" class="result-error">
                          <strong>错误信息:</strong>
                          <p>{{ result.error }}</p>
                        </div>
                        <div v-if="result.assertions" class="result-assertions">
                          <strong>断言结果:</strong>
                          <div v-for="(assertion, idx) in result.assertions" :key="idx" class="assertion-item">
                            <el-icon :class="assertion.passed ? 'check' : 'x'">
                              {{ assertion.passed ? CircleCheck : CircleClose }}
                            </el-icon>
                            <span>{{ assertion.name }}: {{ assertion.actual }} {{ assertion.comparator }} {{ assertion.expected }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </div>

    <!-- 创建/编辑测试套件对话框 -->
    <el-dialog
      v-model="showCreateSuiteDialog"
      :title="editingSuite ? $t('apiTesting.automation.editSuite') : $t('apiTesting.automation.createSuite')"
      width="600px"
      :close-on-click-modal="false"
      @close="resetSuiteForm"
    >
      <el-form
        ref="suiteFormRef"
        :model="suiteForm"
        :rules="suiteRules"
        label-width="100px"
      >
        <el-form-item :label="$t('apiTesting.automation.suiteName')" prop="name">
          <el-input v-model="suiteForm.name" :placeholder="$t('apiTesting.automation.inputSuiteName')" />
        </el-form-item>

        <el-form-item :label="$t('apiTesting.automation.suiteDescription')" prop="description">
          <el-input
            v-model="suiteForm.description"
            type="textarea"
            :rows="3"
            :placeholder="$t('apiTesting.automation.inputSuiteDescription')"
          />
        </el-form-item>

        <el-form-item :label="$t('apiTesting.automation.belongProject')" prop="project">
          <el-select v-model="suiteForm.project" :placeholder="$t('apiTesting.automation.selectProject')">
            <el-option
              v-for="project in httpProjects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('apiTesting.automation.executionEnvironment')" prop="environment">
          <el-select v-model="suiteForm.environment" :placeholder="$t('apiTesting.automation.selectEnvironment')" clearable>
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="执行配置">
          <div class="form-row">
            <el-input 
              v-model="suiteForm.delay_between_requests" 
              type="number" 
              placeholder="请求间隔(ms)" 
              class="config-input"
            />
            <el-switch v-model="suiteForm.stop_on_failure" active-text="失败停止" inactive-text="继续执行" />
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreateSuiteDialog = false">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="submitSuiteForm" :loading="submittingSuite">
          {{ editingSuite ? $t('apiTesting.common.update') : $t('apiTesting.common.create') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 添加请求对话框 -->
    <el-dialog
      v-model="showAddRequestDialog"
      :title="$t('apiTesting.automation.addRequestToSuite')"
      width="800px"
      :close-on-click-modal="false"
    >
      <div class="add-request-content">
        <div class="request-tree-header">
          <el-input 
            v-model="requestSearch" 
            placeholder="搜索请求..." 
            class="search-input"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
        <div class="request-selector">
          <el-tree
            ref="requestTreeRef"
            :data="requestTree"
            :props="requestTreeProps"
            show-checkbox
            node-key="id"
            :check-on-click-node="false"
            filter-node-method="filterNode"
          >
            <template #default="{ node, data }">
              <div class="request-tree-node">
                <el-icon v-if="data.type === 'collection'">
                  <Folder />
                </el-icon>
                <el-icon v-else>
                  <Document />
                </el-icon>
                <span>{{ data.name }}</span>
                <span v-if="data.type === 'request'" class="method-tag" :class="data.method?.toLowerCase()">
                  {{ data.method }}
                </span>
              </div>
            </template>
          </el-tree>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="showAddRequestDialog = false">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="addSelectedRequests" :loading="addingRequests">
          {{ $t('apiTesting.automation.addSelectedRequests') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 执行结果对话框 -->
    <el-dialog
      v-model="showExecutionDialog"
      :title="$t('apiTesting.automation.testExecutionResult')"
      width="85%"
      :top="'5vh'"
      class="execution-dialog"
    >
      <div v-if="currentExecution" class="execution-detail">
        <div class="execution-header">
          <div class="execution-title">
            <h3>{{ currentExecution.test_suite_name }}</h3>
            <el-tag :type="getStatusType(currentExecution.status)">{{ getStatusText(currentExecution.status) }}</el-tag>
          </div>
          <div class="execution-meta">
            <span>{{ formatDate(currentExecution.created_at) }}</span>
            <span>|</span>
            <span>执行者: {{ currentExecution.executed_by?.username }}</span>
          </div>
        </div>

        <div class="execution-summary-grid">
          <div class="summary-card">
            <div class="summary-icon total">
              <el-icon><List /></el-icon>
            </div>
            <div class="summary-info">
              <div class="summary-num">{{ currentExecution.total_requests }}</div>
              <div class="summary-text">总请求</div>
            </div>
          </div>
          <div class="summary-card">
            <div class="summary-icon passed">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="summary-info">
              <div class="summary-num passed">{{ currentExecution.passed_requests }}</div>
              <div class="summary-text">通过</div>
            </div>
          </div>
          <div class="summary-card">
            <div class="summary-icon failed">
              <el-icon><CircleClose /></el-icon>
            </div>
            <div class="summary-info">
              <div class="summary-num failed">{{ currentExecution.failed_requests }}</div>
              <div class="summary-text">失败</div>
            </div>
          </div>
          <div class="summary-card">
            <div class="summary-icon rate">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <div class="summary-info">
              <div class="summary-num">{{ getPassRate(currentExecution) }}%</div>
              <div class="summary-text">通过率</div>
            </div>
          </div>
        </div>

        <div class="execution-results-section">
          <div class="section-header">
            <h4>执行详情</h4>
            <div class="filter-tabs">
              <el-button 
                :class="{ active: resultFilter === 'all' }" 
                @click="resultFilter = 'all'"
              >全部</el-button>
              <el-button 
                :class="{ active: resultFilter === 'failed' }" 
                @click="resultFilter = 'failed'"
              >仅失败</el-button>
              <el-button 
                :class="{ active: resultFilter === 'passed' }" 
                @click="resultFilter = 'passed'"
              >仅通过</el-button>
            </div>
          </div>

          <div class="results-container">
            <div 
              v-for="(result, index) in filteredResults" 
              :key="index"
              class="result-card"
              :class="{ passed: result.passed, failed: !result.passed }"
            >
              <div class="result-card-header">
                <div class="result-index-badge">{{ index + 1 }}</div>
                <div class="result-card-info">
                  <div class="result-card-title">
                    <span>{{ result.name }}</span>
                    <el-tag :type="getMethodType(result.method)" size="small">{{ result.method }}</el-tag>
                  </div>
                  <div class="result-card-url">{{ result.url }}</div>
                </div>
                <div class="result-card-status">
                  <el-icon :class="result.passed ? 'success' : 'error'">
                    {{ result.passed ? CircleCheck : CircleClose }}
                  </el-icon>
                  <span>{{ result.passed ? '通过' : '失败' }}</span>
                </div>
              </div>
              
              <div class="result-card-body">
                <div class="result-metrics">
                  <span class="metric">
                    <el-icon><Clock /></el-icon>
                    {{ result.response_time?.toFixed(0) }}ms
                  </span>
                  <span class="metric">
                    <el-icon><PriceTag /></el-icon>
                    {{ result.status_code }}
                  </span>
                  <span class="metric">
                    <el-icon><DataAnalysis /></el-icon>
                    {{ formatSize(result.response_size) }}
                  </span>
                </div>

                <div v-if="!result.passed && result.error" class="result-error-box">
                  <div class="error-header">
                    <el-icon><Warning /></el-icon>
                    <span>错误信息</span>
                  </div>
                  <pre class="error-content">{{ result.error }}</pre>
                </div>

                <div v-if="result.assertions && result.assertions.length > 0" class="result-assertions-box">
                  <div class="assertions-header">
                    <el-icon><Checked /></el-icon>
                    <span>断言结果</span>
                  </div>
                  <div class="assertions-list">
                    <div 
                      v-for="(assertion, idx) in result.assertions" 
                      :key="idx"
                      class="assertion-row"
                      :class="{ passed: assertion.passed, failed: !assertion.passed }"
                    >
                      <el-icon :class="assertion.passed ? 'check' : 'x'">
                        {{ assertion.passed ? CircleCheck : CircleClose }}
                      </el-icon>
                      <span class="assertion-name">{{ assertion.name }}</span>
                      <span class="assertion-detail">
                        实际: {{ formatAssertionValue(assertion.actual) }}
                        {{ assertion.comparator }}
                        预期: {{ formatAssertionValue(assertion.expected) }}
                      </span>
                    </div>
                  </div>
                </div>

                <div v-if="result.response_body" class="result-response-box">
                  <div class="response-header">
                    <el-icon><Files /></el-icon>
                    <span>响应体</span>
                    <el-button size="small" @click="copyResponse(result.response_body)">复制</el-button>
                  </div>
                  <pre class="response-content">{{ formatJson(result.response_body) }}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showExecutionDialog = false">{{ $t('apiTesting.common.close') }}</el-button>
        <el-button type="primary" @click="replayExecution(currentExecution)">
          <el-icon><Refresh /></el-icon>
          重新执行
        </el-button>
      </template>
    </el-dialog>

    <!-- 测试计划对话框 -->
    <el-dialog
      v-model="showTestPlanDialog"
      title="测试计划"
      width="600px"
      :close-on-click-modal="false"
    >
      <div class="plan-content">
        <div class="plan-list">
          <div v-if="testPlans.length === 0" class="empty-plan">
            <el-empty description="暂无测试计划" />
          </div>
          <div v-for="plan in testPlans" :key="plan.id" class="plan-item">
            <div class="plan-info">
              <h4>{{ plan.name }}</h4>
              <p>{{ plan.cron_expression }}</p>
              <span class="plan-status" :class="plan.enabled ? 'active' : 'disabled'">
                {{ plan.enabled ? '启用' : '禁用' }}
              </span>
            </div>
            <el-dropdown @command="(cmd) => handlePlanAction(cmd, plan)">
              <el-button size="small" text><el-icon><MoreFilled /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-item :command="'edit'">编辑</el-dropdown-item>
                <el-dropdown-item :command="'delete'">删除</el-dropdown-item>
              </template>
            </el-dropdown>
          </div>
        </div>
        <el-button type="primary" @click="createTestPlan" class="create-plan-btn">
          <el-icon><Plus /></el-icon>
          创建测试计划
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>import { ref, reactive, onMounted, computed, nextTick } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { Plus, Refresh, MoreFilled, VideoPlay, Edit, Folder, Document, Calendar, OfficeBuilding, Setting, Download, Clock, List, CircleCheck, CircleClose, Delete, Check, Close, Search, PriceTag, DataAnalysis, TrendCharts, Checked, Star, View, ArrowUp, ArrowDown, Warning, Files, Grid } from '@element-plus/icons-vue';
import api from '@/utils/api';
import dayjs from 'dayjs';
const { t } = useI18n();
const projects = ref([]);
const selectedProject = ref(null);
const selectedEnvironment = ref(null);
const testSuites = ref([]);
const selectedSuite = ref(null);
const selectedSuites = ref([]);
const selectedRequests = ref([]);
const executions = ref([]);
const environments = ref([]);
const requestTree = ref([]);
const testPlans = ref([]);
const running = ref(false);
const executionsLoading = ref(false);
const showCreateSuiteDialog = ref(false);
const showAddRequestDialog = ref(false);
const showExecutionDialog = ref(false);
const showTestPlanDialog = ref(false);
const editingSuite = ref(null);
const submittingSuite = ref(false);
const addingRequests = ref(false);
const currentExecution = ref(null);
const activeTab = ref('requests');
const resultFilter = ref('all');
const requestSearch = ref('');
const suiteFormRef = ref();
const requestTreeRef = ref();
const suiteForm = reactive({
 name: '',
 description: '',
 project: null,
 environment: null,
 delay_between_requests: 0,
 stop_on_failure: false
});
const suiteRules = computed(() => ({
 name: [{ required: true, message: t('apiTesting.automation.inputSuiteName'), trigger: 'blur' }],
 project: [{ required: true, message: t('apiTesting.automation.selectProject'), trigger: 'change' }]
}));
const requestTreeProps = {
 children: 'children',
 label: 'name'
};
const httpProjects = computed(() => {
 return projects.value.filter(project => project.project_type !== 'WEBSOCKET');
});
const totalAssertions = computed(() => {
 if (!selectedSuite.value?.suite_requests)
 return 0;
 return selectedSuite.value.suite_requests.reduce((sum, sr) => sum + (sr.assertions?.length || 0), 0);
});
const lastPassRate = computed(() => {
 if (!selectedSuite.value)
 return 0;
 const latest = executions.value[0];
 if (!latest)
 return 0;
 return getPassRate(latest);
});
const latestExecution = computed(() => {
 return executions.value[0] || null;
});
const filteredResults = computed(() => {
 if (!currentExecution.value?.results)
 return [];
 let results = formatExecutionResults(currentExecution.value.results);
 switch (resultFilter.value) {
 case 'passed':
 return results.filter(r => r.passed);
 case 'failed':
 return results.filter(r => !r.passed);
 default:
 return results;
 }
});
const getMethodType = (method) => {
 const typeMap = {
 'GET': 'success',
 'POST': 'primary',
 'PUT': 'warning',
 'DELETE': 'danger',
 'PATCH': 'info'
 };
 return typeMap[method] || 'info';
};
const getStatusType = (status) => {
 const typeMap = {
 'PENDING': 'info',
 'RUNNING': 'warning',
 'COMPLETED': 'success',
 'FAILED': 'danger',
 'CANCELLED': 'info'
 };
 return typeMap[status] || 'info';
};
const getStatusText = (status) => {
 const statusKey = {
 'PENDING': 'pending',
 'RUNNING': 'running',
 'COMPLETED': 'completed',
 'FAILED': 'failed',
 'CANCELLED': 'cancelled'
 }[status];
 return statusKey ? t(`apiTesting.automation.status.${statusKey}`) : status;
};
const formatDate = (dateString) => {
 if (!dateString)
 return '-';
 return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss');
};
const getAverageExecutionTime = (execution) => {
 if (!execution.results || !Array.isArray(execution.results) || execution.results.length === 0) {
 return '-';
 }
 const totalResponseTime = execution.results.reduce((sum, result) => sum + (result.response_time || 0), 0);
 const averageTime = totalResponseTime / execution.results.length;
 if (averageTime < 1000) {
 return `${Math.round(averageTime)}ms`;
 }
 else {
 return `${(averageTime / 1000).toFixed(1)}s`;
 }
};
const getPassRate = (execution) => {
 if (execution.total_requests === 0)
 return 0;
 return ((execution.passed_requests / execution.total_requests) * 100).toFixed(1);
};
const getPassRateClass = (execution) => {
 const rate = parseFloat(getPassRate(execution));
 if (rate >= 90)
 return 'high';
 if (rate >= 70)
 return 'medium';
 return 'low';
};
const getSuitePassRate = (suite) => {
 if (!suite.last_execution)
 return 0;
 return getPassRate(suite.last_execution);
};
const getEnvironmentName = (environmentId) => {
 if (!environmentId)
 return t('apiTesting.automation.noEnvironment');
 const env = environments.value.find(e => e.id === environmentId);
 return env ? env.name : t('apiTesting.automation.noEnvironment');
};
const getExecutionDuration = (execution) => {
 if (!execution.start_time || !execution.end_time)
 return '-';
 const start = dayjs(execution.start_time);
 const end = dayjs(execution.end_time);
 const diff = end.diff(start);
 if (diff < 1000)
 return `${diff}ms`;
 if (diff < 60000)
 return `${(diff / 1000).toFixed(1)}s`;
 return `${(diff / 60000).toFixed(1)}m`;
};
const getPassAngle = (execution) => {
 const rate = parseFloat(getPassRate(execution));
 return (rate / 100) * 360;
};
const getPassClipPath = (execution) => {
 const rate = parseFloat(getPassRate(execution));
 if (rate <= 50) {
 const angle = (rate / 100) * 360;
 return `polygon(50% 50%, 50% 0%, 100% 0%, 100% 100%, 0% 100%, 0% 0%, 50% 0%)`;
 }
 else {
 return 'none';
 }
};
const formatSize = (bytes) => {
 if (!bytes || bytes === 0)
 return '0B';
 const k = 1024;
 const sizes = ['B', 'KB', 'MB', 'GB'];
 const i = Math.floor(Math.log(bytes) / Math.log(k));
 return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + sizes[i];
};
const formatJson = (data) => {
 if (typeof data === 'string') {
 try {
 return JSON.stringify(JSON.parse(data), null, 2);
 }
 catch {
 return data;
 }
 }
 return JSON.stringify(data, null, 2);
};
const formatAssertionValue = (value) => {
 if (value === null)
 return 'null';
 if (value === undefined)
 return 'undefined';
 if (typeof value === 'object')
 return JSON.stringify(value);
 return String(value);
};
const loadProjects = async () => {
 try {
 const response = await api.get('/api-testing/projects/');
 projects.value = response.data.results || response.data;
 const httpProjects = projects.value.filter(project => project.project_type !== 'WEBSOCKET');
 if (httpProjects.length > 0 && !selectedProject.value) {
 selectedProject.value = httpProjects[0].id;
 await onProjectChange();
 }
 else if (httpProjects.length === 0) {
 selectedProject.value = null;
 }
 }
 catch (error) {
 ElMessage.error(t('apiTesting.messages.error.loadProjects'));
 }
};
const loadTestSuites = async () => {
 if (!selectedProject.value)
 return;
 try {
 const response = await api.get('/api-testing/test-suites/', {
 params: { project: selectedProject.value }
 });
 testSuites.value = response.data.results || response.data;
 }
 catch (error) {
 ElMessage.error(t('apiTesting.messages.error.loadTestSuites'));
 }
};
const loadEnvironments = async () => {
 try {
 const response = await api.get('/api-testing/environments/');
 const allEnvironments = response.data.results || response.data;
 environments.value = allEnvironments.filter(env => env.scope === 'GLOBAL' ||
 (env.scope === 'LOCAL' && (!selectedProject.value || env.project === selectedProject.value)));
 }
 catch (error) {
 ElMessage.error(t('apiTesting.messages.error.loadEnvironments'));
 }
};
const loadRequestTree = async () => {
 if (!selectedProject.value)
 return;
 try {
 const collectionsRes = await api.get('/api-testing/collections/', {
 params: { project: selectedProject.value }
 });
 const collections = collectionsRes.data.results || collectionsRes.data;
 const requestsRes = await api.get('/api-testing/requests/', {
 params: { project: selectedProject.value }
 });
 const requests = requestsRes.data.results || requestsRes.data;
 requestTree.value = buildRequestTree(collections, requests);
 }
 catch (error) {
 ElMessage.error(t('apiTesting.messages.error.loadRequestTree'));
 }
};
const loadTestPlans = async () => {
 try {
 const response = await api.get('/api-testing/test-plans/', {
 params: { project: selectedProject.value }
 });
 testPlans.value = response.data.results || response.data;
 }
 catch (error) {
 console.error('加载测试计划失败:', error);
 }
};
const buildRequestTree = (collections, requests) => {
 const map = {};
 const roots = [];
 collections.forEach(collection => {
 map[collection.id] = {
 ...collection,
 type: 'collection',
 children: []
 };
 });
 collections.forEach(collection => {
 if (collection.parent && map[collection.parent]) {
 map[collection.parent].children.push(map[collection.id]);
 }
 else {
 roots.push(map[collection.id]);
 }
 });
 requests.forEach(request => {
 if (map[request.collection]) {
 map[request.collection].children.push({
 ...request,
 type: 'request',
 id: `request_${request.id}`
 });
 }
 else {
 roots.push({
 ...request,
 type: 'request',
 id: `request_${request.id}`
 });
 }
 });
 return roots;
};
const loadExecutions = async () => {
 if (!selectedSuite.value)
 return;
 executionsLoading.value = true;
 try {
 const response = await api.get('/api-testing/test-executions/', {
 params: { test_suite: selectedSuite.value.id }
 });
 executions.value = response.data.results || response.data;
 }
 catch (error) {
 ElMessage.error(t('apiTesting.messages.error.loadExecutionHistory'));
 }
 finally {
 executionsLoading.value = false;
 }
};
const onProjectChange = async () => {
 const selectedProjectData = projects.value.find(p => p.id === selectedProject.value);
 if (selectedProjectData && selectedProjectData.project_type === 'WEBSOCKET') {
 ElMessage.warning(t('apiTesting.messages.warning.websocketNotSupported'));
 const httpProjects = projects.value.filter(project => project.project_type !== 'WEBSOCKET');
 if (httpProjects.length > 0) {
 selectedProject.value = httpProjects[0].id;
 }
 else {
 selectedProject.value = null;
 }
 return;
 }
 selectedSuite.value = null;
 selectedSuites.value = [];
 await Promise.all([
 loadTestSuites(),
 loadEnvironments(),
 loadRequestTree(),
 loadTestPlans()
 ]);
};
const selectSuite = (suite) => {
 selectedSuite.value = suite;
 loadExecutions();
};
const toggleSuiteSelection = (suiteId) => {
 const index = selectedSuites.value.indexOf(suiteId);
 if (index > -1) {
 selectedSuites.value.splice(index, 1);
 }
 else {
 selectedSuites.value.push(suiteId);
 }
};
const handleSuiteCheckbox = (suite) => {
 toggleSuiteSelection(suite.id);
};
const batchDeleteSuites = async () => {
 if (selectedSuites.value.length === 0)
 return;
 try {
 await ElMessageBox.confirm(`确定要删除选中的 ${selectedSuites.value.length} 个测试套件吗？`, '确认删除', {
 type: 'warning'
 });
 for (const id of selectedSuites.value) {
 await api.delete(`/api-testing/test-suites/${id}/`);
 }
 ElMessage.success('删除成功');
 selectedSuites.value = [];
 await loadTestSuites();
 }
 catch (error) {
 if (error !== 'cancel') {
 ElMessage.error('删除失败');
 }
 }
};
const handleSuiteAction = async ({ action, suite }) => {
 switch (action) {
 case 'run':
 await runTestSuite(suite);
 break;
 case 'edit':
 editSuite(suite);
 break;
 case 'duplicate':
 await duplicateSuite(suite);
 break;
 case 'export':
 exportSuite(suite);
 break;
 case 'delete':
 await deleteSuite(suite);
 break;
 }
};
const handleQuickAction = async (action) => {
 switch (action) {
 case 'run-all':
 await runTestSuite(selectedSuite.value);
 break;
 case 'run-failed':
 ElMessage.info('功能开发中');
 break;
 case 'clear-history':
 await clearExecutionHistory();
 break;
 }
};
const runTestSuite = async (suite) => {
 running.value = true;
 try {
 const params = {};
 if (selectedEnvironment.value) {
 params.environment = selectedEnvironment.value;
 }
 const response = await api.post(`/api-testing/test-suites/${suite.id}/execute/`, params);
 currentExecution.value = response.data;
 showExecutionDialog.value = true;
 await loadExecutions();
 await loadTestSuites();
 }
 catch (error) {
 ElMessage.error(t('apiTesting.messages.error.executeSuite'));
 }
 finally {
 running.value = false;
 }
};
const editSuite = (suite) => {
 editingSuite.value = suite;
 suiteForm.name = suite.name;
 suiteForm.description = suite.description;
 suiteForm.project = suite.project;
 suiteForm.environment = suite.environment || null;
 suiteForm.delay_between_requests = suite.delay_between_requests || 0;
 suiteForm.stop_on_failure = suite.stop_on_failure || false;
 showCreateSuiteDialog.value = true;
};
const duplicateSuite = async (suite) => {
 try {
 const newSuite = {
 name: `${suite.name} - ${t('apiTesting.common.copyText')}`,
 description: suite.description,
 project: suite.project,
 environment: suite.environment || null,
 delay_between_requests: suite.delay_between_requests || 0,
 stop_on_failure: suite.stop_on_failure || false
 };
 await api.post('/api-testing/test-suites/', newSuite);
 ElMessage.success(t('apiTesting.messages.success.copy'));
 await loadTestSuites();
 }
 catch (error) {
 ElMessage.error(t('apiTesting.messages.error.copyFailed'));
 }
};
const deleteSuite = async (suite) => {
 try {
 await ElMessageBox.confirm(t('apiTesting.automation.confirmDeleteSuite', { name: suite.name }), t('apiTesting.messages.confirm.deleteTitle'), {
 confirmButtonText: t('apiTesting.common.confirm'),
 cancelButtonText: t('apiTesting.common.cancel'),
 type: 'warning'
 });
 await api.delete(`/api-testing/test-suites/${suite.id}/`);
 ElMessage.success(t('apiTesting.messages.success.delete'));
 if (selectedSuite.value?.id === suite.id) {
 selectedSuite.value = null;
 }
 await loadTestSuites();
 }
 catch (error) {
 if (error !== 'cancel') {
 ElMessage.error(t('apiTesting.messages.error.deleteFailed'));
 }
 }
};
const exportSuite = (suite) => {
 ElMessage.info('导出功能开发中');
};
const submitSuiteForm = async () => {
 if (!suiteFormRef.value)
 return;
 const valid = await suiteFormRef.value.validate().catch(() => false);
 if (!valid)
 return;
 submittingSuite.value = true;
 try {
 if (editingSuite.value) {
 await api.put(`/api-testing/test-suites/${editingSuite.value.id}/`, suiteForm);
 ElMessage.success(t('apiTesting.messages.success.suiteUpdated'));
 }
 else {
 await api.post('/api-testing/test-suites/', suiteForm);
 ElMessage.success(t('apiTesting.messages.success.suiteCreated'));
 }
 showCreateSuiteDialog.value = false;
 await loadTestSuites();
 }
 catch (error) {
 ElMessage.error(editingSuite.value ? t('apiTesting.messages.error.updateFailed') : t('apiTesting.messages.error.createFailed'));
 }
 finally {
 submittingSuite.value = false;
 }
};
const resetSuiteForm = () => {
 editingSuite.value = null;
 Object.assign(suiteForm, {
 name: '',
 description: '',
 project: selectedProject.value,
 environment: null,
 delay_between_requests: 0,
 stop_on_failure: false
 });
 suiteFormRef.value?.resetFields();
};
const showAddRequest = async () => {
 await loadRequestTree();
 showAddRequestDialog.value = true;
 nextTick(() => {
 setTimeout(() => {
 if (requestTreeRef.value && selectedSuite.value) {
 const existingRequestIds = selectedSuite.value.suite_requests?.map(sr => `request_${sr.request.id}`) || [];
 requestTreeRef.value.setCheckedKeys(existingRequestIds, false);
 }
 }, 200);
 });
};
const addSelectedRequests = async () => {
 const checkedNodes = requestTreeRef.value.getCheckedNodes();
 const requestIds = checkedNodes
 .filter(node => node.type === 'request')
 .map(node => node.id.replace('request_', ''));
 if (requestIds.length === 0) {
 ElMessage.warning(t('apiTesting.messages.warning.selectAtLeastOneRequest'));
 return;
 }
 addingRequests.value = true;
 try {
 await api.post(`/api-testing/test-suites/${selectedSuite.value.id}/add-requests/`, {
 request_ids: requestIds
 });
 ElMessage.success(t('apiTesting.messages.success.addSuccess'));
 showAddRequestDialog.value = false;
 await reloadCurrentSuite();
 }
 catch (error) {
 ElMessage.error(t('apiTesting.messages.error.addFailed'));
 }
 finally {
 addingRequests.value = false;
 }
};
const handleRequestSelectionChange = (selectedItems) => {
 selectedRequests.value = selectedItems.map(item => item.id);
};
const batchEnableRequests = async () => {
 try {
 for (const id of selectedRequests.value) {
 await api.put(`/api-testing/test-suite-requests/${id}/`, { enabled: true });
 }
 ElMessage.success('批量启用成功');
 await reloadCurrentSuite();
 }
 catch (error) {
 ElMessage.error('批量操作失败');
 }
};
const batchDisableRequests = async () => {
 try {
 for (const id of selectedRequests.value) {
 await api.put(`/api-testing/test-suite-requests/${id}/`, { enabled: false });
 }
 ElMessage.success('批量禁用成功');
 await reloadCurrentSuite();
 }
 catch (error) {
 ElMessage.error('批量操作失败');
 }
};
const updateRequestEnabled = async (suiteRequest) => {
 try {
 await api.put(`/api-testing/test-suite-requests/${suiteRequest.id}/`, {
 enabled: suiteRequest.enabled
 });
 }
 catch (error) {
 ElMessage.error(t('apiTesting.messages.error.updateFailed'));
 suiteRequest.enabled = !suiteRequest.enabled;
 }
};
const editAssertions = (suiteRequest) => {
 ElMessage.info('断言编辑功能开发中');
};
const editRequestOrder = (suiteRequest) => {
 ElMessage.info('排序功能开发中');
};
const removeRequest = async (suiteRequest) => {
 try {
 await ElMessageBox.confirm(t('apiTesting.automation.confirmRemoveRequest'), t('apiTesting.automation.confirmRemove'), {
 confirmButtonText: t('apiTesting.common.confirm'),
 cancelButtonText: t('apiTesting.common.cancel'),
 type: 'warning'
 });
 await api.delete(`/api-testing/test-suite-requests/${suiteRequest.id}/`);
 ElMessage.success(t('apiTesting.messages.success.removeSuccess'));
 await reloadCurrentSuite();
 }
 catch (error) {
 if (error !== 'cancel') {
 ElMessage.error(t('apiTesting.messages.error.removeFailed'));
 }
 }
};
const reloadCurrentSuite = async () => {
 if (!selectedSuite.value)
 return;
 try {
 const response = await api.get(`/api-testing/test-suites/${selectedSuite.value.id}/`);
 const updatedSuite = response.data;
 selectedSuite.value = { ...updatedSuite };
 const index = testSuites.value.findIndex(suite => suite.id === updatedSuite.id);
 if (index !== -1) {
 testSuites.value[index] = { ...updatedSuite };
 }
 }
 catch (error) {
 ElMessage.error(t('apiTesting.messages.error.refreshSuiteFailed'));
 }
};
const viewExecutionDetail = (execution) => {
 currentExecution.value = execution;
 showExecutionDialog.value = true;
};
const replayExecution = (execution) => {
 if (execution.test_suite) {
 runTestSuite({ id: execution.test_suite });
 }
};
const clearExecutionHistory = async () => {
 try {
 await ElMessageBox.confirm('确定要清除所有执行历史吗？', '确认清除', {
 type: 'warning'
 });
 for (const execution of executions.value) {
 await api.delete(`/api-testing/test-executions/${execution.id}/`);
 }
 ElMessage.success('清除成功');
 executions.value = [];
 }
 catch (error) {
 if (error !== 'cancel') {
 ElMessage.error('清除失败');
 }
 }
};
const formatExecutionResults = (results) => {
 if (!results || !Array.isArray(results))
 return [];
 return results;
};
const exportReport = () => {
 ElMessage.info('报告导出功能开发中');
};
const copyResponse = async (body) => {
 try {
 const text = typeof body === 'object' ? JSON.stringify(body, null, 2) : body;
 await navigator.clipboard.writeText(text);
 ElMessage.success('复制成功');
 }
 catch (error) {
 ElMessage.error('复制失败');
 }
};
const createTestPlan = () => {
 ElMessage.info('创建测试计划功能开发中');
};
const handlePlanAction = (action, plan) => {
 if (action === 'delete') {
 ElMessage.info('删除计划功能开发中');
 }
};
onMounted(() => {
 loadProjects();
});
</script>

<style scoped>
.automation-testing {
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.header-left h3 {
  margin: 0;
  color: #303133;
  font-size: 18px;
}

.subtitle {
  font-size: 13px;
  color: #909399;
  margin-left: 8px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.plan-btn {
  background: #f0f5ff;
  color: #409eff;
}

.content-layout {
  display: flex;
  flex: 1;
  gap: 16px;
  overflow: hidden;
}

.sidebar {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.project-selector,
.environment-selector {
  background: white;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #e4e7ed;
}

.selector-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 10px;
}

.project-select,
.env-select {
  width: 100%;
}

.suite-list {
  background: white;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background: #fafafa;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 500;
}

.list-actions {
  display: flex;
  gap: 5px;
}

.suite-item {
  display: flex;
  align-items: center;
  padding: 12px 15px;
  border-bottom: 1px solid #f5f7fa;
  cursor: pointer;
  transition: all 0.2s;
  gap: 10px;
}

.suite-item:hover {
  background: #fafafa;
}

.suite-item.active {
  background: #e8f5e9;
  border-left: 3px solid #67c23a;
}

.suite-item.selected {
  background: #e3f2fd;
}

.suite-checkbox {
  flex-shrink: 0;
}

.suite-info {
  flex: 1;
  min-width: 0;
}

.suite-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.suite-icon {
  color: #909399;
}

.suite-name {
  font-weight: 500;
  font-size: 13px;
  color: #303133;
}

.suite-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 6px;
}

.meta-divider {
  color: #d9d9d9;
}

.suite-stats {
  margin-top: 4px;
}

.stat {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
}

.stat.passed {
  background: #e8f5e9;
  color: #67c23a;
}

.action-btn {
  opacity: 0;
  transition: opacity 0.2s;
}

.suite-item:hover .action-btn {
  opacity: 1;
}

.main-content {
  flex: 1;
  background: white;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.empty-icon {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.empty-icon .el-icon {
  font-size: 40px;
  color: white;
}

.empty-state h3 {
  margin: 0 0 8px;
  color: #606266;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

.suite-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.suite-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px;
  border-bottom: 1px solid #f5f7fa;
  gap: 20px;
}

.suite-title-section {
  display: flex;
  gap: 12px;
}

.suite-icon-wrapper {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.suite-icon-lg {
  font-size: 24px;
  color: white;
}

.suite-info-main h2 {
  margin: 0 0 4px;
  color: #303133;
}

.suite-desc {
  margin: 0;
  color: #909399;
  font-size: 13px;
}

.suite-actions-bar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.run-btn {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  border: none;
}

.stats-cards {
  display: flex;
  gap: 16px;
  padding: 20px;
  border-bottom: 1px solid #f5f7fa;
}

.stat-card {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-icon.requests { background: #e3f2fd; color: #409eff; }
.stat-icon.assertions { background: #fff3e0; color: #ff9800; }
.stat-icon.passed { background: #e8f5e9; color: #67c23a; }
.stat-icon.executions { background: #f3e5f5; color: #9c27b0; }

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.main-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tab-content {
  flex: 1;
  padding: 20px;
  overflow: auto;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.tab-header h4 {
  margin: 0;
  color: #303133;
}

.tab-actions {
  display: flex;
  gap: 10px;
}

.request-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pass-rate-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pass-rate-bar {
  flex: 1;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.pass-rate-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.pass-rate-fill.high { background: #67c23a; }
.pass-rate-fill.medium { background: #e6a23c; }
.pass-rate-fill.low { background: #f56c6c; }

.pass-rate-text {
  font-size: 13px;
  font-weight: 500;
  min-width: 50px;
  text-align: right;
}

.pass-rate-text.high { color: #67c23a; }
.pass-rate-text.medium { color: #e6a23c; }
.pass-rate-text.low { color: #f56c6c; }

.report-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.report-title h4 {
  margin: 0;
  color: #303133;
}

.report-date {
  font-size: 13px;
  color: #909399;
  margin-left: 10px;
}

.report-summary {
  margin-bottom: 24px;
}

.summary-row {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.summary-item {
  flex: 1;
  text-align: center;
  padding: 20px;
  background: #fafafa;
  border-radius: 8px;
}

.summary-item.total { background: #e3f2fd; }
.summary-item.passed { background: #e8f5e9; }
.summary-item.failed { background: #fef0f0; }
.summary-item.rate { background: #fff3e0; }
.summary-item.time { background: #f3e5f5; }

.summary-value {
  font-size: 32px;
  font-weight: 600;
  color: #303133;
}

.summary-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.chart-section {
  display: flex;
  align-items: center;
  gap: 40px;
  padding: 20px;
  background: #fafafa;
  border-radius: 8px;
}

.chart-title {
  font-weight: 500;
  color: #606266;
  margin-bottom: 16px;
}

.pie-chart {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: #f5f5f5;
  position: relative;
  overflow: hidden;
}

.pie-slice {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
}

.pie-slice.passed {
  background: #67c23a;
}

.pie-slice.failed {
  background: #f56c6c;
}

.pie-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100px;
  height: 100px;
  background: white;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.pie-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.pie-label {
  font-size: 12px;
  color: #909399;
}

.chart-legend {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 4px;
}

.legend-color.passed { background: #67c23a; }
.legend-color.failed { background: #f56c6c; }

.report-details {
  flex: 1;
  overflow: auto;
}

.report-details h5 {
  margin: 0 0 16px;
  color: #303133;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-item {
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.result-item.passed {
  background: #f0f9ff;
  border-color: #b3d9e8;
}

.result-item.failed {
  background: #fff5f5;
  border-color: #ffccc7;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.result-index {
  width: 28px;
  height: 28px;
  background: #e4e7ed;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 500;
  color: #606266;
}

.result-info {
  flex: 1;
}

.result-name {
  font-weight: 500;
  color: #303133;
  margin-right: 8px;
}

.result-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.success-icon { color: #67c23a; }
.error-icon { color: #f56c6c; }

.result-url {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.result-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
}

.result-error {
  margin-top: 12px;
  padding: 12px;
  background: #fff1f0;
  border-radius: 6px;
}

.result-error strong {
  color: #f56c6c;
}

.result-error p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #606266;
}

.result-assertions {
  margin-top: 12px;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
}

.result-assertions strong {
  color: #606266;
}

.assertion-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 13px;
}

.assertion-item .check { color: #67c23a; }
.assertion-item .x { color: #f56c6c; }

.add-request-content {
  height: 400px;
  display: flex;
  flex-direction: column;
}

.request-tree-header {
  margin-bottom: 12px;
}

.search-input {
  width: 100%;
}

.request-selector {
  flex: 1;
  overflow: auto;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
}

.request-tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
}

.method-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.method-tag.get { background: #e8f5e9; color: #67c23a; }
.method-tag.post { background: #e3f2fd; color: #409eff; }
.method-tag.put { background: #fff3e0; color: #e6a23c; }
.method-tag.delete { background: #fef0f0; color: #f56c6c; }
.method-tag.patch { background: #e0e5ec; color: #606266; }

.execution-dialog {
  max-height: 90vh;
}

.execution-detail {
  height: calc(90vh - 120px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.execution-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid #e4e7ed;
  margin-bottom: 20px;
}

.execution-title h3 {
  margin: 0;
  color: #303133;
}

.execution-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #909399;
}

.execution-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.summary-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.summary-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.summary-icon.total { background: #e3f2fd; color: #409eff; }
.summary-icon.passed { background: #e8f5e9; color: #67c23a; }
.summary-icon.failed { background: #fef0f0; color: #f56c6c; }
.summary-icon.rate { background: #fff3e0; color: #e6a23c; }

.summary-info {
  flex: 1;
}

.summary-num {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.summary-num.passed { color: #67c23a; }
.summary-num.failed { color: #f56c6c; }

.summary-text {
  font-size: 12px;
  color: #909399;
}

.execution-results-section {
  flex: 1;
  overflow: auto;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h4 {
  margin: 0;
  color: #303133;
}

.filter-tabs {
  display: flex;
  gap: 5px;
}

.filter-tabs .el-button {
  padding: 4px 12px;
  font-size: 12px;
}

.filter-tabs .el-button.active {
  background: #409eff;
  color: white;
}

.results-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-card {
  border-radius: 8px;
  border: 1px solid #e4e7ed;
  overflow: hidden;
}

.result-card.passed {
  border-color: #b3d9e8;
}

.result-card.failed {
  border-color: #ffccc7;
}

.result-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #fafafa;
}

.result-index-badge {
  width: 24px;
  height: 24px;
  background: #409eff;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 500;
}

.result-card-info {
  flex: 1;
}

.result-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.result-card-title span {
  font-weight: 500;
  color: #303133;
}

.result-card-url {
  font-size: 12px;
  color: #909399;
}

.result-card-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.result-card-status .success { color: #67c23a; }
.result-card-status .error { color: #f56c6c; }

.result-card-body {
  padding: 16px;
}

.result-metrics {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
}

.metric {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
}

.result-error-box {
  padding: 12px;
  background: #fff1f0;
  border-radius: 6px;
  margin-bottom: 16px;
}

.error-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f56c6c;
  font-weight: 500;
  margin-bottom: 8px;
}

.error-content {
  margin: 0;
  font-size: 13px;
  color: #606266;
  white-space: pre-wrap;
}

.result-assertions-box {
  margin-bottom: 16px;
}

.assertions-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-weight: 500;
  margin-bottom: 12px;
}

.assertions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.assertion-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 4px;
}

.assertion-row.passed {
  background: #f0f9ff;
}

.assertion-row.failed {
  background: #fff5f5;
}

.assertion-row .check { color: #67c23a; }
.assertion-row .x { color: #f56c6c; }

.assertion-name {
  font-weight: 500;
  color: #303133;
}

.assertion-detail {
  font-size: 12px;
  color: #909399;
}

.result-response-box {
  background: #fafafa;
  border-radius: 6px;
  overflow: hidden;
}

.response-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #e4e7ed;
}

.response-header span {
  font-weight: 500;
  color: #606266;
}

.response-content {
  margin: 0;
  padding: 12px;
  font-size: 13px;
  color: #303133;
  white-space: pre-wrap;
  max-height: 300px;
  overflow: auto;
}

.plan-content {
  height: 300px;
  display: flex;
  flex-direction: column;
}

.plan-list {
  flex: 1;
  overflow: auto;
  margin-bottom: 16px;
}

.empty-plan {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.plan-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #f5f7fa;
}

.plan-info h4 {
  margin: 0 0 4px;
  color: #303133;
}

.plan-info p {
  margin: 0 0 4px;
  font-size: 12px;
  color: #909399;
}

.plan-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.plan-status.active {
  background: #e8f5e9;
  color: #67c23a;
}

.plan-status.disabled {
  background: #f5f5f5;
  color: #909399;
}

.create-plan-btn {
  width: 100%;
}

.form-row {
  display: flex;
  gap: 16px;
  align-items: center;
}

.config-input {
  width: 200px;
}

.no-report {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

:deep(.el-table .cell) {
  padding: 10px 12px;
}

:deep(.el-table th) {
  background: #fafafa;
}

:deep(.el-tree-node__content) {
  height: auto;
  padding: 8px 12px;
}

:deep(.el-tree-node__expand-icon) {
  margin-right: 6px;
}

:deep(.el-dialog__body) {
  padding: 20px;
}

:deep(.el-form-item) {
  margin-bottom: 16px;
}
</style>