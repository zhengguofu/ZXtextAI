<template>
  <div class="interface-management">
    <div class="interface-layout">
      <!-- 左侧集合树 -->
      <div class="sidebar">
        <div class="sidebar-header">
          <el-select v-model="selectedProject" :placeholder="$t('apiTesting.common.selectProject')" @change="onProjectChange" style="width: 100%;">
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
          <div class="header-actions">
            <el-input
              v-model="searchKeyword"
              :placeholder="$t('apiTesting.interface.searchInterface')"
              size="small"
              clearable
              @input="onSearchDebounced"
              @keyup.enter="onSearch(searchKeyword)"
              style="flex: 1; min-width: 0;"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" size="small" @click="openCreateCollectionDialog" :title="$t('apiTesting.interface.createCollection')">
              <el-icon><FolderAdd /></el-icon>
            </el-button>
            <el-button type="success" size="small" @click="createEmptyRequest" :title="$t('apiTesting.interface.addInterface')">
              <el-icon><Plus /></el-icon>
            </el-button>
          </div>
        </div>

        <div class="collection-tree" v-show="!searchKeyword || searchKeyword.trim() === ''">
          <el-tree
            ref="treeRef"
            :data="collections"
            :props="treeProps"
            node-key="id"
            :expand-on-click-node="false"
            :default-expanded-keys="expandedKeys"
            @node-click="onNodeClick"
            @node-contextmenu="onNodeRightClick"
            @node-expand="onNodeExpand"
            @node-collapse="onNodeCollapse"
          >
            <template #default="{ node, data }">
              <div class="tree-node">
                <el-icon v-if="data.type === 'collection'" class="node-icon">
                  <Folder :class="{ 'folder-open': expandedKeys.includes(data.id) }" />
                </el-icon>
                <el-icon v-else class="node-icon" :class="getMethodIconClass(data.method)">
                  <Document />
                </el-icon>

                <!-- 集合名称编辑 -->
                <div v-if="data.type === 'collection' && editingNodeId === data.id" class="node-edit">
                  <el-input
                    v-model="editingNodeName"
                    size="small"
                    @blur="saveCollectionName"
                    @keyup.enter="saveCollectionName"
                    @keyup.esc="cancelEdit"
                    ref="editInputRef"
                  />
                </div>

                <!-- 普通显示模式 -->
                <span v-else class="node-label">{{ node.label }}</span>

                <span v-if="data.type === 'request'" class="method-tag" :class="(data.method || 'GET').toLowerCase()">
                  {{ data.method || 'GET' }}
                </span>
              </div>
            </template>
          </el-tree>

          <!-- 搜索结果 -->
          <div v-if="filteredCollections.length > 0" class="search-results">
            <div class="search-results-header">
              <span>{{ $t('apiTesting.interface.searchResults', { count: filteredCollections.length }) }}</span>
              <el-button size="small" text @click="clearSearch">
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
            <div class="search-results-list">
              <div
                v-for="item in filteredCollections"
                :key="item.id"
                class="search-result-item"
                @click="selectSearchResult(item)"
              >
                <el-icon><Document /></el-icon>
                <div class="search-result-content">
                  <div class="search-result-name">{{ item.name }}</div>
                  <div class="search-result-url">{{ item.url }}</div>
                </div>
                <span class="method-tag" :class="(item.method || 'GET').toLowerCase()">{{ item.method || 'GET' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧请求详情 -->
      <div class="main-content">
        <div v-if="!selectedRequest" class="empty-state">
          <div class="empty-content">
            <div class="empty-icon">
              <FileText class="icon" />
            </div>
            <h3>{{ $t('apiTesting.interface.selectInterface') }}</h3>
            <p>{{ $t('apiTesting.interface.emptyHint') }}</p>
            <el-button type="primary" @click="createEmptyRequest">{{ $t('apiTesting.interface.createNewInterface') }}</el-button>
          </div>
        </div>

        <div v-else class="request-detail">
          <!-- 请求基本信息 -->
          <div class="request-header">
            <div class="request-line">
              <!-- HTTP接口显示方法选择器 -->
              <el-select
                v-model="requestMethod"
                class="method-select"
                :class="requestMethod.toLowerCase()"
                :placeholder="'GET'"
                :popper-class="'method-select-dropdown'"
              >
                <el-option
                  v-for="method in availableMethods"
                  :key="method"
                  :label="method"
                  :value="method"
                  :class="method.toLowerCase()"
                />
              </el-select>

              <el-input
                v-model="requestUrl"
                :placeholder="$t('apiTesting.interface.inputRequestUrl')"
                class="url-input"
              >
                <template #prepend>
                  <el-select v-model="selectedEnvironment" :placeholder="$t('apiTesting.interface.environment')" class="env-select">
                    <el-option :label="$t('apiTesting.common.noEnvironment')" :value="null" />
                    <el-option
                      v-for="env in environments"
                      :key="env.id"
                      :label="env.name"
                      :value="env.id"
                    />
                  </el-select>
                </template>
              </el-input>

              <!-- WebSocket连接按钮 -->
              <el-button
                v-if="selectedRequest && selectedRequest.request_type === 'WEBSOCKET'"
                :type="websocketConnectionStatus === 'disconnected' ? 'primary' : 'info'"
                :loading="websocketConnectionStatus === 'connecting'"
                @click="toggleWebSocketConnection"
                class="send-button"
              >
                <span v-if="websocketConnectionStatus === 'disconnected'">{{ $t('apiTesting.interface.connect') }}</span>
                <span v-else-if="websocketConnectionStatus === 'connecting'">{{ $t('apiTesting.interface.connecting') }}</span>
                <span v-else>{{ $t('apiTesting.interface.disconnect') }}</span>
              </el-button>

              <!-- HTTP发送按钮 -->
              <el-button
                v-if="!selectedRequest || !selectedRequest.request_type || selectedRequest.request_type !== 'WEBSOCKET'"
                type="primary"
                @click="sendRequest"
                :loading="sending"
                class="send-button"
              >
                <el-icon><Right /></el-icon>
                {{ $t('apiTesting.interface.send') }}
              </el-button>
            </div>

            <div class="request-meta">
              <el-input
                v-model="selectedRequest.name"
                :placeholder="$t('apiTesting.interface.requestName')"
                size="small"
                class="name-input"
              />
              <div class="action-buttons">
                <el-button size="small" @click="saveRequest" :loading="saving">
                  <el-icon><DocumentCopy /></el-icon>
                  {{ $t('apiTesting.common.save') }}
                </el-button>
                <el-dropdown split-button type="default" size="small" @click="importCurl">
                  <el-icon><Download /></el-icon>
                  {{ $t('apiTesting.common.import') }}
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item @click="importCurl">{{ $t('apiTesting.interface.importCurl') }}</el-dropdown-item>
                      <el-dropdown-item @click="exportRequest">{{ $t('apiTesting.interface.exportCurl') }}</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-dropdown split-button type="default" size="small" @click="generateDataAnalysis('javascript')">
                  <el-icon><DataAnalysis /></el-icon>
                  {{ $t('apiTesting.interface.generateDataAnalysis') }}
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item @click="generateDataAnalysis('javascript')">JavaScript</el-dropdown-item>
                      <el-dropdown-item @click="generateDataAnalysis('python')">Python</el-dropdown-item>
                      <el-dropdown-item @click="generateDataAnalysis('java')">Java</el-dropdown-item>
                      <el-dropdown-item @click="generateDataAnalysis('curl')">cURL</el-dropdown-item>
                      <el-dropdown-item @click="generateDataAnalysis('node')">Node.js</el-dropdown-item>
                      <el-dropdown-item @click="generateDataAnalysis('php')">PHP</el-dropdown-item>
                      <el-dropdown-item @click="generateDataAnalysis('go')">Go</el-dropdown-item>
                      <el-dropdown-item @click="generateDataAnalysis('csharp')">C#</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>

          <!-- 请求配置 -->
          <el-tabs v-model="activeTab" class="request-tabs" type="card">
            <el-tab-pane label="Params" name="params">
              <div class="tab-content-wrapper">
                <KeyValueEditor
                  v-model="selectedRequest.params"
                  :placeholder-key="$t('apiTesting.interface.paramName')"
                  :placeholder-value="$t('apiTesting.interface.paramValue')"
                  :enable-data-factory="true"
                />
              </div>
            </el-tab-pane>

            <el-tab-pane label="Headers" name="headers">
              <div class="tab-content-wrapper">
                <KeyValueEditor
                  ref="headersEditorRef"
                  v-model="selectedRequest.headers"
                  :placeholder-key="$t('apiTesting.interface.headerName')"
                  :placeholder-value="$t('apiTesting.interface.headerValue')"
                  :enable-data-factory="true"
                  @update:modelValue="onHeadersUpdate"
                />
              </div>
            </el-tab-pane>

            <!-- Authorization 认证（Postman风格） -->
            <el-tab-pane label="Auth" name="auth">
              <div class="auth-container">
                <el-select v-model="authType" class="auth-type-select" :placeholder="$t('apiTesting.interface.authType')">
                  <el-option label="No Auth" value="none" />
                  <el-option label="Bearer Token" value="bearer" />
                  <el-option label="Basic Auth" value="basic" />
                  <el-option label="API Key" value="apikey" />
                </el-select>

                <div v-if="authType === 'bearer'" class="auth-config">
                  <el-input v-model="authToken" placeholder="输入 Token..." style="margin-bottom:8px">
                    <template #prepend>Token</template>
                  </el-input>
                  <div class="auth-hint">
                    <el-icon><InfoFilled /></el-icon>
                    <span>{{ $t('apiTesting.interface.authHintBearer') }}</span>
                  </div>
                </div>

                <div v-else-if="authType === 'basic'" class="auth-config">
                  <el-input v-model="authUsername" placeholder="用户名" style="margin-bottom:8px">
                    <template #prepend>用户名</template>
                  </el-input>
                  <el-input v-model="authPassword" placeholder="密码" type="password" show-password>
                    <template #prepend>密码</template>
                  </el-input>
                  <div class="auth-hint">
                    <el-icon><InfoFilled /></el-icon>
                    <span>{{ $t('apiTesting.interface.authHintBasic') }}</span>
                  </div>
                </div>

                <div v-else-if="authType === 'apikey'" class="auth-config">
                  <el-input v-model="authKey" placeholder="Key" style="margin-bottom:8px">
                    <template #prepend>Key</template>
                  </el-input>
                  <el-input v-model="authValue" placeholder="Value" style="margin-bottom:8px">
                    <template #prepend>Value</template>
                  </el-input>
                  <el-radio-group v-model="authAddTo" style="margin-top:8px">
                    <el-radio value="header">添加到 Header</el-radio>
                    <el-radio value="query">添加到 Query Params</el-radio>
                  </el-radio-group>
                  <div class="auth-hint">
                    <el-icon><InfoFilled /></el-icon>
                    <span>{{ $t('apiTesting.interface.authHintApiKey') }}</span>
                  </div>
                </div>

                <div v-else class="auth-config">
                  <div class="no-auth-info">
                    <el-icon><Lock /></el-icon>
                    <span>{{ $t('apiTesting.interface.authHintNone') }}</span>
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <el-tab-pane label="Body" name="body" v-if="hasBody">
              <div class="body-container">
                <el-radio-group v-model="bodyType" @change="onBodyTypeChange">
                  <el-radio value="none">none</el-radio>
                  <el-radio value="form-data">form-data</el-radio>
                  <el-radio value="x-www-form-urlencoded">x-www-form-urlencoded</el-radio>
                  <el-radio value="raw">raw</el-radio>
                  <el-radio value="binary">binary</el-radio>
                </el-radio-group>

                <div v-if="bodyType === 'form-data'" class="body-content">
                  <KeyValueEditor
                    v-model="formData"
                    :placeholder-key="$t('apiTesting.interface.key')"
                    :placeholder-value="$t('apiTesting.interface.value')"
                    :show-file="true"
                  />
                </div>

                <div v-else-if="bodyType === 'x-www-form-urlencoded'" class="body-content">
                  <KeyValueEditor
                    v-model="formUrlEncoded"
                    :placeholder-key="$t('apiTesting.interface.key')"
                    :placeholder-value="$t('apiTesting.interface.value')"
                  />
                </div>

                <div v-else-if="bodyType === 'raw'" class="body-content">
                  <div class="raw-options">
                    <el-select v-model="rawType" style="width: 150px;">
                      <el-option label="Text" value="text" />
                      <el-option label="JSON" value="json" />
                      <el-option label="HTML" value="html" />
                      <el-option label="XML" value="xml" />
                    </el-select>

                    <el-button
                      size="small"
                      :icon="MagicStick"
                      @click="openDataFactorySelectorForBody('rawBody')"
                      :title="$t('apiTesting.interface.referDataFactory')"
                      class="data-factory-btn"
                    >
                      {{ $t('apiTesting.interface.referDataFactory') }}
                    </el-button>
                    <el-button
                      size="small"
                      :icon="MagicStick"
                      @click="openVariableHelper('rawBody')"
                      :title="$t('apiTesting.interface.variableHelper')"
                      class="variable-helper-btn"
                    >
                      {{ $t('apiTesting.interface.variableHelper') }}
                    </el-button>
                  </div>
                  <el-input
                    ref="rawBodyInputRef"
                    v-model="rawBody"
                    type="textarea"
                    :rows="12"
                    :placeholder="$t('apiTesting.interface.inputRequestBody')"
                    class="raw-body"
                  />
                </div>

                <div v-else-if="bodyType === 'binary'" class="body-content">
                  <el-upload
                    drag
                    action="#"
                    :auto-upload="false"
                    :show-file-list="false"
                    :on-change="handleWebSocketFileUpload"
                    class="binary-upload"
                  >
                    <el-icon class="el-icon--upload"><Upload /></el-icon>
                    <div class="el-upload__text">
                      {{ $t('apiTesting.interface.dragBinaryFile') }}<em>{{ $t('apiTesting.interface.clickUpload') }}</em>
                    </div>
                  </el-upload>
                  <div v-if="websocketBinaryFile" class="uploaded-file">
                    <span>{{ websocketBinaryFile.name }}</span>
                    <el-button size="small" type="danger" @click="clearWebSocketBinaryFile">{{ $t('apiTesting.interface.clear') }}</el-button>
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <!-- HTTP接口专用标签页 -->
            <template v-if="!selectedRequest || selectedRequest.request_type !== 'WEBSOCKET'">
              <el-tab-pane label="Pre-request Script" name="pre-script">
                <div class="script-editor-container">
                  <div class="script-header">
                    <span>{{ $t('apiTesting.interface.preRequestScriptHint') }}</span>
                    <div class="script-actions">
                      <el-button
                        size="small"
                        :icon="MagicStick"
                        @click="openDataFactorySelectorForScript('pre_request_script')"
                        :title="$t('apiTesting.interface.referDataFactory')"
                        class="script-factory-btn"
                      >
                        {{ $t('apiTesting.interface.referDataFactory') }}
                      </el-button>
                      <el-button
                        size="small"
                        :icon="MagicStick"
                        @click="openVariableHelper('pre_request_script')"
                        :title="$t('apiTesting.interface.variableHelper')"
                        class="script-variable-btn"
                      >
                        {{ $t('apiTesting.interface.variableHelper') }}
                      </el-button>
                    </div>
                  </div>
                  <el-input
                    v-model="selectedRequest.pre_request_script"
                    type="textarea"
                    :rows="15"
                    placeholder="// 请求前脚本，使用JavaScript语法"
                    class="script-editor"
                  />
                </div>
              </el-tab-pane>

              <el-tab-pane label="Tests" name="tests">
                <div class="script-editor-container">
                  <div class="script-header">
                    <span>{{ $t('apiTesting.interface.testScriptHint') }}</span>
                    <div class="script-actions">
                      <el-button
                        size="small"
                        :icon="MagicStick"
                        @click="openDataFactorySelectorForScript('post_request_script')"
                        :title="$t('apiTesting.interface.referDataFactory')"
                        class="script-factory-btn"
                      >
                        {{ $t('apiTesting.interface.referDataFactory') }}
                      </el-button>
                      <el-button
                        size="small"
                        :icon="MagicStick"
                        @click="openVariableHelper('post_request_script')"
                        :title="$t('apiTesting.interface.variableHelper')"
                        class="script-variable-btn"
                      >
                        {{ $t('apiTesting.interface.variableHelper') }}
                      </el-button>
                    </div>
                  </div>
                  <el-input
                    v-model="selectedRequest.post_request_script"
                    type="textarea"
                    :rows="15"
                    placeholder="// 请求后脚本和测试，使用JavaScript语法"
                    class="script-editor"
                  />
                </div>
              </el-tab-pane>

              <el-tab-pane :label="$t('apiTesting.interface.assertions')" name="assertions">
                <div class="assertions-editor">
                  <div class="assertions-header">
                    <span>{{ $t('apiTesting.interface.assertions') }}</span>
                    <el-button size="small" type="primary" @click="addAssertion">
                      <el-icon><Plus /></el-icon>
                      {{ $t('apiTesting.interface.addAssertion') }}
                    </el-button>
                  </div>

                  <div class="assertions-list">
                    <div
                      v-for="(assertion, index) in selectedRequest.assertions"
                      :key="index"
                      class="assertion-item"
                    >
                      <div class="assertion-header">
                        <el-input
                          v-model="assertion.name"
                          :placeholder="$t('apiTesting.interface.assertionName')"
                          size="small"
                          class="assertion-name"
                        />
                        <el-button
                          size="small"
                          type="danger"
                          @click="removeAssertion(index)"
                          circle
                        >
                          <el-icon><Delete /></el-icon>
                        </el-button>
                      </div>

                      <div class="assertion-config">
                        <el-select
                          v-model="assertion.type"
                          :placeholder="$t('apiTesting.interface.selectAssertionType')"
                          size="small"
                          @change="onAssertionTypeChange(assertion)"
                        >
                          <el-option :label="$t('apiTesting.interface.assertionTypes.statusDataAnalysis')" value="status_code" />
                          <el-option :label="$t('apiTesting.interface.assertionTypes.responseTime')" value="response_time" />
                          <el-option :label="$t('apiTesting.interface.assertionTypes.contains')" value="contains" />
                          <el-option :label="$t('apiTesting.interface.assertionTypes.jsonPath')" value="json_path" />
                          <el-option :label="$t('apiTesting.interface.assertionTypes.header')" value="header" />
                          <el-option :label="$t('apiTesting.interface.assertionTypes.equals')" value="equals" />
                        </el-select>

                        <div class="assertion-params" v-if="assertion.type">
                          <!-- 状态码断言 -->
                          <div v-if="assertion.type === 'status_code'" class="assertion-param-row">
                            <span class="param-label">{{ $t('apiTesting.interface.expectedStatusDataAnalysis') }}</span>
                            <el-input-number
                              v-model="assertion.expected"
                              :min="100"
                              :max="599"
                              size="small"
                            />
                          </div>

                          <!-- 响应时间断言 -->
                          <div v-else-if="assertion.type === 'response_time'" class="assertion-param-row">
                            <span class="param-label">{{ $t('apiTesting.interface.maxResponseTime') }}</span>
                            <el-input-number
                              v-model="assertion.expected"
                              :min="1"
                              size="small"
                            />
                            <span class="param-unit">ms</span>
                          </div>

                          <!-- 包含文本断言 -->
                          <div v-else-if="assertion.type === 'contains'" class="assertion-param-row">
                            <span class="param-label">{{ $t('apiTesting.interface.expectedContains') }}</span>
                            <el-input
                              v-model="assertion.expected"
                              :placeholder="$t('apiTesting.interface.expectedContains')"
                              size="small"
                              class="flex-1"
                            />
                          </div>

                          <!-- JSON路径断言 -->
                          <div v-else-if="assertion.type === 'json_path'" class="assertion-param-row">
                            <span class="param-label">{{ $t('apiTesting.interface.jsonPath') }}</span>
                            <el-input
                              v-model="assertion.json_path"
                              :placeholder="$t('apiTesting.interface.jsonPathExample')"
                              size="small"
                              class="flex-1"
                            />
                          </div>
                          <div v-if="assertion.type === 'json_path'" class="assertion-param-row">
                            <span class="param-label">{{ $t('apiTesting.interface.expectedValue') }}</span>
                            <el-input
                              v-model="assertion.expected"
                              :placeholder="$t('apiTesting.interface.expectedValue')"
                              size="small"
                              class="flex-1"
                            />
                          </div>

                          <!-- 响应头断言 -->
                          <div v-else-if="assertion.type === 'header'" class="assertion-param-row">
                            <span class="param-label">{{ $t('apiTesting.interface.headerName') }}</span>
                            <el-input
                              v-model="assertion.header_name"
                              :placeholder="$t('apiTesting.interface.headerName')"
                              size="small"
                              class="flex-1"
                            />
                          </div>
                          <div v-if="assertion.type === 'header'" class="assertion-param-row">
                            <span class="param-label">{{ $t('apiTesting.interface.expectedValue') }}</span>
                            <el-input
                              v-model="assertion.expected_value"
                              :placeholder="$t('apiTesting.interface.expectedValue')"
                              size="small"
                              class="flex-1"
                            />
                          </div>

                          <!-- 完全匹配断言 -->
                          <div v-else-if="assertion.type === 'equals'" class="assertion-param-row">
                            <span class="param-label">{{ $t('apiTesting.interface.expectedMatch') }}</span>
                            <el-input
                              v-model="assertion.expected"
                              :placeholder="$t('apiTesting.interface.expectedMatch')"
                              size="small"
                              class="flex-1"
                            />
                          </div>
                        </div>
                      </div>
                    </div>

                    <div v-if="!selectedRequest.assertions || selectedRequest.assertions.length === 0" class="no-assertions">
                      <el-icon><QuestionFilled /></el-icon>
                      <p>{{ $t('apiTesting.interface.noAssertions') }}</p>
                      <el-button size="small" type="primary" @click="addAssertion">
                        <el-icon><Plus /></el-icon>
                        {{ $t('apiTesting.interface.addFirstAssertion') }}
                      </el-button>
                    </div>
                  </div>
                </div>
              </el-tab-pane>
            </template>

            <!-- WebSocket接口专用标签页 -->
            <template v-else-if="selectedRequest && selectedRequest.request_type === 'WEBSOCKET'">
              <el-tab-pane label="Message" name="message">
                <div class="message-container">
                  <div class="message-input-section">
                    <el-select
                      v-model="websocketMessageType"
                      :placeholder="$t('apiTesting.interface.messageType')"
                      style="width: 150px; margin-bottom: 15px;"
                    >
                      <el-option label="Text" value="text" />
                      <el-option label="JSON" value="json" />
                      <el-option label="Binary" value="binary" />
                    </el-select>

                    <div v-if="websocketMessageType === 'text' || websocketMessageType === 'json'">
                      <el-input
                        v-model="websocketMessageContent"
                        type="textarea"
                        :rows="6"
                        :placeholder="$t('apiTesting.interface.inputWebSocketMessage')"
                      />
                    </div>

                    <div v-else-if="websocketMessageType === 'binary'">
                      <el-upload
                        drag
                        action="#"
                        :auto-upload="false"
                        :show-file-list="false"
                        :on-change="handleWebSocketFileUpload"
                      >
                        <el-icon class="el-icon--upload"><Upload /></el-icon>
                        <div class="el-upload__text">
                          {{ $t('apiTesting.interface.dragBinaryFile') }}<em>{{ $t('apiTesting.interface.clickUpload') }}</em>
                        </div>
                      </el-upload>
                      <div v-if="websocketBinaryFile" class="uploaded-file">
                        <span>{{ websocketBinaryFile.name }}</span>
                        <el-button size="small" type="danger" @click="clearWebSocketBinaryFile">{{ $t('apiTesting.interface.clear') }}</el-button>
                      </div>
                    </div>

                    <div class="message-actions" style="margin-top: 15px;">
                      <el-button type="primary" @click="sendWebSocketMessage">
                        <el-icon><Right /></el-icon>
                        {{ $t('apiTesting.interface.sendMessage') }}
                      </el-button>
                      <el-button @click="clearWebSocketMessage">
                        <el-icon><Delete /></el-icon>
                        {{ $t('apiTesting.interface.clearMessage') }}
                      </el-button>
                    </div>
                  </div>

                  <!-- WebSocket消息历史记录 -->
                  <div class="websocket-response-section" v-if="websocketMessages.length > 0">
                    <div class="websocket-header">
                      <h3>{{ $t('apiTesting.interface.messageHistory') }}</h3>
                      <el-button size="small" @click="clearWebSocketMessages">{{ $t('apiTesting.interface.clearHistory') }}</el-button>
                    </div>
                    <div class="websocket-messages">
                      <div
                        v-for="(msg, index) in websocketMessages.slice().reverse()"
                        :key="index"
                        class="websocket-message-item"
                        :class="msg.type"
                      >
                        <div class="message-header">
                          <span class="message-type" :class="msg.type">
                            {{ msg.type === 'sent' ? $t('apiTesting.interface.messageSent') :
                               msg.type === 'connected' ? $t('apiTesting.interface.messageConnected') :
                               msg.type === 'info' ? $t('apiTesting.interface.messageInfoFilled') :
                               msg.type === 'error' ? $t('apiTesting.interface.messageError') : $t('apiTesting.interface.messageReceived') }}
                          </span>
                          <span class="message-time">{{ msg.timestamp }}</span>
                        </div>
                        <div class="message-content">
                          <pre v-if="msg.type === 'received' && isJsonString(msg.content)">{{ formatJson(msg.content) }}</pre>
                          <pre v-else>{{ msg.content }}</pre>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </el-tab-pane>
            </template>
          </el-tabs>

          <!-- 响应区域 -->
          <div v-if="response" class="response-section">
            <div class="response-header">
              <div class="response-title">
                <el-icon><Document /></el-icon>
                <h3>{{ $t('apiTesting.interface.response') }}</h3>
              </div>
              <div class="response-info">
                <el-tag :type="getStatusType(response.status_code)" class="status-tag">
                  {{ response.status_code }}
                </el-tag>
                <span class="response-time">{{ response.response_time ? response.response_time.toFixed(0) : 0 }}ms</span>
                <span class="response-size">{{ formatSize(response.response_data?.body?.length || 0) }}</span>
              </div>
            </div>

            <el-tabs v-model="responseActiveTab" type="card">
              <el-tab-pane label="Body" name="body">
                <div class="response-body">
                  <div class="response-actions">
                    <el-button-group>
                      <el-button size="small" @click="formatResponse">{{ $t('apiTesting.interface.format') }}</el-button>
                      <el-button size="small" @click="copyResponse">{{ $t('apiTesting.interface.copy') }}</el-button>
                      <el-button size="small" @click="toggleJsonPathExtractor">
                        {{ $t('apiTesting.interface.jsonPathExtract') }}
                      </el-button>
                    </el-button-group>
                    <div class="response-view-options">
                      <el-radio-group v-model="responseViewMode">
                        <el-radio value="raw">Raw</el-radio>
                        <el-radio value="pretty">Pretty</el-radio>
                      </el-radio-group>
                    </div>
                  </div>
                  <div v-if="showJsonPathExtractor" class="jsonpath-extractor">
                    <div class="jsonpath-input">
                      <el-input
                        v-model="jsonPathExpression"
                        :placeholder="$t('apiTesting.interface.jsonPathExample')"
                        size="small"
                        @input="evaluateJsonPath"
                      >
                        <template #append>
                          <el-button size="small" @click="copyJsonPathResult">{{ $t('apiTesting.interface.copyResult') }}</el-button>
                        </template>
                      </el-input>
                    </div>
                    <div v-if="jsonPathResult !== null" class="jsonpath-result">
                      <strong>{{ $t('apiTesting.interface.extractResult') }}</strong>
                      <pre>{{ jsonPathResult }}</pre>
                    </div>
                  </div>
                  <div v-if="responseViewMode === 'pretty' && isJsonResponse" class="json-tree-view">
                    <JsonTreeNode
                      :data="parsedResponseJson"
                      :expand-all="prettyExpandAll"
                      :level="0"
                    />
                  </div>
                  <div v-else class="response-content" v-html="highlightedResponseBody"></div>
                </div>
              </el-tab-pane>

              <el-tab-pane label="Headers" name="headers">
                <div class="response-headers">
                  <div class="response-actions" style="margin-bottom:15px">
                    <el-button size="small" @click="copyHeaders">复制 Headers</el-button>
                  </div>
                  <div v-for="(value, key) in (response.response_data?.headers || {})" :key="key" class="header-row">
                    <span class="header-name">{{ key }}:</span>
                    <span class="header-value">{{ value }}</span>
                  </div>
                </div>
              </el-tab-pane>

              <el-tab-pane label="Cookies" name="cookies" v-if="response.response_data?.cookies && response.response_data.cookies.length > 0">
                <div class="response-cookies">
                  <div class="response-actions" style="margin-bottom:15px">
                    <el-button size="small" @click="copyCookies">复制 Cookies</el-button>
                  </div>
                  <div class="cookies-table">
                    <div class="cookies-header">
                      <span>Name</span>
                      <span>Value</span>
                      <span>Domain</span>
                      <span>Path</span>
                      <span>Expires</span>
                      <span>Secure</span>
                      <span>HttpOnly</span>
                    </div>
                    <div v-for="(cookie, idx) in response.response_data.cookies" :key="idx" class="cookies-row">
                      <span>{{ cookie.name }}</span>
                      <span>{{ cookie.value }}</span>
                      <span>{{ cookie.domain || '-' }}</span>
                      <span>{{ cookie.path || '/' }}</span>
                      <span>{{ cookie.expires || '-' }}</span>
                      <span>{{ cookie.secure ? 'Yes' : 'No' }}</span>
                      <span>{{ cookie.http_only ? 'Yes' : 'No' }}</span>
                    </div>
                  </div>
                </div>
              </el-tab-pane>

              <el-tab-pane label="Preview" name="preview" v-if="isHtmlResponse">
                <div class="response-preview">
                  <iframe :srcdoc="response.response_data?.body" class="preview-iframe" sandbox="allow-scripts"></iframe>
                </div>
              </el-tab-pane>

              <el-tab-pane label="Script" name="script-results" v-if="response.script_results && Object.keys(response.script_results).length > 0">
                <div class="response-headers">
                  <div v-for="(value, key) in response.script_results" :key="key" class="header-row">
                    <span class="header-name">{{ key }}:</span>
                    <span class="header-value">{{ value }}</span>
                  </div>
                </div>
              </el-tab-pane>

              <el-tab-pane :label="$t('apiTesting.interface.assertionResults')" name="assertions" v-if="response.assertions_results && response.assertions_results.length > 0">
                <div class="assertions-results">
                  <div class="assertions-summary">
                    <span class="summary-item">
                      <el-tag type="success">{{ response.assertions_results.filter(r => r.passed).length }} {{ $t('apiTesting.interface.passed') }}</el-tag>
                    </span>
                    <span class="summary-item">
                      <el-tag type="danger">{{ response.assertions_results.filter(r => !r.passed).length }} {{ $t('apiTesting.interface.failed') }}</el-tag>
                    </span>
                  </div>
                  <div
                    v-for="(result, index) in response.assertions_results"
                    :key="index"
                    class="assertion-result-item"
                    :class="{ 'passed': result.passed, 'failed': !result.passed }"
                  >
                    <div class="assertion-result-header">
                      <el-icon v-if="result.passed"><CircleCheck /></el-icon>
                      <el-icon v-else><CircleClose /></el-icon>
                      <span class="assertion-name">{{ result.name }}</span>
                    </div>
                    <div class="assertion-result-details">
                      <div class="result-row">
                        <span class="label">{{ $t('apiTesting.interface.expected') }}</span>
                        <span class="value">{{ formatAssertionValue(result.expected) }}</span>
                      </div>
                      <div class="result-row">
                        <span class="label">{{ $t('apiTesting.interface.actual') }}</span>
                        <span class="value">{{ formatAssertionValue(result.actual) }}</span>
                      </div>
                      <div class="result-row" v-if="result.error">
                        <span class="label">{{ $t('apiTesting.interface.error') }}</span>
                        <span class="value error">{{ result.error }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建集合对话框 -->
    <el-dialog v-model="showCreateCollectionDialog" :title="$t('apiTesting.interface.createCollection')" :close-on-click-modal="false" :close-on-press-escape="false" :modal="true" :destroy-on-close="false" width="500px">
      <el-form ref="collectionFormRef" :model="collectionForm" :rules="collectionRules" label-width="100px">
        <el-form-item :label="$t('apiTesting.interface.collectionName')" prop="name">
          <el-input v-model="collectionForm.name" :placeholder="$t('apiTesting.interface.inputCollectionName')" />
        </el-form-item>
        <el-form-item :label="$t('apiTesting.common.description')" prop="description">
          <el-input v-model="collectionForm.description" type="textarea" :rows="3" :placeholder="`${$t('apiTesting.common.pleaseInput')}${$t('apiTesting.common.description')}`" />
        </el-form-item>
        <el-form-item :label="$t('apiTesting.interface.parentCollection')" prop="parent">
          <el-select v-model="collectionForm.parent" :placeholder="$t('apiTesting.interface.selectParentCollection')" clearable>
            <el-option
              v-for="collection in flatCollections"
              :key="collection.id"
              :label="collection.name"
              :value="collection.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeCreateCollectionDialog">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="createCollection">{{ $t('apiTesting.common.create') }}</el-button>
      </template>
    </el-dialog>

    <!-- 编辑集合对话框 -->
    <el-dialog v-model="showEditCollectionDialog" :title="$t('apiTesting.interface.editCollection')" :close-on-click-modal="false" width="500px">
      <el-form ref="editCollectionFormRef" :model="editCollectionForm" :rules="collectionRules" label-width="100px">
        <el-form-item :label="$t('apiTesting.interface.collectionName')" prop="name">
          <el-input v-model="editCollectionForm.name" :placeholder="$t('apiTesting.interface.inputCollectionName')" />
        </el-form-item>
        <el-form-item :label="$t('apiTesting.common.description')" prop="description">
          <el-input v-model="editCollectionForm.description" type="textarea" :rows="3" :placeholder="`${$t('apiTesting.common.pleaseInput')}${$t('apiTesting.common.description')}`" />
        </el-form-item>
        <el-form-item :label="$t('apiTesting.interface.parentCollection')" prop="parent">
          <el-select v-model="editCollectionForm.parent" :placeholder="$t('apiTesting.interface.selectParentCollection')" clearable>
            <el-option
              v-for="collection in flatCollections.filter(c => c.id !== editCollectionForm.id)"
              :key="collection.id"
              :label="collection.name"
              :value="collection.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeEditCollectionDialog">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="editCollection">{{ $t('apiTesting.common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 右键菜单 -->
    <ul v-show="showContextMenu" class="context-menu" :style="{ left: contextMenuX + 'px', top: contextMenuY + 'px' }">
      <li @click="addRequest"><el-icon><Plus /></el-icon>{{ $t('apiTesting.interface.contextMenu.addRequest') }}</li>
      <li @click="addCollection"><el-icon><FolderAdd /></el-icon>{{ $t('apiTesting.interface.contextMenu.addSubCollection') }}</li>
      <li @click="editNode"><el-icon><Edit /></el-icon>{{ $t('apiTesting.interface.contextMenu.edit') }}</li>
      <li @click="duplicateNode"><el-icon><CopyDocument /></el-icon>{{ $t('apiTesting.interface.contextMenu.copy') }}</li>
      <li class="divider"></li>
      <li @click="deleteNode"><el-icon><Delete /></el-icon>{{ $t('apiTesting.interface.contextMenu.delete') }}</li>
    </ul>

    <!-- 数据工厂选择器 -->
    <DataFactorySelector
      v-model="showDataFactorySelector"
      @select="handleDataFactorySelect"
    />

    <!-- 变量助手对话框 -->
    <el-dialog
      :close-on-press-escape="false"
      :modal="true"
      :destroy-on-close="false"
      v-model="showVariableHelper"
      :title="$t('apiTesting.interface.variableHelper') + ' (点击插入)'"
      :close-on-click-modal="false"
      width="900px"
    >
      <div v-if="variableCategories.length === 0" style="padding: 20px; text-align: center; color: #999;">
        <p>{{ $t('apiTesting.interface.variableCategoriesLoading') }}</p>
      </div>
      <el-tabs v-else tab-position="left" style="height: 450px">
        <el-tab-pane
          v-for="(category, index) in variableCategories"
          :key="index"
          :label="category.label"
        >
          <div style="height: 450px; overflow-y: auto; padding: 10px;">
            <el-table :data="category.variables" style="width: 100%" @row-click="insertVariable" highlight-current-row>
              <el-table-column prop="name" :label="$t('apiTesting.interface.functionName')" width="150">
                <template #default="{ row }">
                  <el-tag size="small">{{ row.name }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="desc" :label="$t('apiTesting.interface.description')" min-width="150" />
              <el-table-column prop="syntax" :label="$t('apiTesting.interface.syntax')" min-width="200" show-overflow-tooltip />
              <el-table-column prop="example" :label="$t('apiTesting.interface.example')" min-width="200" show-overflow-tooltip />
              <el-table-column :label="$t('apiTesting.interface.operation')" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small">{{ $t('apiTesting.interface.insert') }}</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- CURL导入对话框 -->
    <el-dialog
      v-model="showCurlImportDialog"
      :title="$t('apiTesting.interface.importCurlCommand')"
      width="800px"
      :close-on-click-modal="false"
    >
      <el-input
        v-model="curlCommand"
        type="textarea"
        :rows="15"
        :placeholder="$t('apiTesting.interface.pasteCurlCommand')"
        class="curl-input"
      />
      <template #footer>
        <el-button @click="closeCurlImportDialog">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="parseAndImportCurl">{{ $t('apiTesting.interface.parseAndImport') }}</el-button>
      </template>
    </el-dialog>

    <!-- 代码生成对话框 -->
    <el-dialog
      v-model="showDataAnalysisGenerateDialog"
      :title="$t('apiTesting.interface.generateDataAnalysis')"
      width="900px"
      :close-on-click-modal="false"
    >
      <el-select v-model="codeLanguage" :placeholder="$t('apiTesting.interface.selectLanguage')" style="width: 150px; margin-bottom: 10px" @change="generateDataAnalysis(codeLanguage)">
        <el-option label="JavaScript" value="javascript" />
        <el-option label="Python" value="python" />
        <el-option label="Java" value="java" />
        <el-option label="Node.js" value="node" />
        <el-option label="cURL" value="curl" />
        <el-option label="PHP" value="php" />
        <el-option label="Go" value="go" />
        <el-option label="C#" value="csharp" />
        <el-option label="Ruby" value="ruby" />
        <el-option label="Swift" value="swift" />
        <el-option label="Kotlin" value="kotlin" />
        <el-option label="Rust" value="rust" />
        <el-option label="Dart" value="dart" />
        <el-option label="Objective-C" value="objc" />
        <el-option label="PowerShell" value="powershell" />
        <el-option label="MATLAB" value="matlab" />
        <el-option label="R" value="r" />
        <el-option label="Ansible" value="ansible" />
        <el-option label="C" value="c" />
        <el-option label="CFML" value="cfml" />
        <el-option label="Clojure" value="clojure" />
        <el-option label="Elixir" value="elixir" />
        <el-option label="HTTP" value="http" />
        <el-option label="HTTPie" value="httpie" />
        <el-option label="Julia" value="julia" />
        <el-option label="Lua" value="lua" />
        <el-option label="OCaml" value="ocaml" />
        <el-option label="Perl" value="perl" />
        <el-option label="Wget" value="wget" />
      </el-select>
      <el-input
        v-model="generatedDataAnalysis"
        type="textarea"
        :rows="20"
        readonly
        class="code-generate"
      />
      <template #footer>
        <el-button @click="closeDataAnalysisGenerateDialog">{{ $t('apiTesting.common.cancel') }}</el-button>
        <el-button type="primary" @click="copyGeneratedDataAnalysis">{{ $t('apiTesting.common.copy') }}</el-button>
      </template>
    </el-dialog>

    <!-- 请求历史记录 -->
    <el-drawer
      v-model="showHistoryDrawer"
      title="{{ $t('apiTesting.interface.requestHistory') }}"
      direction="rtl"
      size="400px"
    >
      <div class="history-content">
        <div class="history-filter">
          <el-input
            v-model="historySearch"
            placeholder="搜索历史记录"
            size="small"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button size="small" type="danger" @click="clearHistory">{{ $t('apiTesting.interface.clearHistory') }}</el-button>
        </div>
        <div class="history-list">
          <div
            v-for="(item, index) in filteredHistory"
            :key="index"
            class="history-item"
            @click="loadHistoryRequest(item)"
          >
            <div class="history-header">
              <span class="method-tag" :class="item.method.toLowerCase()">{{ item.method }}</span>
              <span class="history-time">{{ item.timestamp }}</span>
            </div>
            <div class="history-url">{{ item.url }}</div>
            <div class="history-info">
              <el-tag :type="getStatusType(item.status_code)" size="small">{{ item.status_code }}</el-tag>
              <span>{{ item.response_time?.toFixed(0) }}ms</span>
            </div>
          </div>
          <div v-if="requestHistory.length === 0" class="empty-history">
            <el-icon><Timer /></el-icon>
            <p>{{ $t('apiTesting.interface.noHistory') }}</p>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, Folder, FolderAdd, Document, DocumentCopy, Download, DataAnalysis, Right, Search, Close,
  Upload, InfoFilled, Lock, Delete, CopyDocument, CircleCheck,
  CircleClose, Timer, MagicStick, Edit, QuestionFilled
} from '@element-plus/icons-vue'
import api from '@/utils/api'
import KeyValueEditor from './components/KeyValueEditor.vue'
import JsonTreeNode from './components/JsonTreeNode.vue'
import DataFactorySelector from '@/components/DataFactorySelector.vue'
import { RequestModelParser } from '@/utils/requestModel'
import { getVariableFunctions } from '@/api/data-factory'
import { CodeGenerator } from '@/utils/codeGenerator'
import { debounce } from 'lodash-es'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const treeRef = ref(null)
const expandedKeys = ref([])
const projects = ref([])
const selectedProject = ref(null)
const collections = ref([])
const flatCollections = ref([])
const environments = ref([])
const selectedEnvironment = ref(null)
const selectedRequest = ref(null)
const response = ref(null)
const sending = ref(false)
const saving = ref(false)
const activeTab = ref('params')
const responseActiveTab = ref('body')
const prettyExpandAll = ref(false)
const responseViewMode = ref('pretty')

// JSON Pretty 模式
const parsedResponseJson = computed(() => {
  if (!response.value?.response_data) return null
  const data = response.value.response_data
  try {
    if (data.json) return data.json
    if (data.body && typeof data.body === 'object') return data.body
    return JSON.parse(data.body)
  } catch {
    return null
  }
})

const isJsonResponse = computed(() => {
  return parsedResponseJson.value !== null && typeof parsedResponseJson.value === 'object'
})

const isHtmlResponse = computed(() => {
  const headers = response.value?.response_data?.headers || {}
  const contentType = headers['Content-Type'] || headers['content-type'] || ''
  return contentType.includes('text/html')
})

const showCreateCollectionDialog = ref(false)
const showEditCollectionDialog = ref(false)
const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const rightClickedNode = ref(null)
const headersEditorRef = ref(null)
const editingNodeId = ref(null)
const editingNodeName = ref('')
const editInputRef = ref(null)
const rawBodyInputRef = ref(null)
const currentHeaders = ref({})

const searchKeyword = ref('')
const filteredCollections = ref([])

const treeProps = {
  children: 'children',
  label: 'name'
}

// 数据工厂选择器相关
const showDataFactorySelector = ref(false)
const showVariableHelper = ref(false)
const currentEditingField = ref('')
const currentBodyField = ref('')
const currentAssertion = ref(null)
const currentAssertionField = ref('')
const currentAssertionIndex = ref(-1)
const currentScriptField = ref('')
const variableCategories = ref([])
const loading = ref(false)

// CURL导入相关
const showCurlImportDialog = ref(false)
const curlCommand = ref('')

// 代码生成相关
const showDataAnalysisGenerateDialog = ref(false)
const codeLanguage = ref('javascript')
const generatedDataAnalysis = ref('')

// WebSocket相关
const websocketConnectionStatus = ref('disconnected')
const websocketConnection = ref(null)
const websocketMessages = ref([])
const websocketMessageType = ref('text')
const websocketMessageContent = ref('')
const websocketBinaryFile = ref(null)

// JSONPath提取相关
const showJsonPathExtractor = ref(false)
const jsonPathExpression = ref('')
const jsonPathResult = ref(null)

// Body相关
const bodyType = ref('none')
const rawType = ref('text')
const formData = ref([])
const formUrlEncoded = ref([])
const rawBody = ref('')

// Authorization 认证相关（Postman风格）
const authType = ref('none')
const authToken = ref('')
const authUsername = ref('')
const authPassword = ref('')
const authKey = ref('')
const authValue = ref('')
const authAddTo = ref('header')

// 请求历史相关
const showHistoryDrawer = ref(false)
const historySearch = ref('')
const requestHistory = ref([])

const availableMethods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS', 'CONNECT', 'TRACE']

const onSearchDebounced = debounce((value) => {
  onSearch(value)
}, 300)

const onSearch = async (value) => {
  if (!value || value.trim() === '') {
    filteredCollections.value = []
    return
  }

  try {
    const response = await api.get('/api-testing/collections/search', {
      params: {
        project: selectedProject.value,
        keyword: value
      }
    })
    filteredCollections.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error('搜索失败')
    console.error('搜索失败:', error)
  }
}

const selectSearchResult = (item) => {
  selectedRequest.value = item
  searchKeyword.value = ''
  filteredCollections.value = []
}

const onProjectChange = async (projectId) => {
  if (!projectId) return

  try {
    await loadCollections(projectId)
    await loadEnvironments(projectId)
  } catch (error) {
    ElMessage.error('切换项目失败')
    console.error('切换项目失败:', error)
  }
}

const loadProjects = async () => {
  try {
    const response = await api.get('/api-testing/projects/')
    projects.value = response.data.results || response.data || []
    if (projects.value.length > 0) {
      selectedProject.value = projects.value[0].id
      await loadCollections(selectedProject.value)
      await loadEnvironments(selectedProject.value)
    }
  } catch (error) {
    ElMessage.error('加载项目失败')
    console.error('加载项目失败:', error)
  }
}

const loadCollections = async (projectId) => {
  try {
    const response = await api.get('/api-testing/collections/', {
      params: {
        project: projectId
      }
    })
    const collectionsData = response.data.results || response.data || []

    collections.value = buildTree(collectionsData)
    flatCollections.value = collectionsData

    await loadRequests()
  } catch (error) {
    ElMessage.error('加载集合失败')
    console.error('加载集合失败:', error)
  }
}

const loadEnvironments = async (projectId) => {
  try {
    const response = await api.get('/api-testing/environments/', {
      params: {
        project: projectId
      }
    })
    environments.value = response.data.results || response.data || []
  } catch (error) {
    ElMessage.error('加载环境失败')
    console.error('加载环境失败:', error)
  }
}

const buildTree = (items) => {
  const map = {}
  const roots = []

  items.forEach(item => {
    map[item.id] = {
      ...item,
      type: 'collection',
      children: []
    }
  })

  items.forEach(item => {
    if (item.parent) {
      if (map[item.parent]) {
        map[item.parent].children.push(map[item.id])
      }
    } else {
      roots.push(map[item.id])
    }
  })

  return roots
}

const findCollectionById = (collections, id) => {
  for (const collection of collections) {
    if (collection.id === id) return collection
    if (collection.children) {
      const found = findCollectionById(collection.children, id)
      if (found) return found
    }
  }
  return null
}

const clearCollectionChildren = (collection) => {
  if (collection.children) {
    collection.children = collection.children.filter(child => child.type === 'collection')
    collection.children.forEach(child => clearCollectionChildren(child))
  }
}

const loadRequests = async () => {
  if (!selectedProject.value) return

  try {
    const response = await api.get('/api-testing/requests/', {
      params: {
        project: selectedProject.value
      }
    })
    const requests = response.data.results || response.data || []

    collections.value.forEach(collection => {
      clearCollectionChildren(collection)
    })

    collections.value = collections.value.filter(item => item.type === 'collection')

    requests.forEach(request => {
      if (request.collection) {
        const collection = findCollectionById(collections.value, request.collection)
        if (collection) {
          if (!collection.children) collection.children = []
          collection.children.push({
            ...request,
            type: 'request',
            name: request.name
          })
        }
      } else {
        collections.value.push({
          ...request,
          type: 'request',
          name: request.name
        })
      }
    })
  } catch (error) {
    ElMessage.error('加载请求失败')
    console.error('加载请求失败:', error)
  }
}

const flattenCollections = (items, parent = null) => {
  let result = []
  for (const item of items) {
    if (item.type === 'collection') {
      result.push(item)
      if (item.children && item.children.length > 0) {
        result = result.concat(flattenCollections(item.children, item))
      }
    }
  }
  return result
}

const onNodeClick = async (data) => {
  if (data.type === 'request') {
    try {
      const apiResponse = await api.get(`/api-testing/requests/${data.id}/`)
      const requestData = apiResponse.data

      currentHeaders.value = requestData.headers || {}

      if (requestData.params && typeof requestData.params === 'object' && !Array.isArray(requestData.params)) {
        const paramsArray = []
        Object.keys(requestData.params).forEach(key => {
          if (key && requestData.params[key] !== undefined) {
            paramsArray.push({
              enabled: true,
              key,
              value: requestData.params[key],
              description: '',
              type: 'text'
            })
          }
        })
        requestData.params = paramsArray
      }

      if (requestData.headers && typeof requestData.headers === 'object' && !Array.isArray(requestData.headers)) {
        const headersArray = []
        Object.keys(requestData.headers).forEach(key => {
          if (key && requestData.headers[key] !== undefined) {
            headersArray.push({
              enabled: true,
              key,
              value: requestData.headers[key],
              description: '',
              type: 'text'
            })
          }
        })
        requestData.headers = headersArray
      }

      if (requestData.body && requestData.body.type) {
        if (requestData.body.type === 'json' && requestData.body.data) {
          bodyType.value = 'raw'
          rawType.value = 'json'
          rawBody.value = JSON.stringify(requestData.body.data, null, 2)
        } else if (requestData.body.type === 'raw' && requestData.body.data) {
          bodyType.value = 'raw'
          rawType.value = 'text'
          rawBody.value = requestData.body.data
        } else if (requestData.body.type === 'form-data') {
          bodyType.value = 'form-data'
          formData.value = requestData.body.data || []
        } else if (requestData.body.type === 'x-www-form-urlencoded') {
          bodyType.value = 'x-www-form-urlencoded'
          formUrlEncoded.value = requestData.body.data || []
        } else if (requestData.body.type === 'binary') {
          bodyType.value = 'binary'
        } else {
          bodyType.value = 'none'
          rawBody.value = ''
        }
      } else {
        bodyType.value = 'none'
        rawBody.value = ''
      }

      response.value = null
      selectedRequest.value = requestData
    } catch (error) {
      ElMessage.error('加载请求失败')
      console.error('加载请求失败:', error)
    }
  }
}

const onNodeRightClick = (event, node, treeNode) => {
  event.preventDefault()
  showContextMenu.value = true
  contextMenuX.value = event.clientX
  contextMenuY.value = event.clientY
  rightClickedNode.value = node
}

const onNodeExpand = (node) => {
  expandedKeys.value.push(node.id)
}

const onNodeCollapse = (node) => {
  expandedKeys.value = expandedKeys.value.filter(key => key !== node.id)
}

const createEmptyRequest = () => {
  if (!selectedProject.value) {
    ElMessage.warning('请先选择项目')
    return
  }

  const newRequest = {
    id: null,
    collection: null,
    name: '未命名接口',
    url: '',
    method: 'GET',
    params: [],
    headers: [],
    pre_request_script: '',
    post_request_script: '',
    assertions: [],
    request_type: 'HTTP'
  }

  selectedRequest.value = newRequest
}

const openCreateCollectionDialog = () => {
  showCreateCollectionDialog.value = true
}

const clearSearch = () => {
  searchKeyword.value = ''
  filteredCollections.value = []
}

const closeCreateCollectionDialog = () => {
  showCreateCollectionDialog.value = false
}

const closeEditCollectionDialog = () => {
  showEditCollectionDialog.value = false
}

const closeCurlImportDialog = () => {
  showCurlImportDialog.value = false
}

const closeDataAnalysisGenerateDialog = () => {
  showDataAnalysisGenerateDialog.value = false
}

const toggleJsonPathExtractor = () => {
  showJsonPathExtractor.value = !showJsonPathExtractor.value
}

const addRequest = () => {
  if (!rightClickedNode.value) return

  const parentNode = rightClickedNode.value
  if (!parentNode || parentNode.type !== 'collection') {
    ElMessage.warning('只能在集合下添加接口')
    return
  }

  const newRequest = {
    id: null,
    collection: parentNode.id,
    name: '未命名接口',
    url: '',
    method: 'GET',
    params: [],
    headers: [],
    pre_request_script: '',
    post_request_script: '',
    assertions: [],
    request_type: 'HTTP'
  }

  selectedRequest.value = newRequest
  showContextMenu.value = false
}

const addCollection = () => {
  if (!rightClickedNode.value) return

  const parentNode = rightClickedNode.value
  if (!parentNode || parentNode.type !== 'collection') {
    ElMessage.warning('只能在集合下添加子集合')
    return
  }

  collectionForm.parent = parentNode.id
  showCreateCollectionDialog.value = true
  showContextMenu.value = false
}

const editNode = () => {
  if (!rightClickedNode.value) return

  const node = rightClickedNode.value
  if (!node) {
    ElMessage.warning('无法编辑此节点')
    return
  }

  if (node.type === 'collection') {
    editingNodeId.value = node.id
    editingNodeName.value = node.name
    showContextMenu.value = false

    nextTick(() => {
      editInputRef.value?.focus()
    })
  } else {
    ElMessage.warning('只能编辑集合名称')
  }
}

const duplicateNode = async () => {
  if (!rightClickedNode.value) return

  const node = rightClickedNode.value
  if (!node) {
    ElMessage.warning('无法复制此节点')
    return
  }

  try {
    if (node.type === 'collection') {
      const newCollection = {
        name: `${node.name} (副本)`,
        description: node.description,
        parent: node.parent,
        project: selectedProject.value
      }
      await api.post('/api-testing/collections/', newCollection)
      ElMessage.success('复制成功')
      await loadCollections(selectedProject.value)
    } else if (node.type === 'request') {
      const newRequest = {
        name: `${node.name} (副本)`,
        url: node.url,
        method: node.method,
        params: node.params || [],
        headers: node.headers || [],
        body: node.body,
        collection: node.collection,
        project: selectedProject.value,
        pre_request_script: node.pre_request_script || '',
        post_request_script: node.post_request_script || '',
        assertions: node.assertions || []
      }
      await api.post('/api-testing/requests/', newRequest)
      ElMessage.success('复制成功')
      await loadRequests()
    }
    showContextMenu.value = false
  } catch (error) {
    ElMessage.error('复制失败')
    console.error('复制失败:', error)
  }
}

const deleteNode = async () => {
  if (!rightClickedNode.value) return

  const node = rightClickedNode.value
  if (!node) {
    ElMessage.warning('无法删除此节点')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除"${node.name}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    let response
    if (node.type === 'collection') {
      response = await api.delete(`/api-testing/collections/${node.id}/`)
    } else if (node.type === 'request') {
      response = await api.delete(`/api-testing/requests/${node.id}/`)
    }

    if (response && (response.status === 204 || response.status === 200)) {
      ElMessage.success('删除成功')
      showContextMenu.value = false

      if (selectedRequest.value && selectedRequest.value.id === node.id) {
        selectedRequest.value = null
      }

      await loadCollections(selectedProject.value)
    } else {
      ElMessage.error('删除失败，服务器未返回成功状态')
      console.error('删除失败:', response)
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error('删除失败:', error)
    }
    showContextMenu.value = false
  }
}

const saveCollectionName = async () => {
  if (!editingNodeId.value) return

  try {
    await api.put(`/api-testing/collections/${editingNodeId.value}/`, {
      name: editingNodeName.value
    })
    await loadCollections(selectedProject.value)
  } catch (error) {
    ElMessage.error('保存失败')
    console.error('保存失败:', error)
  } finally {
    editingNodeId.value = null
    editingNodeName.value = ''
  }
}

const cancelEdit = () => {
  editingNodeId.value = null
  editingNodeName.value = ''
}

const collectionFormRef = ref(null)
const collectionForm = reactive({
  name: '',
  description: '',
  parent: null
})

const collectionRules = {
  name: [
    { required: true, message: '请输入集合名称', trigger: 'blur' }
  ]
}

const createCollection = async () => {
  if (!collectionFormRef.value) return

  const valid = await collectionFormRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    await api.post('/api-testing/collections/', {
      ...collectionForm,
      project: selectedProject.value
    })
    ElMessage.success('创建成功')
    closeCreateCollectionDialog()
    await loadCollections(selectedProject.value)
    collectionForm.name = ''
    collectionForm.description = ''
    collectionForm.parent = null
  } catch (error) {
    ElMessage.error('创建失败')
    console.error('创建失败:', error)
  }
}

const editCollectionFormRef = ref(null)
const editCollectionForm = reactive({
  id: null,
  name: '',
  description: '',
  parent: null
})

const editCollection = async () => {
  if (!editCollectionFormRef.value) return

  const valid = await editCollectionFormRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    await api.put(`/api-testing/collections/${editCollectionForm.id}/`, editCollectionForm)
    ElMessage.success('修改成功')
    closeEditCollectionDialog()
    await loadCollections(selectedProject.value)
  } catch (error) {
    ElMessage.error('修改失败')
    console.error('修改失败:', error)
  }
}

const saveRequest = async () => {
  if (!selectedRequest.value) return

  saving.value = true
  try {
    const requestData = {
      ...selectedRequest.value,
      project: selectedProject.value
    }

    // 处理 body
    if (bodyType.value === 'raw') {
      requestData.body = {
        type: rawType.value === 'json' ? 'json' : 'raw',
        data: rawBody.value
      }
    } else if (bodyType.value === 'form-data') {
      requestData.body = {
        type: 'form-data',
        data: formData.value
      }
    } else if (bodyType.value === 'x-www-form-urlencoded') {
      requestData.body = {
        type: 'x-www-form-urlencoded',
        data: formUrlEncoded.value
      }
    } else if (bodyType.value === 'binary') {
      requestData.body = {
        type: 'binary',
        data: null
      }
    } else {
      requestData.body = null
    }

    if (selectedRequest.value.id) {
      await api.put(`/api-testing/requests/${selectedRequest.value.id}/`, requestData)
      ElMessage.success('保存成功')
    } else {
      const response = await api.post('/api-testing/requests/', requestData)
      selectedRequest.value.id = response.data.id
      ElMessage.success('创建成功')
    }

    await loadRequests()
  } catch (error) {
    ElMessage.error('保存失败')
    console.error('保存失败:', error)
  } finally {
    saving.value = false
  }
}

const sendRequest = async () => {
  if (!selectedRequest.value || !requestUrl.value) {
    ElMessage.warning('请填写请求URL')
    return
  }

  sending.value = true
  try {
    const requestData = {
      url: requestUrl.value,
      method: requestMethod.value,
      headers: selectedRequest.value.headers?.filter(h => h.enabled).reduce((acc, h) => {
        acc[h.key] = h.value
        return acc
      }, {}) || {},
      params: selectedRequest.value.params?.filter(p => p.enabled).reduce((acc, p) => {
        acc[p.key] = p.value
        return acc
      }, {}) || {},
      body: null,
      assertions: selectedRequest.value.assertions || [],
      pre_request_script: selectedRequest.value.pre_request_script || '',
      post_request_script: selectedRequest.value.post_request_script || '',
      environment: selectedEnvironment.value
    }

    // 处理 body
    if (bodyType.value === 'raw') {
      requestData.body = {
        type: rawType.value === 'json' ? 'json' : 'raw',
        data: rawBody.value
      }
    } else if (bodyType.value === 'form-data') {
      requestData.body = {
        type: 'form-data',
        data: formData.value
      }
    } else if (bodyType.value === 'x-www-form-urlencoded') {
      requestData.body = {
        type: 'x-www-form-urlencoded',
        data: formUrlEncoded.value
      }
    }

    const responseData = await api.post('/api-testing/requests/execute/', requestData)
    response.value = responseData.data

    // 保存到历史记录
    saveToHistory({
      url: requestUrl.value,
      method: requestMethod.value,
      status_code: response.value.status_code,
      response_time: response.value.response_time,
      timestamp: new Date().toLocaleString('zh-CN')
    })
  } catch (error) {
    ElMessage.error('请求失败')
    console.error('请求失败:', error)
  } finally {
    sending.value = false
  }
}

const saveToHistory = (item) => {
  requestHistory.value.unshift(item)
  if (requestHistory.value.length > 100) {
    requestHistory.value = requestHistory.value.slice(0, 100)
  }
}

const filteredHistory = computed(() => {
  if (!historySearch.value) return requestHistory.value
  return requestHistory.value.filter(item =>
    item.url.toLowerCase().includes(historySearch.value.toLowerCase())
  )
})

const loadHistoryRequest = (item) => {
  requestUrl.value = item.url
  requestMethod.value = item.method
  showHistoryDrawer.value = false
}

const clearHistory = () => {
  requestHistory.value = []
}

const onHeadersUpdate = () => {
  // Headers 更新处理
}

const hasBody = computed(() => {
  const method = requestMethod.value?.toUpperCase()
  return !['GET', 'HEAD', 'OPTIONS'].includes(method)
})

const requestMethod = computed({
  get: () => selectedRequest.value?.method || 'GET',
  set: (value) => {
    if (selectedRequest.value) {
      selectedRequest.value.method = value
    }
  }
})

const requestUrl = computed({
  get: () => selectedRequest.value?.url || '',
  set: (value) => {
    if (selectedRequest.value) {
      selectedRequest.value.url = value
    }
  }
})

const onBodyTypeChange = () => {
  // Body类型切换处理
}

const handleWebSocketFileUpload = (file) => {
  websocketBinaryFile.value = file.raw
}

const clearWebSocketBinaryFile = () => {
  websocketBinaryFile.value = null
}

const toggleWebSocketConnection = async () => {
  if (websocketConnectionStatus.value === 'connected') {
    closeWebSocketConnection()
    return
  }

  websocketConnectionStatus.value = 'connecting'
  try {
    const url = selectedRequest.value.url
    const wsUrl = url.replace(/^http/, 'ws')
    websocketConnection.value = new WebSocket(wsUrl)

    websocketConnection.value.onopen = () => {
      websocketConnectionStatus.value = 'connected'
      websocketMessages.value.push({
        type: 'connected',
        content: `已连接到 ${url}`,
        timestamp: new Date().toLocaleTimeString('zh-CN')
      })
    }

    websocketConnection.value.onmessage = (event) => {
      websocketMessages.value.push({
        type: 'received',
        content: event.data,
        timestamp: new Date().toLocaleTimeString('zh-CN')
      })
    }

    websocketConnection.value.onerror = (error) => {
      websocketMessages.value.push({
        type: 'error',
        content: `连接错误: ${error.message}`,
        timestamp: new Date().toLocaleTimeString('zh-CN')
      })
      websocketConnectionStatus.value = 'disconnected'
    }

    websocketConnection.value.onclose = () => {
      websocketMessages.value.push({
        type: 'info',
        content: '连接已关闭',
        timestamp: new Date().toLocaleTimeString('zh-CN')
      })
      websocketConnectionStatus.value = 'disconnected'
    }
  } catch (error) {
    ElMessage.error('连接失败')
    websocketConnectionStatus.value = 'disconnected'
    console.error('WebSocket连接失败:', error)
  }
}

const closeWebSocketConnection = () => {
  if (websocketConnection.value) {
    websocketConnection.value.close()
    websocketConnection.value = null
  }
}

const sendWebSocketMessage = () => {
  if (!websocketConnection.value || websocketConnectionStatus.value !== 'connected') {
    ElMessage.warning('请先连接')
    return
  }

  try {
    let content = websocketMessageContent.value
    if (websocketMessageType.value === 'json') {
      JSON.parse(content)
    }
    websocketConnection.value.send(content)
    websocketMessages.value.push({
      type: 'sent',
      content,
      timestamp: new Date().toLocaleTimeString('zh-CN')
    })
  } catch (error) {
    ElMessage.error('发送失败')
    console.error('发送失败:', error)
  }
}

const clearWebSocketMessage = () => {
  websocketMessageContent.value = ''
}

const clearWebSocketMessages = () => {
  websocketMessages.value = []
}

const isJsonString = (str) => {
  try {
    JSON.parse(str)
    return true
  } catch {
    return false
  }
}

const formatJson = (str) => {
  try {
    return JSON.stringify(JSON.parse(str), null, 2)
  } catch {
    return str
  }
}

const addAssertion = () => {
  if (!selectedRequest.value.assertions) {
    selectedRequest.value.assertions = []
  }
  selectedRequest.value.assertions.push({
    name: '',
    type: 'status_code',
    expected: 200,
    json_path: '',
    header_name: '',
    expected_value: ''
  })
}

const removeAssertion = (index) => {
  selectedRequest.value.assertions.splice(index, 1)
}

const onAssertionTypeChange = (assertion) => {
  // 断言类型切换处理
}

const highlightedResponseBody = computed(() => {
  if (!response.value?.response_data?.body) return ''
  const body = response.value.response_data.body
  if (typeof body === 'object') {
    return JSON.stringify(body, null, 2)
  }
  return escapeHtml(body)
})

const escapeHtml = (str) => {
  const div = document.createElement('div')
  div.textContent = str
  return div.innerHTML
}

const formatResponse = () => {
  if (!response.value?.response_data?.body) return
  try {
    const body = response.value.response_data.body
    if (typeof body === 'string') {
      response.value.response_data.body = JSON.stringify(JSON.parse(body), null, 2)
    }
    prettyExpandAll.value = !prettyExpandAll.value
  } catch {
    ElMessage.warning('无法格式化非JSON内容')
  }
}

const copyResponse = async () => {
  if (!response.value?.response_data?.body) return
  try {
    const body = response.value.response_data.body
    const text = typeof body === 'object' ? JSON.stringify(body, null, 2) : body
    await navigator.clipboard.writeText(text)
    ElMessage.success('复制成功')
  } catch (error) {
    ElMessage.error('复制失败')
    console.error('复制失败:', error)
  }
}

const copyHeaders = async () => {
  if (!response.value?.response_data?.headers) return
  try {
    const headers = response.value.response_data.headers
    const text = Object.entries(headers)
      .map(([key, value]) => `${key}: ${value}`)
      .join('\n')
    await navigator.clipboard.writeText(text)
    ElMessage.success('复制成功')
  } catch (error) {
    ElMessage.error('复制失败')
    console.error('复制失败:', error)
  }
}

const copyCookies = async () => {
  if (!response.value?.response_data?.cookies) return
  try {
    const cookies = response.value.response_data.cookies
    const text = cookies.map(c => `${c.name}=${c.value}`).join('; ')
    await navigator.clipboard.writeText(text)
    ElMessage.success('复制成功')
  } catch (error) {
    ElMessage.error('复制失败')
    console.error('复制失败:', error)
  }
}

const evaluateJsonPath = () => {
  if (!jsonPathExpression.value || !parsedResponseJson.value) {
    jsonPathResult.value = null
    return
  }

  try {
    const result = jsonPath(parsedResponseJson.value, jsonPathExpression.value)
    jsonPathResult.value = JSON.stringify(result, null, 2)
  } catch (error) {
    jsonPathResult.value = `错误: ${error.message}`
    console.error('JSONPath解析错误:', error)
  }
}

const jsonPath = (obj, path) => {
  try {
    const paths = path.replace(/^\$/, '').split('.').filter(p => p)
    let result = obj
    for (const p of paths) {
      const matches = p.match(/(\w+)\[(\d+)\]/)
      if (matches) {
        result = result[matches[1]][parseInt(matches[2])]
      } else {
        result = result[p]
      }
    }
    return result
  } catch {
    throw new Error('无效的JSON路径')
  }
}

const copyJsonPathResult = async () => {
  if (!jsonPathResult.value) return
  try {
    await navigator.clipboard.writeText(jsonPathResult.value)
    ElMessage.success('复制成功')
  } catch (error) {
    ElMessage.error('复制失败')
    console.error('复制失败:', error)
  }
}

const formatAssertionValue = (value) => {
  if (value === null) return 'null'
  if (value === undefined) return 'undefined'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const getStatusType = (status) => {
  if (!status) return 'info'
  if (status >= 200 && status < 300) return 'success'
  if (status >= 300 && status < 400) return 'warning'
  if (status >= 400) return 'danger'
  return 'info'
}

const formatSize = (bytes) => {
  if (bytes === 0) return '0B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + sizes[i]
}

const openDataFactorySelectorForBody = (field) => {
  currentBodyField.value = field
  showDataFactorySelector.value = true
}

const openDataFactorySelectorForScript = (field) => {
  currentScriptField.value = field
  showDataFactorySelector.value = true
}

const handleDataFactorySelect = (dataFactoryItem) => {
  showDataFactorySelector.value = false
  const placeholder = `{{${dataFactoryItem.code}}}`

  if (currentBodyField.value === 'rawBody') {
    rawBody.value = rawBody.value || ''
    rawBody.value += placeholder
  } else if (currentScriptField.value === 'pre_request_script') {
    selectedRequest.value.pre_request_script += `\n${placeholder}`
  } else if (currentScriptField.value === 'post_request_script') {
    selectedRequest.value.post_request_script += `\n${placeholder}`
  }

  currentBodyField.value = ''
  currentScriptField.value = ''
}

const openVariableHelper = async (field) => {
  currentEditingField.value = field
  if (variableCategories.value.length === 0) {
    await loadVariableFunctions()
  }
  showVariableHelper.value = true
}

const loadVariableFunctions = async () => {
  try {
    const response = await getVariableFunctions()
    variableCategories.value = response.data || []
  } catch (error) {
    console.error('加载变量函数失败:', error)
  }
}

const insertVariable = (variable) => {
  const placeholder = variable.syntax || `{{${variable.name}}}`

  if (currentEditingField.value === 'rawBody') {
    rawBody.value = rawBody.value || ''
    rawBody.value += placeholder
  } else if (currentEditingField.value === 'pre_request_script') {
    selectedRequest.value.pre_request_script += `\n${placeholder}`
  } else if (currentEditingField.value === 'post_request_script') {
    selectedRequest.value.post_request_script += `\n${placeholder}`
  }

  showVariableHelper.value = false
  currentEditingField.value = ''
}

const importCurl = () => {
  showCurlImportDialog.value = true
}

const parseAndImportCurl = async () => {
  if (!curlCommand.value.trim()) {
    ElMessage.warning('请输入CURL命令')
    return
  }

  try {
    const parser = new RequestModelParser()
    const requestModel = parser.parse(curlCommand.value)

    if (requestModel) {
      const newRequest = {
        id: null,
        name: requestModel.name || '从CURL导入',
        url: requestModel.url,
        method: requestModel.method || 'GET',
        params: requestModel.params?.map(p => ({
          enabled: true,
          key: p.key,
          value: p.value,
          description: ''
        })) || [],
        headers: requestModel.headers?.map(h => ({
          enabled: true,
          key: h.key,
          value: h.value,
          description: ''
        })) || [],
        body: requestModel.body ? {
          type: requestModel.bodyType || 'raw',
          data: requestModel.body
        } : null,
        collection: null,
        project: selectedProject.value,
        pre_request_script: '',
        post_request_script: '',
        assertions: []
      }

      selectedRequest.value = newRequest
      closeCurlImportDialog()
      curlCommand.value = ''
      ElMessage.success('导入成功')
    } else {
      ElMessage.error('解析失败')
    }
  } catch (error) {
    ElMessage.error('导入失败')
    console.error('导入失败:', error)
  }
}

const exportRequest = () => {
  if (!selectedRequest.value) return

  try {
    const generator = new DataAnalysisGenerator()
    const curlCommand = generator.generateCurl(selectedRequest.value)
    navigator.clipboard.writeText(curlCommand).then(() => {
      ElMessage.success('已复制到剪贴板')
    })
  } catch (error) {
    ElMessage.error('导出失败')
    console.error('导出失败:', error)
  }
}

const generateDataAnalysis = async (language) => {
  if (!selectedRequest.value) {
    ElMessage.warning('请选择一个请求')
    return
  }

  try {
    const generator = new DataAnalysisGenerator()
    generatedDataAnalysis.value = await generator.generateDataAnalysis(language, {
      url: selectedRequest.value.url,
      method: selectedRequest.value.method,
      headers: selectedRequest.value.headers?.reduce((acc, h) => {
        if (h.enabled) acc[h.key] = h.value
        return acc
      }, {}) || {},
      params: selectedRequest.value.params?.reduce((acc, p) => {
        if (p.enabled) acc[p.key] = p.value
        return acc
      }, {}) || {},
      body: bodyType.value === 'raw' ? rawBody.value : null
    })
    codeLanguage.value = language
    showDataAnalysisGenerateDialog.value = true
  } catch (error) {
    ElMessage.error('生成代码失败')
    console.error('生成代码失败:', error)
  }
}

const copyGeneratedDataAnalysis = async () => {
  if (!generatedDataAnalysis.value) return
  try {
    await navigator.clipboard.writeText(generatedDataAnalysis.value)
    ElMessage.success('复制成功')
  } catch (error) {
    ElMessage.error('复制失败')
    console.error('复制失败:', error)
  }
}

const getMethodIconClass = (method) => {
  const methodClassMap = {
    GET: 'method-get',
    POST: 'method-post',
    PUT: 'method-put',
    DELETE: 'method-delete',
    PATCH: 'method-patch',
    HEAD: 'method-head',
    OPTIONS: 'method-options'
  }
  return methodClassMap[method] || ''
}

const handleClickOutside = (event) => {
  const target = event.target
  if (!target.closest('.context-menu') && !target.closest('.el-tree-node__content')) {
    showContextMenu.value = false
  }
}

onMounted(() => {
  loadProjects()
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  closeWebSocketConnection()
})
</script>

<style scoped>
.interface-management {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.interface-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* 左侧侧边栏 */
.sidebar {
  width: 280px;
  background: #f5f7fa;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 12px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
}

.sidebar-header :deep(.el-select) {
  margin-bottom: 10px;
}

.header-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.collection-tree {
  flex: 1;
  overflow: auto;
  padding: 8px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  padding: 2px 0;
}

.node-icon {
  font-size: 14px;
  color: #909399;
}

.node-icon.folder-open {
  color: #409eff;
}

.node-icon.method-get { color: #67c23a; }
.node-icon.method-post { color: #409eff; }
.node-icon.method-put { color: #e6a23c; }
.node-icon.method-delete { color: #f56c6c; }
.node-icon.method-patch { color: #909399; }
.node-icon.method-head { color: #6f7ad3; }
.node-icon.method-options { color: #c0c4cc; }

.node-label {
  flex: 1;
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-edit {
  flex: 1;
}

.method-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  color: white;
  font-weight: 600;
}

.method-tag.get { background: #67c23a; }
.method-tag.post { background: #409eff; }
.method-tag.put { background: #e6a23c; }
.method-tag.delete { background: #f56c6c; }
.method-tag.patch { background: #909399; }

/* 搜索结果 */
.search-results {
  margin-top: 10px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.search-results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid #e4e7ed;
  font-size: 13px;
  font-weight: 500;
}

.search-result-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f5f7fa;
}

.search-result-item:hover {
  background: #f5f7fa;
}

.search-result-content {
  flex: 1;
  overflow: hidden;
}

.search-result-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-result-url {
  font-size: 11px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 右侧主内容 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
}

.empty-content {
  text-align: center;
}

.empty-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-icon .icon {
  font-size: 40px;
  color: white;
}

.empty-content h3 {
  margin: 0 0 8px;
  font-size: 18px;
  color: #606266;
}

.empty-content p {
  margin: 0 0 16px;
  font-size: 14px;
  color: #909399;
}

/* 请求详情 */
.request-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 请求头部 */
.request-header {
  background: white;
  border-bottom: 1px solid #e4e7ed;
  padding: 12px 16px;
}

.request-line {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
}

.method-select {
  width: 100px;
  font-weight: 600;
}

.method-select.get { --el-select-hover-border-color: #67c23a; }
.method-select.post { --el-select-hover-border-color: #409eff; }
.method-select.put { --el-select-hover-border-color: #e6a23c; }
.method-select.delete { --el-select-hover-border-color: #f56c6c; }

.url-input {
  flex: 1;
}

.env-select {
  width: 150px;
}

.send-button {
  width: 100px;
}

.request-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.name-input {
  width: 200px;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

/* 请求标签页 */
.request-tabs {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.request-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: auto;
  padding: 16px;
}

.tab-content-wrapper {
  height: 100%;
}

/* 认证容器 */
.auth-container {
  padding: 10px;
}

.auth-type-select {
  width: 200px;
  margin-bottom: 15px;
}

.auth-config {
  background: #fafafa;
  padding: 15px;
  border-radius: 6px;
}

.auth-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  font-size: 12px;
  color: #909399;
}

.no-auth-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 30px;
  color: #67c23a;
}

.no-auth-info span {
  font-size: 14px;
}

/* Body容器 */
.body-container {
  padding: 10px;
}

.body-content {
  margin-top: 15px;
}

.raw-options {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
  align-items: center;
}

.raw-body {
  width: 100%;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 13px;
}

.data-factory-btn, .variable-helper-btn {
  margin-left: auto;
}

.binary-upload {
  border: 2px dashed #d9d9d9;
  border-radius: 6px;
  padding: 30px;
}

.uploaded-file {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

/* 脚本编辑器 */
.script-editor-container {
  height: 100%;
}

.script-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-size: 13px;
  color: #606266;
}

.script-actions {
  display: flex;
  gap: 8px;
}

.script-editor {
  width: 100%;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 13px;
}

/* 断言编辑器 */
.assertions-editor {
  padding: 10px;
}

.assertions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.assertions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.assertion-item {
  background: #fafafa;
  border-radius: 6px;
  padding: 12px;
}

.assertion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.assertion-name {
  flex: 1;
  margin-right: 10px;
}

.assertion-config {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.assertion-params {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
  padding-left: 10px;
  border-left: 2px solid #e4e7ed;
}

.assertion-param-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.param-label {
  font-size: 13px;
  color: #606266;
  width: 120px;
}

.param-unit {
  font-size: 12px;
  color: #909399;
}

.flex-1 {
  flex: 1;
}

.no-assertions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 30px;
  color: #909399;
}

.no-assertions p {
  margin: 0;
}

/* WebSocket消息容器 */
.message-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.message-input-section {
  padding: 10px;
}

.message-actions {
  display: flex;
  gap: 10px;
}

.websocket-response-section {
  flex: 1;
  border-top: 1px solid #e4e7ed;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.websocket-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: #f5f7fa;
}

.websocket-header h3 {
  margin: 0;
  font-size: 14px;
}

.websocket-messages {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.websocket-message-item {
  margin-bottom: 10px;
  padding: 10px;
  border-radius: 6px;
}

.websocket-message-item.sent {
  background: #e8f5e9;
  margin-left: 50px;
}

.websocket-message-item.received {
  background: #f3e5f5;
  margin-right: 50px;
}

.websocket-message-item.connected {
  background: #e3f2fd;
}

.websocket-message-item.info {
  background: #fff8e1;
}

.websocket-message-item.error {
  background: #ffebee;
}

.message-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.message-type {
  font-size: 12px;
  font-weight: 500;
}

.message-type.sent { color: #2e7d32; }
.message-type.received { color: #7b1fa2; }
.message-type.connected { color: #1565c0; }
.message-type.info { color: #f57c00; }
.message-type.error { color: #c62828; }

.message-time {
  font-size: 11px;
  color: #909399;
}

.message-content {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 13px;
  word-break: break-all;
}

.message-content pre {
  margin: 0;
  white-space: pre-wrap;
}

/* 响应区域 */
.response-section {
  border-top: 1px solid #e4e7ed;
  background: white;
}

.response-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}

.response-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.response-title h3 {
  margin: 0;
  font-size: 14px;
}

.response-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-tag {
  font-size: 12px;
  font-weight: 600;
}

.response-time, .response-size {
  font-size: 12px;
  color: #606266;
}

/* 响应Body */
.response-body {
  padding: 12px;
}

.response-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.response-view-options {
  display: flex;
  gap: 10px;
}

.jsonpath-extractor {
  margin-bottom: 12px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 6px;
}

.jsonpath-input {
  margin-bottom: 10px;
}

.jsonpath-result {
  padding: 10px;
  background: white;
  border-radius: 4px;
}

.jsonpath-result strong {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
}

.jsonpath-result pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.json-tree-view {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 13px;
}

.response-content {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 400px;
  overflow-y: auto;
}

/* 响应Headers */
.response-headers {
  padding: 12px;
}

.header-row {
  display: flex;
  padding: 6px 0;
  border-bottom: 1px solid #f5f7fa;
}

.header-name {
  font-weight: 500;
  color: #303133;
  min-width: 150px;
}

.header-value {
  color: #606266;
}

/* 响应Cookies */
.response-cookies {
  padding: 12px;
}

.cookies-table {
  width: 100%;
  border-collapse: collapse;
}

.cookies-header, .cookies-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  padding: 8px;
  text-align: left;
}

.cookies-header {
  background: #f5f7fa;
  font-weight: 500;
  font-size: 12px;
}

.cookies-row {
  border-bottom: 1px solid #f5f7fa;
  font-size: 12px;
}

/* 响应Preview */
.response-preview {
  height: 400px;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

/* 断言结果 */
.assertions-results {
  padding: 12px;
}

.assertions-summary {
  display: flex;
  gap: 12px;
  margin-bottom: 15px;
}

.summary-item {
  font-size: 13px;
}

.assertion-result-item {
  margin-bottom: 10px;
  padding: 12px;
  border-radius: 6px;
}

.assertion-result-item.passed {
  background: #f0f9eb;
  border-left: 3px solid #67c23a;
}

.assertion-result-item.failed {
  background: #fef0f0;
  border-left: 3px solid #f56c6c;
}

.assertion-result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.assertion-result-header .assertion-name {
  font-weight: 500;
}

.assertion-result-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.result-row {
  display: flex;
  gap: 10px;
  font-size: 13px;
}

.result-row .label {
  color: #606266;
  min-width: 60px;
}

.result-row .value {
  color: #303133;
}

.result-row .value.error {
  color: #f56c6c;
}

/* 右键菜单 */
.context-menu {
  position: fixed;
  z-index: 9999;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 4px 0;
  min-width: 160px;
}

.context-menu li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 13px;
  color: #303133;
}

.context-menu li:hover {
  background: #f5f7fa;
}

.context-menu li.divider {
  height: 1px;
  background: #e4e7ed;
  padding: 0;
  margin: 4px 0;
  cursor: default;
}

.context-menu li.divider:hover {
  background: transparent;
}

/* CURL导入 */
.curl-input {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 12px;
}

/* 代码生成 */
.code-generate {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 12px;
  background: #1e1e1e;
  color: #d4d4d4;
}

/* 请求历史 */
.history-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.history-filter {
  display: flex;
  gap: 10px;
  padding: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.history-item {
  padding: 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
}

.history-item:hover {
  border-color: #409eff;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.history-time {
  font-size: 11px;
  color: #909399;
}

.history-url {
  font-size: 13px;
  color: #303133;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-info {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: #606266;
}

.empty-history {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #909399;
}

.empty-history p {
  margin: 8px 0 0;
}
</style>