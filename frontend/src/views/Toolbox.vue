<template>
  <div class="toolbox-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-text">
        <div class="header-title-row">
          <el-button class="back-btn" text @click="goHome">
            <el-icon><ArrowLeft /></el-icon>
            <span>返回主页</span>
          </el-button>
        </div>
        <h1>工具集中心</h1>
        <p>一站式测试工具与开发辅助工具集合，覆盖测试、转码、常用三大类</p>
      </div>
      <div class="header-stats">
        <div class="stat-item">
          <span class="stat-num">{{ tools.length }}</span>
          <span class="stat-label">可用工具</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ categories.length }}</span>
          <span class="stat-label">工具分类</span>
        </div>
      </div>
    </div>

    <!-- 搜索栏 -->
    <div class="search-section">
      <div class="search-box">
        <el-icon class="search-icon"><Search /></el-icon>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索工具名称或功能描述..."
        />
        <el-icon v-if="searchQuery" class="clear-icon" @click="searchQuery = ''"><Close /></el-icon>
      </div>
    </div>

    <!-- 最近使用 -->
    <div v-if="recentTools.length > 0 && !searchQuery" class="recent-section">
      <div class="section-header">
        <h3>
          <el-icon><Clock /></el-icon>
          最近使用
        </h3>
        <el-button text type="info" @click="clearRecent">清空记录</el-button>
      </div>
      <div class="recent-grid">
        <div
          v-for="tool in recentTools"
          :key="tool.id"
          class="recent-item"
          @click="openTool(tool)"
        >
          <div class="recent-icon" :class="tool.tone">
            <el-icon :size="16"><component :is="tool.icon" /></el-icon>
          </div>
          <span>{{ tool.name }}</span>
        </div>
      </div>
    </div>

    <!-- 分类标签 -->
    <div v-if="!searchQuery" class="category-tabs">
      <button
        v-for="category in categories"
        :key="category.id"
        class="category-tab"
        :class="{ active: activeCategory === category.id }"
        @click="activeCategory = category.id"
      >
        <el-icon><component :is="category.icon" /></el-icon>
        <span>{{ category.name }}</span>
        <span class="tab-count">{{ countByCategory(category.id) }}</span>
      </button>
    </div>

    <!-- 工具网格 -->
    <div class="tools-grid">
      <div
        v-for="tool in filteredTools"
        :key="tool.id"
        class="tool-card"
        @click="openTool(tool)"
      >
        <div class="tool-icon" :class="tool.tone">
          <el-icon :size="24"><component :is="tool.icon" /></el-icon>
        </div>
        <div class="tool-info">
          <h4>{{ tool.name }}</h4>
          <p>{{ tool.description }}</p>
        </div>
        <div class="tool-action">
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>
      <div v-if="filteredTools.length === 0" class="empty-state">
        <el-icon :size="48"><Search /></el-icon>
        <p>未找到匹配的工具</p>
      </div>
    </div>

    <!-- 工具弹窗 -->
    <el-dialog
      v-model="showToolModal"
      :title="currentTool?.name || ''"
      width="820px"
      top="6vh"
      destroy-on-close
      append-to-body
    >
      <div v-if="currentTool" class="tool-modal-content">
        <!-- 单元测试生成器 -->
        <div v-if="currentTool.id === 'unit-test-generator'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>编程语言</label>
              <el-select v-model="toolData.unitTestLang" style="width:100%">
                <el-option label="JavaScript" value="javascript" />
                <el-option label="TypeScript" value="typescript" />
                <el-option label="Python" value="python" />
                <el-option label="Java" value="java" />
              </el-select>
            </div>
            <div class="panel-section">
              <label>测试框架</label>
              <el-select v-model="toolData.unitTestFramework" style="width:100%">
                <el-option label="Jest" value="jest" />
                <el-option label="Mocha/Chai" value="mocha" />
                <el-option label="pytest" value="pytest" />
                <el-option label="JUnit5" value="junit" />
              </el-select>
            </div>
          </div>
          <div class="panel-section">
            <label>输入代码（粘贴函数/方法）</label>
            <textarea v-model="toolData.unitTestInput" rows="8" placeholder="function add(a, b) { return a + b; }"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="generateUnitTest">生成测试代码</el-button>
          </div>
          <div v-if="toolData.unitTestOutput" class="panel-section">
            <div class="output-header">
              <label>生成结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.unitTestOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.unitTestOutput }}</pre>
          </div>
        </div>

        <!-- API测试工具 -->
        <div v-else-if="currentTool.id === 'api-tester'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section" style="flex:0 0 130px">
              <label>请求方法</label>
              <el-select v-model="toolData.apiMethod" style="width:100%">
                <el-option label="GET" value="GET" />
                <el-option label="POST" value="POST" />
                <el-option label="PUT" value="PUT" />
                <el-option label="PATCH" value="PATCH" />
                <el-option label="DELETE" value="DELETE" />
              </el-select>
            </div>
            <div class="panel-section">
              <label>请求 URL</label>
              <input v-model="toolData.apiUrl" placeholder="https://api.example.com/users" />
            </div>
          </div>
          <div class="panel-section">
            <label>请求头 (JSON)</label>
            <textarea v-model="toolData.apiHeaders" rows="3" placeholder='{"Content-Type": "application/json"}'></textarea>
          </div>
          <div v-if="['POST','PUT','PATCH'].includes(toolData.apiMethod)" class="panel-section">
            <label>请求体 (JSON)</label>
            <textarea v-model="toolData.apiBody" rows="5" placeholder='{"key": "value"}'></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" :loading="toolData.apiLoading" @click="testApi">发送请求</el-button>
          </div>
          <div v-if="toolData.apiResponse" class="panel-section">
            <div class="output-header">
              <label>响应结果 <span v-if="toolData.apiStatus" class="status-badge" :class="toolData.apiStatusOk ? 'ok' : 'err'">{{ toolData.apiStatus }}</span></label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.apiResponse)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.apiResponse }}</pre>
          </div>
        </div>

        <!-- Mock数据生成器 -->
        <div v-else-if="currentTool.id === 'mock-generator'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>数据类型</label>
              <el-select v-model="toolData.mockType" style="width:100%">
                <el-option label="用户数据" value="user" />
                <el-option label="产品数据" value="product" />
                <el-option label="订单数据" value="order" />
                <el-option label="自定义模板" value="custom" />
              </el-select>
            </div>
            <div class="panel-section">
              <label>生成数量</label>
              <el-input-number v-model="toolData.mockCount" :min="1" :max="100" style="width:100%" />
            </div>
          </div>
          <div v-if="toolData.mockType === 'custom'" class="panel-section">
            <label>模板 (支持 @name @integer(min,max) @email @phone @date @bool)</label>
            <textarea v-model="toolData.mockTemplate" rows="5" placeholder='{"name": "@name", "age": "@integer(18,60)"}'></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="generateMock">生成数据</el-button>
          </div>
          <div v-if="toolData.mockOutput" class="panel-section">
            <div class="output-header">
              <label>生成结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.mockOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.mockOutput }}</pre>
          </div>
        </div>

        <!-- 覆盖率计算器 -->
        <div v-else-if="currentTool.id === 'coverage-calculator'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>总行数</label>
              <el-input-number v-model="toolData.coverageLines" :min="1" style="width:100%" />
            </div>
            <div class="panel-section">
              <label>已覆盖行数</label>
              <el-input-number v-model="toolData.coverageCovered" :min="0" style="width:100%" />
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="calculateCoverage">计算覆盖率</el-button>
          </div>
          <div v-if="toolData.coverageResult !== null" class="panel-section">
            <label>覆盖率结果</label>
            <div class="coverage-result">
              <div class="coverage-bar">
                <div class="coverage-fill" :style="{ width: toolData.coverageResult + '%' }" :class="getCoverageClass(toolData.coverageResult)"></div>
              </div>
              <div class="coverage-meta">
                <span class="coverage-value">{{ toolData.coverageResult.toFixed(2) }}%</span>
                <span class="coverage-status" :class="getCoverageClass(toolData.coverageResult)">{{ getCoverageStatus(toolData.coverageResult) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- JSON/XML转换器 -->
        <div v-else-if="currentTool.id === 'json-xml-converter'" class="tool-panel">
          <div class="seg-tabs">
            <button :class="{ active: convertDirection === 'json2xml' }" @click="convertDirection = 'json2xml'">JSON → XML</button>
            <button :class="{ active: convertDirection === 'xml2json' }" @click="convertDirection = 'xml2json'">XML → JSON</button>
          </div>
          <div class="panel-section">
            <label>{{ convertDirection === 'json2xml' ? 'JSON 输入' : 'XML 输入' }}</label>
            <textarea v-model="toolData.convertInput" rows="8" :placeholder="convertPlaceholder"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertData">转换</el-button>
          </div>
          <div v-if="toolData.convertOutput" class="panel-section">
            <div class="output-header">
              <label>转换结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.convertOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.convertOutput }}</pre>
          </div>
        </div>

        <!-- 代码格式化器 -->
        <div v-else-if="currentTool.id === 'code-formatter'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>语言</label>
              <el-select v-model="toolData.formatLang" style="width:100%">
                <el-option label="JSON" value="json" />
                <el-option label="JavaScript" value="javascript" />
                <el-option label="CSS" value="css" />
                <el-option label="HTML/XML" value="html" />
              </el-select>
            </div>
            <div class="panel-section">
              <label>缩进</label>
              <el-select v-model="toolData.formatIndent" style="width:100%">
                <el-option label="2 空格" value="2" />
                <el-option label="4 空格" value="4" />
                <el-option label="Tab" value="tab" />
              </el-select>
            </div>
          </div>
          <div class="panel-section">
            <label>输入代码</label>
            <textarea v-model="toolData.formatInput" rows="8" placeholder="粘贴需要格式化的代码..."></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="formatCode">格式化</el-button>
            <el-button @click="minifyCode">压缩</el-button>
          </div>
          <div v-if="toolData.formatOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.formatOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.formatOutput }}</pre>
          </div>
        </div>

        <!-- Base64编解码器 -->
        <div v-else-if="currentTool.id === 'base64-encoder'" class="tool-panel">
          <div class="seg-tabs">
            <button :class="{ active: encodeMode === 'encode' }" @click="encodeMode = 'encode'">编码</button>
            <button :class="{ active: encodeMode === 'decode' }" @click="encodeMode = 'decode'">解码</button>
          </div>
          <div class="panel-section">
            <label>{{ encodeMode === 'encode' ? '待编码文本' : '待解码 Base64' }}</label>
            <textarea v-model="toolData.base64Input" rows="6" placeholder="输入内容..."></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="handleBase64">执行{{ encodeMode === 'encode' ? '编码' : '解码' }}</el-button>
          </div>
          <div v-if="toolData.base64Output" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.base64Output)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.base64Output }}</pre>
          </div>
        </div>

        <!-- URL编解码 -->
        <div v-else-if="currentTool.id === 'url-encoder'" class="tool-panel">
          <div class="seg-tabs">
            <button :class="{ active: urlEncodeMode === 'encode' }" @click="urlEncodeMode = 'encode'">URL 编码</button>
            <button :class="{ active: urlEncodeMode === 'decode' }" @click="urlEncodeMode = 'decode'">URL 解码</button>
          </div>
          <div class="panel-section">
            <label>{{ urlEncodeMode === 'encode' ? '待编码内容' : '待解码内容' }}</label>
            <textarea v-model="toolData.urlInput" rows="5" placeholder="输入 URL 或文本..."></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="handleUrlEncode">执行{{ urlEncodeMode === 'encode' ? '编码' : '解码' }}</el-button>
          </div>
          <div v-if="toolData.urlOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.urlOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.urlOutput }}</pre>
          </div>
        </div>

        <!-- JSON格式化/校验 -->
        <div v-else-if="currentTool.id === 'json-formatter'" class="tool-panel">
          <div class="panel-section">
            <label>JSON 输入</label>
            <textarea v-model="toolData.jsonInput" rows="9" placeholder='{"name":"test","list":[1,2,3]}'></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="formatJson">格式化校验</el-button>
            <el-button @click="compressJson">压缩</el-button>
          </div>
          <div v-if="toolData.jsonError" class="error-box">{{ toolData.jsonError }}</div>
          <div v-if="toolData.jsonOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.jsonOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.jsonOutput }}</pre>
          </div>
        </div>

        <!-- 时间戳转换器 -->
        <div v-else-if="currentTool.id === 'timestamp-converter'" class="tool-panel">
          <div class="info-box">
            当前时间戳（秒）：<strong>{{ currentTimestamp }}</strong>
            <el-button text type="primary" size="small" @click="copyToClipboard(String(currentTimestamp))">复制</el-button>
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>时间戳 → 日期</label>
              <input v-model="toolData.timestampInput" placeholder="支持秒或毫秒" />
            </div>
            <div class="panel-section" style="flex:0 0 130px;display:flex;align-items:flex-end">
              <el-button type="primary" style="width:100%" @click="convertTimestamp">转换</el-button>
            </div>
          </div>
          <div v-if="toolData.timestampOutput" class="result-box">{{ toolData.timestampOutput }}</div>
          <div class="panel-row" style="margin-top:8px">
            <div class="panel-section">
              <label>日期 → 时间戳</label>
              <input v-model="toolData.dateInput" placeholder="2024-01-01 12:00:00" />
            </div>
            <div class="panel-section" style="flex:0 0 130px;display:flex;align-items:flex-end">
              <el-button type="primary" style="width:100%" @click="dateToTimestamp">转换</el-button>
            </div>
          </div>
          <div v-if="toolData.dateOutput" class="result-box">{{ toolData.dateOutput }}</div>
        </div>

        <!-- UUID生成器 -->
        <div v-else-if="currentTool.id === 'uuid-generator'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>UUID 版本</label>
              <el-select v-model="toolData.uuidVersion" style="width:100%">
                <el-option label="Version 4 (随机)" value="v4" />
                <el-option label="Version 1 (时间戳)" value="v1" />
              </el-select>
            </div>
            <div class="panel-section">
              <label>数量</label>
              <el-input-number v-model="toolData.uuidCount" :min="1" :max="50" style="width:100%" />
            </div>
            <div class="panel-section">
              <label>格式</label>
              <el-select v-model="toolData.uuidCase" style="width:100%">
                <el-option label="小写" value="lower" />
                <el-option label="大写" value="upper" />
              </el-select>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="generateUuid">生成 UUID</el-button>
            <el-button v-if="toolData.uuidOutput.length" @click="copyToClipboard(toolData.uuidOutput.join('\n'))">复制全部</el-button>
          </div>
          <div v-if="toolData.uuidOutput.length" class="panel-section">
            <div class="uuid-list">
              <div v-for="(uuid, index) in toolData.uuidOutput" :key="index" class="uuid-item">
                <span>{{ uuid }}</span>
                <el-button text type="primary" size="small" @click="copyToClipboard(uuid)">复制</el-button>
              </div>
            </div>
          </div>
        </div>

        <!-- 哈希计算器 -->
        <div v-else-if="currentTool.id === 'hash-calculator'" class="tool-panel">
          <div class="panel-section">
            <label>输入文本</label>
            <textarea v-model="toolData.hashInput" rows="5" placeholder="输入要计算哈希的文本..."></textarea>
          </div>
          <div class="panel-section">
            <label>选择算法</label>
            <div class="hash-checkboxes">
              <el-checkbox v-model="toolData.hashAlgorithms.sha1">SHA-1</el-checkbox>
              <el-checkbox v-model="toolData.hashAlgorithms.sha256">SHA-256</el-checkbox>
              <el-checkbox v-model="toolData.hashAlgorithms.sha384">SHA-384</el-checkbox>
              <el-checkbox v-model="toolData.hashAlgorithms.sha512">SHA-512</el-checkbox>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" :loading="toolData.hashLoading" @click="calculateHash">计算哈希</el-button>
          </div>
          <div v-if="toolData.hashOutput" class="panel-section">
            <label>计算结果</label>
            <div class="hash-results">
              <div v-for="(value, key) in toolData.hashOutput" :key="key" class="hash-item">
                <span class="hash-label">{{ key.toUpperCase() }}</span>
                <span class="hash-value">{{ value }}</span>
                <el-button text type="primary" size="small" @click="copyToClipboard(value)">复制</el-button>
              </div>
            </div>
          </div>
        </div>

        <!-- 正则表达式测试器 -->
        <div v-else-if="currentTool.id === 'regex-tester'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>正则表达式</label>
              <input v-model="toolData.regexPattern" placeholder="\d{3}-\d{4}" />
            </div>
            <div class="panel-section" style="flex:0 0 130px">
              <label>标志</label>
              <input v-model="toolData.regexFlags" placeholder="gim" />
            </div>
          </div>
          <div class="panel-section">
            <label>测试文本</label>
            <textarea v-model="toolData.regexTestText" rows="6" placeholder="输入要测试的文本..."></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="testRegex">测试匹配</el-button>
          </div>
          <div v-if="toolData.regexResult" class="panel-section">
            <label>匹配结果</label>
            <div class="regex-result">
              <div class="match-count">共找到 {{ toolData.regexMatchCount }} 个匹配</div>
              <div v-for="(match, index) in toolData.regexMatches" :key="index" class="match-item">
                <span class="match-index">{{ index + 1 }}</span>
                <span class="match-text">{{ match }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 大小写转换 -->
        <div v-else-if="currentTool.id === 'case-converter'" class="tool-panel">
          <div class="panel-section">
            <label>输入文本</label>
            <textarea v-model="toolData.caseInput" rows="6" placeholder="hello world example"></textarea>
          </div>
          <div class="panel-actions wrap">
            <el-button @click="convertCase('upper')">大写</el-button>
            <el-button @click="convertCase('lower')">小写</el-button>
            <el-button @click="convertCase('capitalize')">首字母大写</el-button>
            <el-button @click="convertCase('camel')">驼峰</el-button>
            <el-button @click="convertCase('snake')">下划线</el-button>
            <el-button @click="convertCase('kebab')">短横线</el-button>
          </div>
          <div v-if="toolData.caseOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.caseOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.caseOutput }}</pre>
          </div>
        </div>

        <!-- 颜色转换器 -->
        <div v-else-if="currentTool.id === 'color-converter'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>HEX 颜色</label>
              <input v-model="toolData.colorInput" placeholder="#2563eb" @input="convertColor" />
            </div>
            <div class="panel-section" style="flex:0 0 80px;display:flex;align-items:flex-end">
              <div class="color-preview" :style="{ background: toolData.colorValid ? toolData.colorInput : '#fff' }"></div>
            </div>
          </div>
          <div v-if="toolData.colorRgb" class="result-box">RGB：{{ toolData.colorRgb }}</div>
          <div v-if="toolData.colorHsl" class="result-box">HSL：{{ toolData.colorHsl }}</div>
        </div>

        <!-- 字数统计 -->
        <div v-else-if="currentTool.id === 'text-counter'" class="tool-panel">
          <div class="panel-section">
            <label>输入文本</label>
            <textarea v-model="toolData.counterInput" rows="8" placeholder="输入或粘贴文本，自动统计..." @input="countText"></textarea>
          </div>
          <div class="stat-grid">
            <div class="stat-cell"><span class="num">{{ toolData.counterStats.chars }}</span><span class="lbl">字符数</span></div>
            <div class="stat-cell"><span class="num">{{ toolData.counterStats.charsNoSpace }}</span><span class="lbl">字符(不含空格)</span></div>
            <div class="stat-cell"><span class="num">{{ toolData.counterStats.words }}</span><span class="lbl">单词数</span></div>
            <div class="stat-cell"><span class="num">{{ toolData.counterStats.lines }}</span><span class="lbl">行数</span></div>
            <div class="stat-cell"><span class="num">{{ toolData.counterStats.chinese }}</span><span class="lbl">中文字数</span></div>
          </div>
        </div>

        <!-- 随机密码生成器 -->
        <div v-else-if="currentTool.id === 'password-generator'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>密码长度：{{ toolData.pwdLength }}</label>
              <el-slider v-model="toolData.pwdLength" :min="4" :max="64" />
            </div>
          </div>
          <div class="panel-section">
            <label>包含字符</label>
            <div class="hash-checkboxes">
              <el-checkbox v-model="toolData.pwdUpper">大写字母</el-checkbox>
              <el-checkbox v-model="toolData.pwdLower">小写字母</el-checkbox>
              <el-checkbox v-model="toolData.pwdNumber">数字</el-checkbox>
              <el-checkbox v-model="toolData.pwdSymbol">特殊符号</el-checkbox>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="generatePassword">生成密码</el-button>
          </div>
          <div v-if="toolData.pwdOutput" class="panel-section">
            <div class="output-header">
              <label>生成结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.pwdOutput)">复制</el-button>
            </div>
            <div class="result-box big">{{ toolData.pwdOutput }}</div>
          </div>
        </div>

        <!-- 二维码生成器 -->
        <div v-else-if="currentTool.id === 'qrcode-generator'" class="tool-panel">
          <div class="panel-section">
            <label>输入文本或链接</label>
            <textarea v-model="toolData.qrInput" rows="4" placeholder="https://example.com"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="generateQrcode">生成二维码</el-button>
          </div>
          <div v-if="toolData.qrUrl" class="qr-preview">
            <img :src="toolData.qrUrl" alt="二维码" />
          </div>
        </div>

        <!-- 进制转换器 -->
        <div v-else-if="currentTool.id === 'number-base'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>输入数值</label>
              <input v-model="toolData.baseInput" placeholder="输入数值" />
            </div>
            <div class="panel-section" style="flex:0 0 140px">
              <label>源进制</label>
              <el-select v-model="toolData.baseFrom" style="width:100%">
                <el-option label="二进制 (2)" :value="2" />
                <el-option label="八进制 (8)" :value="8" />
                <el-option label="十进制 (10)" :value="10" />
                <el-option label="十六进制 (16)" :value="16" />
              </el-select>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertBase">转换</el-button>
          </div>
          <div v-if="toolData.baseResult" class="panel-section">
            <div class="result-box">二进制：{{ toolData.baseResult.bin }}</div>
            <div class="result-box">八进制：{{ toolData.baseResult.oct }}</div>
            <div class="result-box">十进制：{{ toolData.baseResult.dec }}</div>
            <div class="result-box">十六进制：{{ toolData.baseResult.hex }}</div>
          </div>
        </div>

        <!-- Cron表达式解析 -->
        <div v-else-if="currentTool.id === 'cron-parser'" class="tool-panel">
          <div class="panel-section">
            <label>Cron 表达式（分 时 日 月 周）</label>
            <input v-model="toolData.cronInput" placeholder="0 0 * * *" />
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="parseCron">解析</el-button>
          </div>
          <div v-if="toolData.cronOutput" class="result-box">{{ toolData.cronOutput }}</div>
          <div v-if="toolData.cronError" class="error-box">{{ toolData.cronError }}</div>
        </div>

        <!-- cURL 转代码 -->
        <div v-else-if="currentTool.id === 'curl-converter'" class="tool-panel">
          <div class="panel-section">
            <label>粘贴 cURL 命令</label>
            <textarea v-model="toolData.curlInput" rows="6" placeholder="curl -X POST 'https://api.example.com' -H 'Content-Type: application/json' -d '{}'"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertCurl">转换为 fetch</el-button>
          </div>
          <div v-if="toolData.curlOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.curlOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.curlOutput }}</pre>
          </div>
        </div>

        <!-- HTML 实体编解码 -->
        <div v-else-if="currentTool.id === 'html-entity'" class="tool-panel">
          <div class="seg-tabs">
            <button :class="{ active: toolData.htmlEntityMode === 'encode' }" @click="toolData.htmlEntityMode = 'encode'">转义</button>
            <button :class="{ active: toolData.htmlEntityMode === 'decode' }" @click="toolData.htmlEntityMode = 'decode'">还原</button>
          </div>
          <div class="panel-section">
            <label>{{ toolData.htmlEntityMode === 'encode' ? '原始文本' : 'HTML 实体' }}</label>
            <textarea v-model="toolData.htmlEntityInput" rows="6" :placeholder="toolData.htmlEntityMode === 'encode' ? '<div>测试</div>' : '&lt;div&gt;测试&lt;/div&gt;'"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="handleHtmlEntity">执行</el-button>
          </div>
          <div v-if="toolData.htmlEntityOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.htmlEntityOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.htmlEntityOutput }}</pre>
          </div>
        </div>

        <!-- Unicode 编解码 -->
        <div v-else-if="currentTool.id === 'unicode-converter'" class="tool-panel">
          <div class="seg-tabs">
            <button :class="{ active: toolData.unicodeMode === 'encode' }" @click="toolData.unicodeMode = 'encode'">中文转 Unicode</button>
            <button :class="{ active: toolData.unicodeMode === 'decode' }" @click="toolData.unicodeMode = 'decode'">Unicode 转中文</button>
          </div>
          <div class="panel-section">
            <label>输入</label>
            <textarea v-model="toolData.unicodeInput" rows="6" :placeholder="toolData.unicodeMode === 'encode' ? '你好世界' : '\\u4f60\\u597d'"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="handleUnicode">转换</el-button>
          </div>
          <div v-if="toolData.unicodeOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.unicodeOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.unicodeOutput }}</pre>
          </div>
        </div>

        <!-- JWT 解析 -->
        <div v-else-if="currentTool.id === 'jwt-decoder'" class="tool-panel">
          <div class="panel-section">
            <label>JWT Token</label>
            <textarea v-model="toolData.jwtInput" rows="5" placeholder="eyJhbGc...header.eyJzdWI...payload.signature"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="decodeJwt">解析</el-button>
          </div>
          <div v-if="toolData.jwtError" class="error-box">{{ toolData.jwtError }}</div>
          <div v-if="toolData.jwtHeader" class="panel-section">
            <label>Header</label>
            <pre class="code-output">{{ toolData.jwtHeader }}</pre>
          </div>
          <div v-if="toolData.jwtPayload" class="panel-section">
            <label>Payload</label>
            <pre class="code-output">{{ toolData.jwtPayload }}</pre>
          </div>
        </div>

        <!-- 图片格式转换 -->
        <div v-else-if="currentTool.id === 'image-format'" class="tool-panel">
          <div class="panel-section">
            <label>选择图片</label>
            <input type="file" accept="image/*" @change="onImgFmtChange" />
          </div>
          <div v-if="toolData.imgFmtSrc" class="img-preview"><img :src="toolData.imgFmtSrc" /></div>
          <div class="panel-row">
            <div class="panel-section">
              <label>目标格式</label>
              <el-select v-model="toolData.imgFmtTarget" style="width:100%">
                <el-option label="PNG" value="image/png" />
                <el-option label="JPEG" value="image/jpeg" />
                <el-option label="WebP" value="image/webp" />
              </el-select>
            </div>
            <div class="panel-section">
              <label>质量：{{ toolData.imgFmtQuality }}</label>
              <el-slider v-model="toolData.imgFmtQuality" :min="0.1" :max="1" :step="0.01" />
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" :loading="toolData.imgFmtLoading" @click="convertImageFormat">转换</el-button>
            <el-button v-if="toolData.imgFmtResult" @click="downloadImgFmt">下载</el-button>
          </div>
          <div v-if="toolData.imgFmtResult" class="img-preview"><img :src="toolData.imgFmtResult" /></div>
        </div>

        <!-- 图片转 PDF -->
        <div v-else-if="currentTool.id === 'image-to-pdf'" class="tool-panel">
          <div class="panel-section">
            <label>选择图片（可多选，按顺序合并）</label>
            <input type="file" accept="image/*" multiple @change="onImg2pdfChange" />
          </div>
          <div v-if="toolData.img2pdfFiles.length" class="thumb-grid">
            <div v-for="(f, idx) in toolData.img2pdfFiles" :key="idx" class="thumb-item">
              <img :src="f.src" />
              <span class="thumb-name">{{ f.name }}</span>
              <el-button text type="danger" size="small" @click="removeImg2pdf(idx)">移除</el-button>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" :loading="toolData.img2pdfLoading" @click="exportImg2pdf">生成并下载 PDF</el-button>
          </div>
        </div>

        <!-- PDF 转图片 -->
        <div v-else-if="currentTool.id === 'pdf-to-image'" class="tool-panel">
          <div class="panel-section">
            <label>选择 PDF 文件</label>
            <input type="file" accept="application/pdf" @change="onPdf2imgChange" />
          </div>
          <div v-if="toolData.pdf2imgLoading" class="info-box">正在解析 PDF，请稍候...</div>
          <div v-if="toolData.pdf2imgPages.length" class="thumb-grid">
            <div v-for="p in toolData.pdf2imgPages" :key="p.page" class="thumb-item">
              <img :src="p.url" />
              <span class="thumb-name">第 {{ p.page }} 页</span>
              <el-button text type="primary" size="small" @click="downloadPdfPage(p)">下载</el-button>
            </div>
          </div>
        </div>

        <!-- 图片转 Base64 -->
        <div v-else-if="currentTool.id === 'image-to-base64'" class="tool-panel">
          <div class="panel-section">
            <label>选择图片</label>
            <input type="file" accept="image/*" @change="onImg2b64Change" />
          </div>
          <div v-if="toolData.img2b64Result" class="img-preview"><img :src="toolData.img2b64Result" /></div>
          <div v-if="toolData.img2b64Result" class="panel-section">
            <div class="output-header">
              <label>Base64 / DataURL</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.img2b64Result)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.img2b64Result }}</pre>
          </div>
        </div>

        <!-- 图片压缩 -->
        <div v-else-if="currentTool.id === 'image-compress'" class="tool-panel">
          <div class="panel-section">
            <label>选择图片</label>
            <input type="file" accept="image/*" @change="onImgCompChange" />
          </div>
          <div class="panel-section">
            <label>压缩质量：{{ toolData.imgCompRatio }}</label>
            <el-slider v-model="toolData.imgCompRatio" :min="0.1" :max="1" :step="0.05" />
          </div>
          <div class="panel-actions">
            <el-button type="primary" :loading="toolData.imgCompLoading" @click="compressImage">压缩</el-button>
            <el-button v-if="toolData.imgCompResult" @click="downloadImgComp">下载</el-button>
          </div>
          <div v-if="toolData.imgCompResult" class="info-box">
            原始：{{ formatBytes(toolData.imgCompOrigSize) }} → 压缩后：约 {{ formatBytes(toolData.imgCompNewSize) }}
          </div>
          <div v-if="toolData.imgCompResult" class="img-preview"><img :src="toolData.imgCompResult" /></div>
        </div>

        <!-- Excel 转 JSON -->
        <div v-else-if="currentTool.id === 'excel-to-json'" class="tool-panel">
          <div class="panel-section">
            <label>选择 Excel / CSV 文件</label>
            <input type="file" accept=".xlsx,.xls,.csv" @change="onExcel2jsonChange" />
          </div>
          <div v-if="toolData.excel2jsonOutput" class="panel-section">
            <div class="output-header">
              <label>JSON 结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.excel2jsonOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.excel2jsonOutput }}</pre>
          </div>
        </div>

        <!-- JSON 转 Excel -->
        <div v-else-if="currentTool.id === 'json-to-excel'" class="tool-panel">
          <div class="panel-section">
            <label>JSON 数组</label>
            <textarea v-model="toolData.json2excelInput" rows="9" placeholder='[{"姓名":"张三","年龄":25},{"姓名":"李四","年龄":30}]'></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" :loading="toolData.json2excelLoading" @click="exportJson2excel">生成并下载 Excel</el-button>
          </div>
        </div>

        <!-- CSV / JSON 互转 -->
        <div v-else-if="currentTool.id === 'csv-json'" class="tool-panel">
          <div class="seg-tabs">
            <button :class="{ active: toolData.csvJsonMode === 'csv2json' }" @click="toolData.csvJsonMode = 'csv2json'">CSV → JSON</button>
            <button :class="{ active: toolData.csvJsonMode === 'json2csv' }" @click="toolData.csvJsonMode = 'json2csv'">JSON → CSV</button>
          </div>
          <div class="panel-section">
            <label>输入</label>
            <textarea v-model="toolData.csvJsonInput" rows="8" :placeholder="toolData.csvJsonMode === 'csv2json' ? 'name,age\n张三,25' : '[{&quot;name&quot;:&quot;张三&quot;,&quot;age&quot;:25}]'"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="handleCsvJson">转换</el-button>
          </div>
          <div v-if="toolData.csvJsonOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.csvJsonOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.csvJsonOutput }}</pre>
          </div>
        </div>

        <!-- Markdown 转 HTML -->
        <div v-else-if="currentTool.id === 'markdown-html'" class="tool-panel">
          <div class="panel-section">
            <label>Markdown</label>
            <textarea v-model="toolData.mdInput" rows="8" placeholder="# 标题&#10;- 列表项&#10;**加粗** *斜体*"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertMarkdown">转换</el-button>
          </div>
          <div v-if="toolData.mdOutput" class="panel-section">
            <div class="output-header">
              <label>HTML 源码</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.mdOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.mdOutput }}</pre>
          </div>
          <div v-if="toolData.mdOutput" class="panel-section">
            <label>预览</label>
            <div class="md-preview" v-html="toolData.mdOutput"></div>
          </div>
        </div>

        <!-- 文本去重排序 -->
        <div v-else-if="currentTool.id === 'text-dedupe'" class="tool-panel">
          <div class="panel-section">
            <label>输入文本（按行处理）</label>
            <textarea v-model="toolData.dedupeInput" rows="7" placeholder="每行一条数据"></textarea>
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>排序方式</label>
              <el-select v-model="toolData.dedupeSort" style="width:100%">
                <el-option label="不排序" value="none" />
                <el-option label="升序" value="asc" />
                <el-option label="降序" value="desc" />
              </el-select>
            </div>
            <div class="panel-section">
              <label>选项</label>
              <div class="hash-checkboxes">
                <el-checkbox v-model="toolData.dedupeTrim">去首尾空格</el-checkbox>
                <el-checkbox v-model="toolData.dedupeRemoveEmpty">去空行</el-checkbox>
              </div>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="handleDedupe">处理</el-button>
            <el-button v-if="toolData.dedupeOutput" @click="copyToClipboard(toolData.dedupeOutput)">复制结果</el-button>
          </div>
          <div v-if="toolData.dedupeOutput" class="panel-section">
            <pre class="code-output">{{ toolData.dedupeOutput }}</pre>
          </div>
        </div>

        <!-- 文本对比 -->
        <div v-else-if="currentTool.id === 'text-diff'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>文本 A</label>
              <textarea v-model="toolData.diffLeft" rows="7" placeholder="原始文本"></textarea>
            </div>
            <div class="panel-section">
              <label>文本 B</label>
              <textarea v-model="toolData.diffRight" rows="7" placeholder="对比文本"></textarea>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="handleDiff">对比</el-button>
          </div>
          <div v-if="toolData.diffResult.length" class="panel-section">
            <label>对比结果（高亮为差异行）</label>
            <div class="diff-result">
              <div v-for="row in toolData.diffResult" :key="row.line" class="diff-row" :class="{ diff: !row.same }">
                <span class="diff-ln">{{ row.line }}</span>
                <span class="diff-col">{{ row.left }}</span>
                <span class="diff-col">{{ row.right }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 随机文本生成 -->
        <div v-else-if="currentTool.id === 'lorem-ipsum'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>语言</label>
              <el-select v-model="toolData.loremType" style="width:100%">
                <el-option label="中文" value="cn" />
                <el-option label="英文 Lorem" value="en" />
              </el-select>
            </div>
            <div class="panel-section">
              <label>段落数</label>
              <el-input-number v-model="toolData.loremCount" :min="1" :max="20" style="width:100%" />
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="generateLorem">生成</el-button>
            <el-button v-if="toolData.loremOutput" @click="copyToClipboard(toolData.loremOutput)">复制</el-button>
          </div>
          <div v-if="toolData.loremOutput" class="panel-section">
            <pre class="code-output">{{ toolData.loremOutput }}</pre>
          </div>
        </div>

        <!-- 接口签名计算 -->
        <div v-else-if="currentTool.id === 'sign-calculator'" class="tool-panel">
          <div class="panel-section">
            <label>参数（JSON格式）</label>
            <textarea v-model="toolData.signParams" rows="4" placeholder='{"appId":"123","timestamp":123456}'></textarea>
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>密钥</label>
              <input v-model="toolData.signSecret" placeholder="输入密钥" />
            </div>
            <div class="panel-section">
              <label>算法</label>
              <el-select v-model="toolData.signAlgo" style="width:100%">
                <el-option label="MD5" value="md5" />
                <el-option label="SHA-256" value="sha256" />
              </el-select>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="calculateSign">生成签名</el-button>
          </div>
          <div v-if="toolData.signOutput" class="panel-section">
            <div class="output-header">
              <label>签名结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.signOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.signOutput }}</pre>
          </div>
        </div>

        <!-- 测试用例生成 -->
        <div v-else-if="currentTool.id === 'test-case-gen'" class="tool-panel">
          <div class="panel-section">
            <label>需求描述</label>
            <textarea v-model="toolData.testCaseInput" rows="5" placeholder="用户登录功能：用户名非空，密码至少6位，支持手机号登录"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="generateTestCase">生成测试用例</el-button>
          </div>
          <div v-if="toolData.testCaseOutput" class="panel-section">
            <div class="output-header">
              <label>测试用例</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.testCaseOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.testCaseOutput }}</pre>
          </div>
        </div>

        <!-- JSON Schema验证 -->
        <div v-else-if="currentTool.id === 'schema-validator'" class="tool-panel">
          <div class="panel-section">
            <label>Schema</label>
            <textarea v-model="toolData.schemaInput" rows="6" placeholder='{"type":"object","properties":{"name":{"type":"string"}}}'></textarea>
          </div>
          <div class="panel-section">
            <label>待验证JSON</label>
            <textarea v-model="toolData.schemaJson" rows="6" placeholder='{"name":"test"}'></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="validateSchema">验证</el-button>
          </div>
          <div v-if="toolData.schemaResult" class="result-box" :class="toolData.schemaValid ? 'success' : 'error'">
            {{ toolData.schemaValid ? '✓ 验证通过' : '✗ ' + toolData.schemaError }}
          </div>
        </div>

        <!-- CSS变量转SCSS -->
        <div v-else-if="currentTool.id === 'css-vars-converter'" class="tool-panel">
          <div class="seg-tabs">
            <button :class="{ active: toolData.cssVarMode === 'css2scss' }" @click="toolData.cssVarMode = 'css2scss'">CSS → SCSS</button>
            <button :class="{ active: toolData.cssVarMode === 'scss2css' }" @click="toolData.cssVarMode = 'scss2css'">SCSS → CSS</button>
          </div>
          <div class="panel-section">
            <label>输入</label>
            <textarea v-model="toolData.cssVarInput" rows="6" placeholder=":root { --primary: #2563eb; }"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertCssVars">转换</el-button>
          </div>
          <div v-if="toolData.cssVarOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.cssVarOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.cssVarOutput }}</pre>
          </div>
        </div>

        <!-- 代码注释生成 -->
        <div v-else-if="currentTool.id === 'comment-generator'" class="tool-panel">
          <div class="panel-section">
            <label>输入函数</label>
            <textarea v-model="toolData.commentInput" rows="6" placeholder="function add(a, b) { return a + b; }"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="generateComment">生成注释</el-button>
          </div>
          <div v-if="toolData.commentOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.commentOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.commentOutput }}</pre>
          </div>
        </div>

        <!-- SQL格式化 -->
        <div v-else-if="currentTool.id === 'sql-formatter'" class="tool-panel">
          <div class="panel-section">
            <label>SQL语句</label>
            <textarea v-model="toolData.sqlInput" rows="6" placeholder="SELECT * FROM users WHERE id=1 AND status='active'"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="formatSql">格式化</el-button>
          </div>
          <div v-if="toolData.sqlOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.sqlOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.sqlOutput }}</pre>
          </div>
        </div>

        <!-- YAML/JSON互转 -->
        <div v-else-if="currentTool.id === 'yaml-json'" class="tool-panel">
          <div class="seg-tabs">
            <button :class="{ active: toolData.yamlMode === 'yaml2json' }" @click="toolData.yamlMode = 'yaml2json'">YAML → JSON</button>
            <button :class="{ active: toolData.yamlMode === 'json2yaml' }" @click="toolData.yamlMode = 'json2yaml'">JSON → YAML</button>
          </div>
          <div class="panel-section">
            <label>输入</label>
            <textarea v-model="toolData.yamlInput" rows="6" placeholder="name: test&#10;value: 123"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertYamlJson">转换</el-button>
          </div>
          <div v-if="toolData.yamlOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.yamlOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.yamlOutput }}</pre>
          </div>
        </div>

        <!-- 图片加水印 -->
        <div v-else-if="currentTool.id === 'image-watermark'" class="tool-panel">
          <div class="panel-section">
            <label>选择图片</label>
            <input type="file" accept="image/*" @change="onWatermarkImgChange" />
          </div>
          <div v-if="toolData.watermarkSrc" class="img-preview"><img :src="toolData.watermarkSrc" /></div>
          <div class="panel-row">
            <div class="panel-section">
              <label>水印文字</label>
              <input v-model="toolData.watermarkText" placeholder="水印文字" />
            </div>
            <div class="panel-section">
              <label>透明度</label>
              <el-slider v-model="toolData.watermarkOpacity" :min="0.1" :max="1" :step="0.1" />
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="addWatermark">添加水印</el-button>
            <el-button v-if="toolData.watermarkResult" @click="downloadWatermark">下载</el-button>
          </div>
          <div v-if="toolData.watermarkResult" class="img-preview"><img :src="toolData.watermarkResult" /></div>
        </div>

        <!-- IP地址查询 -->
        <div v-else-if="currentTool.id === 'ip-checker'" class="tool-panel">
          <div class="panel-section">
            <label>IP地址</label>
            <input v-model="toolData.ipInput" placeholder="192.168.1.1" />
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="queryIp">查询</el-button>
          </div>
          <div v-if="toolData.ipResult" class="panel-section">
            <pre class="code-output">{{ toolData.ipResult }}</pre>
          </div>
        </div>

        <!-- 身份证验证 -->
        <div v-else-if="currentTool.id === 'id-card-validator'" class="tool-panel">
          <div class="panel-section">
            <label>身份证号码</label>
            <input v-model="toolData.idCardInput" placeholder="18位身份证号码" />
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="validateIdCard">验证</el-button>
          </div>
          <div v-if="toolData.idCardResult" class="result-box" :class="toolData.idCardValid ? 'success' : 'error'">
            {{ toolData.idCardResult }}
          </div>
        </div>

        <!-- 日期计算器 -->
        <div v-else-if="currentTool.id === 'date-calculator'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>开始日期</label>
              <input v-model="toolData.dateStart" placeholder="2024-01-01" />
            </div>
            <div class="panel-section">
              <label>结束日期</label>
              <input v-model="toolData.dateEnd" placeholder="2024-12-31" />
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="calculateDateDiff">计算天数</el-button>
          </div>
          <div v-if="toolData.dateDiffResult" class="result-box">{{ toolData.dateDiffResult }}</div>
        </div>

        <!-- 颜色选择器 -->
        <div v-else-if="currentTool.id === 'color-picker'" class="tool-panel">
          <div class="panel-section" style="text-align:center;">
            <div class="color-picker-box" :style="{ background: toolData.colorPickerValue }"></div>
            <input type="color" v-model="toolData.colorPickerValue" />
          </div>
          <div class="stat-grid">
            <div class="stat-cell"><span class="num">{{ toolData.colorPickerValue }}</span><span class="lbl">HEX</span></div>
            <div class="stat-cell"><span class="num">{{ toolData.colorPickerRgb }}</span><span class="lbl">RGB</span></div>
          </div>
          <div class="panel-actions">
            <el-button text type="primary" @click="copyToClipboard(toolData.colorPickerValue)">复制HEX</el-button>
            <el-button text type="primary" @click="copyToClipboard(toolData.colorPickerRgb)">复制RGB</el-button>
          </div>
        </div>

        <!-- 文件大小换算 -->
        <div v-else-if="currentTool.id === 'file-size-calc'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>数值</label>
              <el-input-number v-model="toolData.fileSizeValue" :min="0" style="width:100%" />
            </div>
            <div class="panel-section">
              <label>单位</label>
              <el-select v-model="toolData.fileSizeUnit" style="width:100%">
                <el-option label="B" value="b" />
                <el-option label="KB" value="kb" />
                <el-option label="MB" value="mb" />
                <el-option label="GB" value="gb" />
              </el-select>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertFileSize">换算</el-button>
          </div>
          <div v-if="toolData.fileSizeResult" class="panel-section">
            <div class="result-box">B: {{ toolData.fileSizeResult.b }}</div>
            <div class="result-box">KB: {{ toolData.fileSizeResult.kb }}</div>
            <div class="result-box">MB: {{ toolData.fileSizeResult.mb }}</div>
            <div class="result-box">GB: {{ toolData.fileSizeResult.gb }}</div>
          </div>
        </div>

        <!-- 数字格式化 -->
        <div v-else-if="currentTool.id === 'number-formatter'" class="tool-panel">
          <div class="panel-section">
            <label>输入数字</label>
            <input v-model="toolData.numberInput" placeholder="1234567.89" />
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="formatNumber">格式化</el-button>
          </div>
          <div v-if="toolData.numberOutput" class="panel-section">
            <div class="result-box">千分位: {{ toolData.numberOutput.thousand }}</div>
            <div class="result-box">货币: {{ toolData.numberOutput.currency }}</div>
            <div class="result-box">百分比: {{ toolData.numberOutput.percent }}</div>
          </div>
        </div>

        <!-- 密码强度检测 -->
        <div v-else-if="currentTool.id === 'pwd-strength'" class="tool-panel">
          <div class="panel-section">
            <label>密码</label>
            <input type="password" v-model="toolData.pwdStrengthInput" placeholder="输入密码" @input="checkPwdStrength" />
          </div>
          <div v-if="toolData.pwdStrengthResult" class="panel-section">
            <div class="pwd-strength-bar">
              <div class="pwd-bar" :class="toolData.pwdStrengthClass" :style="{ width: toolData.pwdStrengthPercent + '%' }"></div>
            </div>
            <div class="pwd-strength-text">{{ toolData.pwdStrengthResult }}</div>
          </div>
        </div>

        <!-- 数据脱敏 -->
        <div v-else-if="currentTool.id === 'data-masking'" class="tool-panel">
          <div class="panel-section">
            <label>原始数据</label>
            <textarea v-model="toolData.maskInput" rows="4" placeholder="手机号: 13812345678&#10;身份证: 110101199001011234"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="maskData">脱敏处理</el-button>
          </div>
          <div v-if="toolData.maskOutput" class="panel-section">
            <div class="output-header">
              <label>脱敏结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.maskOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.maskOutput }}</pre>
          </div>
        </div>

        <!-- DNS查询 -->
        <div v-else-if="currentTool.id === 'dns-lookup'" class="tool-panel">
          <div class="panel-section">
            <label>域名</label>
            <input v-model="toolData.dnsDomain" placeholder="example.com" />
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="lookupDns">查询</el-button>
          </div>
          <div v-if="toolData.dnsResult" class="panel-section">
            <pre class="code-output">{{ toolData.dnsResult }}</pre>
          </div>
        </div>

        <!-- 批量替换 -->
        <div v-else-if="currentTool.id === 'string-replace'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>查找</label>
              <input v-model="toolData.replaceFind" placeholder="要查找的内容" />
            </div>
            <div class="panel-section">
              <label>替换为</label>
              <input v-model="toolData.replaceReplace" placeholder="替换后的内容" />
            </div>
          </div>
          <div class="panel-section">
            <label>源文本</label>
            <textarea v-model="toolData.replaceInput" rows="5" placeholder="输入要处理的文本"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="stringReplace">替换</el-button>
          </div>
          <div v-if="toolData.replaceOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.replaceOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.replaceOutput }}</pre>
          </div>
        </div>

        <!-- Emoji选择器 -->
        <div v-else-if="currentTool.id === 'emoji-picker'" class="tool-panel">
          <div class="emoji-grid">
            <div v-for="emoji in emojiList" :key="emoji" class="emoji-item" @click="copyEmoji(emoji)">
              {{ emoji }}
            </div>
          </div>
        </div>

        <!-- XSS检测 -->
        <div v-else-if="currentTool.id === 'xss-tester'" class="tool-panel">
          <div class="panel-section">
            <label>输入内容</label>
            <textarea v-model="toolData.xssInput" rows="5" placeholder="输入要检测的内容"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="testXss">检测</el-button>
          </div>
          <div v-if="toolData.xssResult" class="result-box" :class="toolData.xssSafe ? 'success' : 'error'">
            {{ toolData.xssResult }}
          </div>
        </div>

        <!-- SQL注入检测 -->
        <div v-else-if="currentTool.id === 'sql-inject-check'" class="tool-panel">
          <div class="panel-section">
            <label>输入内容</label>
            <textarea v-model="toolData.sqlInjectInput" rows="5" placeholder="输入要检测的SQL语句或参数"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="checkSqlInject">检测</el-button>
          </div>
          <div v-if="toolData.sqlInjectResult" class="result-box" :class="toolData.sqlInjectSafe ? 'success' : 'error'">
            {{ toolData.sqlInjectResult }}
          </div>
        </div>

        <!-- CSRF Token生成 -->
        <div v-else-if="currentTool.id === 'csrf-token'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>长度</label>
              <el-input-number v-model="toolData.csrfLength" :min="16" :max="64" style="width:100%" />
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="generateCsrfToken">生成Token</el-button>
          </div>
          <div v-if="toolData.csrfOutput" class="panel-section">
            <div class="output-header">
              <label>Token</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.csrfOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.csrfOutput }}</pre>
          </div>
        </div>

        <!-- 测试报告生成 -->
        <div v-else-if="currentTool.id === 'report-generator'" class="tool-panel">
          <div class="panel-section">
            <label>项目名称</label>
            <input v-model="toolData.reportProject" placeholder="输入项目名称" />
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>用例总数</label>
              <el-input-number v-model="toolData.reportTotal" :min="0" style="width:100%" />
            </div>
            <div class="panel-section">
              <label>通过数</label>
              <el-input-number v-model="toolData.reportPass" :min="0" style="width:100%" />
            </div>
            <div class="panel-section">
              <label>失败数</label>
              <el-input-number v-model="toolData.reportFail" :min="0" style="width:100%" />
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="generateReport">生成报告</el-button>
          </div>
          <div v-if="toolData.reportOutput" class="panel-section">
            <div class="output-header">
              <label>测试报告</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.reportOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.reportOutput }}</pre>
          </div>
        </div>

        <!-- 性能测试工具 -->
        <div v-else-if="currentTool.id === 'perf-tester'" class="tool-panel">
          <div class="panel-section">
            <label>目标URL</label>
            <input v-model="toolData.perfUrl" placeholder="https://example.com" />
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>请求次数</label>
              <el-input-number v-model="toolData.perfCount" :min="1" :max="50" style="width:100%" />
            </div>
            <div class="panel-section">
              <label>请求方法</label>
              <el-select v-model="toolData.perfMethod" style="width:100%">
                <el-option label="GET" value="GET" />
                <el-option label="POST" value="POST" />
              </el-select>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" :loading="toolData.perfLoading" @click="runPerfTest">开始测试</el-button>
          </div>
          <div v-if="toolData.perfResult" class="panel-section">
            <div class="stat-grid">
              <div class="stat-cell"><span class="num">{{ toolData.perfResult.avg }}ms</span><span class="lbl">平均响应</span></div>
              <div class="stat-cell"><span class="num">{{ toolData.perfResult.min }}ms</span><span class="lbl">最快</span></div>
              <div class="stat-cell"><span class="num">{{ toolData.perfResult.max }}ms</span><span class="lbl">最慢</span></div>
              <div class="stat-cell"><span class="num">{{ toolData.perfResult.success }}/{{ toolData.perfResult.total }}</span><span class="lbl">成功率</span></div>
            </div>
          </div>
        </div>

        <!-- API Mock工具 -->
        <div v-else-if="currentTool.id === 'api-mocker'" class="tool-panel">
          <div class="panel-section">
            <label>接口路径</label>
            <input v-model="toolData.mockApiPath" placeholder="/api/users/list" />
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>状态码</label>
              <el-input-number v-model="toolData.mockStatus" :min="200" :max="599" style="width:100%" />
            </div>
            <div class="panel-section">
              <label>响应延迟(ms)</label>
              <el-input-number v-model="toolData.mockDelay" :min="0" :max="5000" style="width:100%" />
            </div>
          </div>
          <div class="panel-section">
            <label>响应体 (JSON)</label>
            <textarea v-model="toolData.mockResponseBody" rows="6" placeholder='{"code":200,"data":[]}'></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="generateMockApi">生成Mock配置</el-button>
          </div>
          <div v-if="toolData.mockApiOutput" class="panel-section">
            <div class="output-header">
              <label>Mock配置</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.mockApiOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.mockApiOutput }}</pre>
          </div>
        </div>

        <!-- 压力测试工具 -->
        <div v-else-if="currentTool.id === 'load-tester'" class="tool-panel">
          <div class="panel-section">
            <label>目标URL</label>
            <input v-model="toolData.loadUrl" placeholder="https://example.com/api" />
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>并发数</label>
              <el-input-number v-model="toolData.loadConcurrency" :min="1" :max="100" style="width:100%" />
            </div>
            <div class="panel-section">
              <label>总请求数</label>
              <el-input-number v-model="toolData.loadTotal" :min="1" :max="1000" style="width:100%" />
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" :loading="toolData.loadLoading" @click="runLoadTest">开始压测</el-button>
          </div>
          <div v-if="toolData.loadResult" class="panel-section">
            <pre class="code-output">{{ toolData.loadResult }}</pre>
          </div>
        </div>

        <!-- Socket测试工具 -->
        <div v-else-if="currentTool.id === 'socket-tester'" class="tool-panel">
          <div class="panel-section">
            <label>WebSocket地址</label>
            <input v-model="toolData.socketUrl" placeholder="wss://echo.websocket.org" />
          </div>
          <div class="panel-actions">
            <el-button type="primary" v-if="!toolData.socketConnected" @click="connectSocket">连接</el-button>
            <el-button type="danger" v-else @click="disconnectSocket">断开</el-button>
          </div>
          <div v-if="toolData.socketConnected" class="panel-section">
            <label>发送消息</label>
            <textarea v-model="toolData.socketSendMsg" rows="3" placeholder="输入要发送的消息"></textarea>
            <div class="panel-actions">
              <el-button type="primary" @click="sendSocketMsg">发送</el-button>
            </div>
          </div>
          <div v-if="toolData.socketLogs.length" class="panel-section">
            <label>消息记录</label>
            <div class="socket-log">
              <div v-for="(log, idx) in toolData.socketLogs" :key="idx" :class="['log-item', log.type]">
                <span class="log-time">[{{ log.time }}]</span>
                <span class="log-type">[{{ log.type === 'send' ? '发送' : log.type === 'recv' ? '接收' : '系统' }}]</span>
                <span class="log-content">{{ log.content }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 日志分析工具 -->
        <div v-else-if="currentTool.id === 'log-analyzer'" class="tool-panel">
          <div class="panel-section">
            <label>日志内容</label>
            <textarea v-model="toolData.logInput" rows="8" placeholder="粘贴日志内容..."></textarea>
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>过滤关键词</label>
              <input v-model="toolData.logKeyword" placeholder="输入关键词过滤" />
            </div>
            <div class="panel-section">
              <label>日志级别</label>
              <el-select v-model="toolData.logLevel" style="width:100%">
                <el-option label="全部" value="all" />
                <el-option label="ERROR" value="ERROR" />
                <el-option label="WARN" value="WARN" />
                <el-option label="INFO" value="INFO" />
                <el-option label="DEBUG" value="DEBUG" />
              </el-select>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="analyzeLog">分析</el-button>
          </div>
          <div v-if="toolData.logStats" class="stat-grid">
            <div class="stat-cell"><span class="num">{{ toolData.logStats.total }}</span><span class="lbl">总行数</span></div>
            <div class="stat-cell"><span class="num" style="color:#ef4444">{{ toolData.logStats.error }}</span><span class="lbl">ERROR</span></div>
            <div class="stat-cell"><span class="num" style="color:#f59e0b">{{ toolData.logStats.warn }}</span><span class="lbl">WARN</span></div>
            <div class="stat-cell"><span class="num" style="color:#3b82f6">{{ toolData.logStats.info }}</span><span class="lbl">INFO</span></div>
          </div>
          <div v-if="toolData.logOutput" class="panel-section">
            <pre class="code-output">{{ toolData.logOutput }}</pre>
          </div>
        </div>

        <!-- TypeScript转JS -->
        <div v-else-if="currentTool.id === 'ts-to-js'" class="tool-panel">
          <div class="panel-section">
            <label>TypeScript代码</label>
            <textarea v-model="toolData.tsInput" rows="8" placeholder="粘贴TypeScript代码..."></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertTsToJs">转换</el-button>
          </div>
          <div v-if="toolData.tsOutput" class="panel-section">
            <div class="output-header">
              <label>JavaScript代码</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.tsOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.tsOutput }}</pre>
          </div>
        </div>

        <!-- XML格式化 -->
        <div v-else-if="currentTool.id === 'xml-formatter'" class="tool-panel">
          <div class="panel-section">
            <label>XML代码</label>
            <textarea v-model="toolData.xmlInput" rows="8" placeholder="<root><item>value</item></root>"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="formatXml">格式化</el-button>
            <el-button @click="minifyXml">压缩</el-button>
          </div>
          <div v-if="toolData.xmlOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.xmlOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.xmlOutput }}</pre>
          </div>
        </div>

        <!-- JS压缩工具 -->
        <div v-else-if="currentTool.id === 'js-minifier'" class="tool-panel">
          <div class="panel-section">
            <label>JavaScript代码</label>
            <textarea v-model="toolData.jsMinInput" rows="8" placeholder="粘贴JS代码..."></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="minifyJs">压缩</el-button>
          </div>
          <div v-if="toolData.jsMinOutput" class="panel-section">
            <div class="stat-grid">
              <div class="stat-cell"><span class="num">{{ toolData.jsMinStats.original }}</span><span class="lbl">原始大小</span></div>
              <div class="stat-cell"><span class="num">{{ toolData.jsMinStats.minified }}</span><span class="lbl">压缩后</span></div>
              <div class="stat-cell"><span class="num">{{ toolData.jsMinStats.ratio }}%</span><span class="lbl">压缩率</span></div>
            </div>
            <div class="output-header">
              <label>压缩结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.jsMinOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.jsMinOutput }}</pre>
          </div>
        </div>

        <!-- CSS压缩工具 -->
        <div v-else-if="currentTool.id === 'css-minifier'" class="tool-panel">
          <div class="panel-section">
            <label>CSS代码</label>
            <textarea v-model="toolData.cssMinInput" rows="8" placeholder="粘贴CSS代码..."></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="minifyCss">压缩</el-button>
          </div>
          <div v-if="toolData.cssMinOutput" class="panel-section">
            <div class="stat-grid">
              <div class="stat-cell"><span class="num">{{ toolData.cssMinStats.original }}</span><span class="lbl">原始大小</span></div>
              <div class="stat-cell"><span class="num">{{ toolData.cssMinStats.minified }}</span><span class="lbl">压缩后</span></div>
              <div class="stat-cell"><span class="num">{{ toolData.cssMinStats.ratio }}%</span><span class="lbl">压缩率</span></div>
            </div>
            <div class="output-header">
              <label>压缩结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.cssMinOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.cssMinOutput }}</pre>
          </div>
        </div>

        <!-- Babel转换 -->
        <div v-else-if="currentTool.id === 'babel-converter'" class="tool-panel">
          <div class="panel-section">
            <label>ES6+ 代码</label>
            <textarea v-model="toolData.babelInput" rows="8" placeholder="const fn = () => { console.log('hello'); };"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertBabel">转换为ES5</el-button>
          </div>
          <div v-if="toolData.babelOutput" class="panel-section">
            <div class="output-header">
              <label>ES5 代码</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.babelOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.babelOutput }}</pre>
          </div>
        </div>

        <!-- TXT转Markdown -->
        <div v-else-if="currentTool.id === 'txt-to-md'" class="tool-panel">
          <div class="panel-section">
            <label>纯文本内容</label>
            <textarea v-model="toolData.txtMdInput" rows="8" placeholder="粘贴纯文本..."></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertTxtToMd">转换</el-button>
          </div>
          <div v-if="toolData.txtMdOutput" class="panel-section">
            <div class="output-header">
              <label>Markdown</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.txtMdOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.txtMdOutput }}</pre>
          </div>
        </div>

        <!-- HTML转文本 -->
        <div v-else-if="currentTool.id === 'html-to-text'" class="tool-panel">
          <div class="panel-section">
            <label>HTML代码</label>
            <textarea v-model="toolData.htmlTextInput" rows="8" placeholder="<div>Hello <b>World</b></div>"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertHtmlToText">提取文本</el-button>
          </div>
          <div v-if="toolData.htmlTextOutput" class="panel-section">
            <div class="output-header">
              <label>纯文本</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.htmlTextOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.htmlTextOutput }}</pre>
          </div>
        </div>

        <!-- SVG转图片 -->
        <div v-else-if="currentTool.id === 'svg-converter'" class="tool-panel">
          <div class="panel-section">
            <label>SVG代码</label>
            <textarea v-model="toolData.svgInput" rows="6" placeholder='<svg width="100" height="100"><circle cx="50" cy="50" r="40" fill="red"/></svg>'></textarea>
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>输出格式</label>
              <el-select v-model="toolData.svgFormat" style="width:100%">
                <el-option label="PNG" value="png" />
                <el-option label="JPEG" value="jpeg" />
              </el-select>
            </div>
            <div class="panel-section">
              <label>缩放倍数</label>
              <el-input-number v-model="toolData.svgScale" :min="1" :max="5" style="width:100%" />
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertSvgToImage">转换</el-button>
            <el-button v-if="toolData.svgResult" @click="downloadSvgImage">下载</el-button>
          </div>
          <div v-if="toolData.svgResult" class="img-preview"><img :src="toolData.svgResult" /></div>
        </div>

        <!-- 图片尺寸调整 -->
        <div v-else-if="currentTool.id === 'image-resize'" class="tool-panel">
          <div class="panel-section">
            <label>选择图片</label>
            <input type="file" accept="image/*" @change="onResizeImgChange" />
          </div>
          <div v-if="toolData.resizeSrc" class="img-preview"><img :src="toolData.resizeSrc" /></div>
          <div class="panel-row">
            <div class="panel-section">
              <label>宽度(px)</label>
              <el-input-number v-model="toolData.resizeWidth" :min="1" :max="5000" style="width:100%" />
            </div>
            <div class="panel-section">
              <label>高度(px)</label>
              <el-input-number v-model="toolData.resizeHeight" :min="1" :max="5000" style="width:100%" />
            </div>
          </div>
          <div class="panel-section">
            <el-checkbox v-model="toolData.resizeKeepRatio">保持比例</el-checkbox>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="resizeImage">调整尺寸</el-button>
            <el-button v-if="toolData.resizeResult" @click="downloadResizedImg">下载</el-button>
          </div>
          <div v-if="toolData.resizeResult" class="img-preview"><img :src="toolData.resizeResult" /></div>
        </div>

        <!-- PDF合并 -->
        <div v-else-if="currentTool.id === 'pdf-merge'" class="tool-panel">
          <div class="panel-section">
            <label>选择PDF文件（多选）</label>
            <input type="file" accept=".pdf" multiple @change="onPdfMergeChange" />
          </div>
          <div v-if="toolData.pdfMergeFiles.length" class="panel-section">
            <label>文件列表（可拖拽排序，此处按选择顺序合并）</label>
            <div class="file-list">
              <div v-for="(f, i) in toolData.pdfMergeFiles" :key="i" class="file-item">
                <span>{{ i + 1 }}. {{ f.name }}</span>
                <el-button text type="danger" size="small" @click="removePdfMerge(i)">移除</el-button>
              </div>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" :loading="toolData.pdfMergeLoading" @click="mergePdfFiles">合并PDF</el-button>
          </div>
        </div>

        <!-- 单位换算器 -->
        <div v-else-if="currentTool.id === 'unit-converter'" class="tool-panel">
          <div class="panel-section">
            <label>换算类型</label>
            <el-select v-model="toolData.unitType" style="width:100%" @change="resetUnitValues">
              <el-option label="长度" value="length" />
              <el-option label="重量" value="weight" />
              <el-option label="温度" value="temperature" />
              <el-option label="面积" value="area" />
              <el-option label="体积" value="volume" />
            </el-select>
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>数值</label>
              <el-input-number v-model="toolData.unitValue" :min="0" style="width:100%" />
            </div>
            <div class="panel-section">
              <label>源单位</label>
              <el-select v-model="toolData.unitFrom" style="width:100%">
                <el-option v-for="u in unitOptions" :key="u.value" :label="u.label" :value="u.value" />
              </el-select>
            </div>
            <div class="panel-section">
              <label>目标单位</label>
              <el-select v-model="toolData.unitTo" style="width:100%">
                <el-option v-for="u in unitOptions" :key="u.value" :label="u.label" :value="u.value" />
              </el-select>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertUnit">换算</el-button>
          </div>
          <div v-if="toolData.unitResult !== null" class="result-box">
            {{ toolData.unitValue }} {{ toolData.unitFrom }} = {{ toolData.unitResult }} {{ toolData.unitTo }}
          </div>
        </div>

        <!-- 转义字符转换 -->
        <div v-else-if="currentTool.id === 'escape-converter'" class="tool-panel">
          <div class="seg-tabs">
            <button :class="{ active: toolData.escapeMode === 'encode' }" @click="toolData.escapeMode = 'encode'">转义</button>
            <button :class="{ active: toolData.escapeMode === 'decode' }" @click="toolData.escapeMode = 'decode'">反转义</button>
          </div>
          <div class="panel-section">
            <label>转义类型</label>
            <el-select v-model="toolData.escapeType" style="width:100%">
              <el-option label="JSON转义" value="json" />
              <el-option label="正则转义" value="regex" />
              <el-option label="Shell转义" value="shell" />
            </el-select>
          </div>
          <div class="panel-section">
            <label>输入</label>
            <textarea v-model="toolData.escapeInput" rows="6" placeholder="输入要转义/反转义的内容"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="convertEscape">转换</el-button>
          </div>
          <div v-if="toolData.escapeOutput" class="panel-section">
            <div class="output-header">
              <label>结果</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.escapeOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.escapeOutput }}</pre>
          </div>
        </div>

        <!-- 端口扫描 -->
        <div v-else-if="currentTool.id === 'port-scanner'" class="tool-panel">
          <div class="panel-section">
            <label>目标主机</label>
            <input v-model="toolData.portHost" placeholder="127.0.0.1 或 example.com" />
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>起始端口</label>
              <el-input-number v-model="toolData.portStart" :min="1" :max="65535" style="width:100%" />
            </div>
            <div class="panel-section">
              <label>结束端口</label>
              <el-input-number v-model="toolData.portEnd" :min="1" :max="65535" style="width:100%" />
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" :loading="toolData.portScanning" @click="scanPorts">开始扫描</el-button>
          </div>
          <div v-if="toolData.portResult" class="panel-section">
            <pre class="code-output">{{ toolData.portResult }}</pre>
          </div>
          <div class="panel-section tip-box">
            提示：浏览器端无法进行真实TCP端口扫描，此工具演示常用端口列表和状态说明。
          </div>
        </div>

        <!-- 网络延迟测试 -->
        <div v-else-if="currentTool.id === 'ping-tester'" class="tool-panel">
          <div class="panel-section">
            <label>目标地址</label>
            <input v-model="toolData.pingHost" placeholder="https://example.com" />
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>测试次数</label>
              <el-input-number v-model="toolData.pingCount" :min="1" :max="20" style="width:100%" />
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" :loading="toolData.pingLoading" @click="runPingTest">开始测试</el-button>
          </div>
          <div v-if="toolData.pingResult" class="panel-section">
            <div class="stat-grid">
              <div class="stat-cell"><span class="num">{{ toolData.pingResult.avg }}ms</span><span class="lbl">平均延迟</span></div>
              <div class="stat-cell"><span class="num">{{ toolData.pingResult.min }}ms</span><span class="lbl">最低延迟</span></div>
              <div class="stat-cell"><span class="num">{{ toolData.pingResult.max }}ms</span><span class="lbl">最高延迟</span></div>
              <div class="stat-cell"><span class="num">{{ toolData.pingResult.jitter }}ms</span><span class="lbl">抖动</span></div>
            </div>
          </div>
        </div>

        <!-- 域名WHOIS -->
        <div v-else-if="currentTool.id === 'whois-lookup'" class="tool-panel">
          <div class="panel-section">
            <label>域名</label>
            <input v-model="toolData.whoisDomain" placeholder="example.com" />
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="lookupWhois">查询</el-button>
          </div>
          <div v-if="toolData.whoisResult" class="panel-section">
            <pre class="code-output">{{ toolData.whoisResult }}</pre>
          </div>
        </div>

        <!-- HTTP头分析 -->
        <div v-else-if="currentTool.id === 'http-header'" class="tool-panel">
          <div class="panel-section">
            <label>HTTP请求头/响应头</label>
            <textarea v-model="toolData.headerInput" rows="8" placeholder="Content-Type: application/json&#10;Authorization: Bearer xxx&#10;Cache-Control: no-cache"></textarea>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="analyzeHeaders">解析</el-button>
          </div>
          <div v-if="toolData.headerResult" class="panel-section">
            <pre class="code-output">{{ toolData.headerResult }}</pre>
          </div>
        </div>

        <!-- CDN检测 -->
        <div v-else-if="currentTool.id === 'cdn-checker'" class="tool-panel">
          <div class="panel-section">
            <label>网站URL</label>
            <input v-model="toolData.cdnUrl" placeholder="https://example.com" />
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="checkCdn">检测</el-button>
          </div>
          <div v-if="toolData.cdnResult" class="result-box" :class="toolData.cdnHas ? 'success' : 'info'">
            {{ toolData.cdnResult }}
          </div>
        </div>

        <!-- SSL证书检测 -->
        <div v-else-if="currentTool.id === 'ssl-checker'" class="tool-panel">
          <div class="panel-section">
            <label>域名</label>
            <input v-model="toolData.sslDomain" placeholder="example.com" />
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="checkSsl">检测</el-button>
          </div>
          <div v-if="toolData.sslResult" class="panel-section">
            <pre class="code-output">{{ toolData.sslResult }}</pre>
          </div>
          <div class="panel-section tip-box">
            提示：浏览器端无法直接获取SSL证书详细信息，此工具提供证书相关知识说明。
          </div>
        </div>

        <!-- WebSocket测试 -->
        <div v-else-if="currentTool.id === 'websocket-tester'" class="tool-panel">
          <div class="panel-section">
            <label>WebSocket URL</label>
            <input v-model="toolData.wsUrl" placeholder="wss://echo.websocket.org" />
          </div>
          <div class="panel-actions">
            <el-button type="primary" v-if="!toolData.wsConnected" @click="wsConnect">连接</el-button>
            <el-button type="danger" v-else @click="wsDisconnect">断开</el-button>
          </div>
          <div v-if="toolData.wsConnected" class="panel-section">
            <label>发送内容</label>
            <textarea v-model="toolData.wsSendMsg" rows="3"></textarea>
            <div class="panel-actions">
              <el-button type="primary" @click="wsSend">发送</el-button>
              <el-button @click="wsClearLog">清空日志</el-button>
            </div>
          </div>
          <div v-if="toolData.wsLogs.length" class="panel-section">
            <label>通信日志</label>
            <div class="ws-log">
              <div v-for="(log, i) in toolData.wsLogs" :key="i" :class="['ws-log-item', log.type]">
                <span class="ws-log-time">{{ log.time }}</span>
                <span class="ws-log-label">{{ log.type === 'sent' ? '↑ 发送' : log.type === 'recv' ? '↓ 接收' : '系统' }}</span>
                <span class="ws-log-content">{{ log.content }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- AES加密解密 -->
        <div v-else-if="currentTool.id === 'aes-encrypt'" class="tool-panel">
          <div class="seg-tabs">
            <button :class="{ active: toolData.aesMode === 'encrypt' }" @click="toolData.aesMode = 'encrypt'">加密</button>
            <button :class="{ active: toolData.aesMode === 'decrypt' }" @click="toolData.aesMode = 'decrypt'">解密</button>
          </div>
          <div class="panel-section">
            <label>{{ toolData.aesMode === 'encrypt' ? '明文' : '密文(Base64)' }}</label>
            <textarea v-model="toolData.aesInput" rows="4" :placeholder="toolData.aesMode === 'encrypt' ? '输入要加密的文本' : '输入要解密的Base64密文'"></textarea>
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>密钥</label>
              <input v-model="toolData.aesKey" placeholder="16/24/32位密钥" />
            </div>
            <div class="panel-section">
              <label>偏移量(IV)</label>
              <input v-model="toolData.aesIv" placeholder="16位IV（可选）" />
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" @click="doAes">{{ toolData.aesMode === 'encrypt' ? '加密' : '解密' }}</el-button>
          </div>
          <div v-if="toolData.aesOutput" class="panel-section">
            <div class="output-header">
              <label>{{ toolData.aesMode === 'encrypt' ? '密文' : '明文' }}</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.aesOutput)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.aesOutput }}</pre>
          </div>
          <div class="panel-section tip-box">
            提示：使用Web Crypto API实现AES-CBC模式加密，数据仅在本地处理。
          </div>
        </div>

        <!-- RSA密钥生成 -->
        <div v-else-if="currentTool.id === 'rsa-tool'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>密钥长度</label>
              <el-select v-model="toolData.rsaKeySize" style="width:100%">
                <el-option label="1024位" :value="1024" />
                <el-option label="2048位" :value="2048" />
                <el-option label="4096位" :value="4096" />
              </el-select>
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" :loading="toolData.rsaLoading" @click="generateRsaKeys">生成密钥对</el-button>
          </div>
          <div v-if="toolData.rsaPublicKey" class="panel-section">
            <div class="output-header">
              <label>公钥 (Public Key)</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.rsaPublicKey)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.rsaPublicKey }}</pre>
          </div>
          <div v-if="toolData.rsaPrivateKey" class="panel-section">
            <div class="output-header">
              <label>私钥 (Private Key)</label>
              <el-button text type="primary" size="small" @click="copyToClipboard(toolData.rsaPrivateKey)">复制</el-button>
            </div>
            <pre class="code-output">{{ toolData.rsaPrivateKey }}</pre>
          </div>
        </div>

        <!-- 证书生成器 -->
        <div v-else-if="currentTool.id === 'cert-generator'" class="tool-panel">
          <div class="panel-row">
            <div class="panel-section">
              <label>国家(C)</label>
              <input v-model="toolData.certCountry" placeholder="CN" />
            </div>
            <div class="panel-section">
              <label>省份(ST)</label>
              <input v-model="toolData.certState" placeholder="Beijing" />
            </div>
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>城市(L)</label>
              <input v-model="toolData.certCity" placeholder="Beijing" />
            </div>
            <div class="panel-section">
              <label>组织(O)</label>
              <input v-model="toolData.certOrg" placeholder="Example Inc." />
            </div>
          </div>
          <div class="panel-row">
            <div class="panel-section">
              <label>通用名(CN)</label>
              <input v-model="toolData.certCN" placeholder="*.example.com" />
            </div>
            <div class="panel-section">
              <label>有效期(天)</label>
              <el-input-number v-model="toolData.certDays" :min="1" :max="3650" style="width:100%" />
            </div>
          </div>
          <div class="panel-actions">
            <el-button type="primary" :loading="toolData.certLoading" @click="generateCertificate">生成自签名证书</el-button>
          </div>
          <div v-if="toolData.certResult" class="panel-section">
            <pre class="code-output">{{ toolData.certResult }}</pre>
          </div>
        </div>

      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import {
  Search, Close, Clock, ArrowRight, ArrowLeft, Cpu, Refresh, Plus, Link, Timer,
  TrendCharts, ZoomIn, Download, View, Edit, Document, Key, PictureRounded,
  Sort, Calendar, Brush, DataAnalysis
} from '@element-plus/icons-vue';

const router = useRouter();
const goHome = () => router.push('/home');

// 分类数据
const categories = [
  { id: 'testing', name: '测试工具', icon: TrendCharts },
  { id: 'converter', name: '代码转换', icon: Refresh },
  { id: 'document', name: '文档转换', icon: Document },
  { id: 'utility', name: '常用工具', icon: Cpu },
  { id: 'network', name: '网络工具', icon: Link },
  { id: 'security', name: '安全工具', icon: Key }
];

// 工具数据
const tools = [
  // 测试工具 (15个)
  { id: 'unit-test-generator', name: '单元测试生成器', description: '根据代码自动生成单元测试模板', category: 'testing', icon: Edit, tone: 'blue', featured: true },
  { id: 'api-tester', name: 'API 测试工具', description: '快速测试 RESTful API 接口', category: 'testing', icon: Link, tone: 'green', featured: true },
  { id: 'mock-generator', name: 'Mock 数据生成', description: '生成模拟测试数据', category: 'testing', icon: Download, tone: 'purple', featured: true },
  { id: 'coverage-calculator', name: '覆盖率计算器', description: '计算代码测试覆盖率', category: 'testing', icon: TrendCharts, tone: 'orange' },
  { id: 'regex-tester', name: '正则测试器', description: '测试和验证正则表达式', category: 'testing', icon: View, tone: 'cyan', featured: true },
  { id: 'curl-converter', name: 'cURL 转代码', description: 'cURL 命令转 fetch 请求', category: 'testing', icon: Link, tone: 'slate' },
  { id: 'sign-calculator', name: '接口签名计算', description: '生成 MD5/SHA256 签名参数', category: 'testing', icon: Key, tone: 'red', featured: true },
  { id: 'test-case-gen', name: '测试用例生成', description: '根据需求生成测试用例', category: 'testing', icon: Document, tone: 'yellow' },
  { id: 'report-generator', name: '测试报告生成', description: '生成格式化测试报告', category: 'testing', icon: Download, tone: 'cyan' },
  { id: 'perf-tester', name: '性能测试工具', description: '接口响应时间测试', category: 'testing', icon: Timer, tone: 'green' },
  { id: 'schema-validator', name: 'JSON Schema验证', description: '验证JSON数据结构', category: 'testing', icon: DataAnalysis, tone: 'purple' },
  { id: 'api-mocker', name: 'API Mock工具', description: '模拟API响应数据', category: 'testing', icon: Download, tone: 'blue' },
  { id: 'load-tester', name: '压力测试工具', description: '模拟高并发请求', category: 'testing', icon: Timer, tone: 'orange' },
  { id: 'socket-tester', name: 'Socket测试工具', description: 'WebSocket连接测试', category: 'testing', icon: Link, tone: 'purple' },
  { id: 'log-analyzer', name: '日志分析工具', description: '解析和过滤日志', category: 'testing', icon: Document, tone: 'slate' },
  // 代码转换工具 (20个)
  { id: 'json-formatter', name: 'JSON 格式化', description: 'JSON 格式化、压缩与校验', category: 'converter', icon: Document, tone: 'blue', featured: true },
  { id: 'json-xml-converter', name: 'JSON/XML 转换', description: 'JSON 与 XML 格式互转', category: 'converter', icon: Refresh, tone: 'cyan' },
  { id: 'code-formatter', name: '代码格式化器', description: '格式化与压缩多种代码', category: 'converter', icon: Edit, tone: 'slate' },
  { id: 'base64-encoder', name: 'Base64 编解码', description: 'Base64 编码和解码', category: 'converter', icon: Refresh, tone: 'yellow', featured: true },
  { id: 'url-encoder', name: 'URL 编解码', description: 'URL 编码和解码', category: 'converter', icon: Link, tone: 'green' },
  { id: 'number-base', name: '进制转换器', description: '二/八/十/十六进制互转', category: 'converter', icon: Sort, tone: 'purple' },
  { id: 'case-converter', name: '大小写转换', description: '驼峰/下划线等命名转换', category: 'converter', icon: Brush, tone: 'orange', featured: true },
  { id: 'color-converter', name: '颜色转换器', description: 'HEX / RGB / HSL 颜色互转', category: 'converter', icon: Brush, tone: 'red' },
  { id: 'html-entity', name: 'HTML 实体编解码', description: 'HTML 特殊字符转义还原', category: 'converter', icon: Document, tone: 'cyan' },
  { id: 'unicode-converter', name: 'Unicode 编解码', description: '中文与 Unicode 互转', category: 'converter', icon: Refresh, tone: 'purple' },
  { id: 'jwt-decoder', name: 'JWT 解析器', description: '解析 JWT Token 内容', category: 'converter', icon: Key, tone: 'orange', featured: true },
  { id: 'css-vars-converter', name: 'CSS变量转SCSS', description: 'CSS变量与SCSS变量互转', category: 'converter', icon: Brush, tone: 'green' },
  { id: 'comment-generator', name: '代码注释生成', description: '自动生成函数注释', category: 'converter', icon: Edit, tone: 'blue' },
  { id: 'ts-to-js', name: 'TypeScript转JS', description: '移除类型注解转换为JS', category: 'converter', icon: Edit, tone: 'slate' },
  { id: 'sql-formatter', name: 'SQL格式化', description: 'SQL语句格式化与美化', category: 'converter', icon: Document, tone: 'purple' },
  { id: 'yaml-json', name: 'YAML/JSON互转', description: 'YAML与JSON格式互转', category: 'converter', icon: Refresh, tone: 'cyan' },
  { id: 'xml-formatter', name: 'XML格式化', description: 'XML格式化与美化', category: 'converter', icon: Document, tone: 'green' },
  { id: 'js-minifier', name: 'JS压缩工具', description: 'JavaScript代码压缩', category: 'converter', icon: Edit, tone: 'red' },
  { id: 'css-minifier', name: 'CSS压缩工具', description: 'CSS代码压缩', category: 'converter', icon: Brush, tone: 'yellow' },
  { id: 'babel-converter', name: 'Babel转换', description: 'ES6+转ES5', category: 'converter', icon: Refresh, tone: 'slate' },
  // 文档转换工具 (15个)
  { id: 'image-format', name: '图片格式转换', description: 'PNG/JPG/WebP 格式互转', category: 'document', icon: PictureRounded, tone: 'blue', featured: true },
  { id: 'image-to-pdf', name: '图片转 PDF', description: '多张图片合并为 PDF', category: 'document', icon: Document, tone: 'red' },
  { id: 'pdf-to-image', name: 'PDF 转图片', description: 'PDF 各页导出为图片', category: 'document', icon: PictureRounded, tone: 'orange' },
  { id: 'image-to-base64', name: '图片转 Base64', description: '图片转 Base64 / DataURL', category: 'document', icon: PictureRounded, tone: 'green' },
  { id: 'image-compress', name: '图片压缩', description: '压缩图片体积并预览', category: 'document', icon: PictureRounded, tone: 'purple' },
  { id: 'excel-to-json', name: 'Excel 转 JSON', description: 'xlsx/csv 表格转 JSON', category: 'document', icon: Document, tone: 'green', featured: true },
  { id: 'json-to-excel', name: 'JSON 转 Excel', description: 'JSON 数组导出为 xlsx', category: 'document', icon: Document, tone: 'blue', featured: true },
  { id: 'csv-json', name: 'CSV / JSON 互转', description: 'CSV 与 JSON 双向转换', category: 'document', icon: Refresh, tone: 'cyan' },
  { id: 'markdown-html', name: 'Markdown 转 HTML', description: 'Markdown 渲染为 HTML', category: 'document', icon: Document, tone: 'slate' },
  { id: 'image-watermark', name: '图片加水印', description: '为图片添加文字水印', category: 'document', icon: PictureRounded, tone: 'yellow' },
  { id: 'txt-to-md', name: 'TXT转Markdown', description: '纯文本转Markdown格式', category: 'document', icon: Document, tone: 'purple' },
  { id: 'html-to-text', name: 'HTML转文本', description: '提取HTML中的纯文本', category: 'document', icon: Document, tone: 'cyan' },
  { id: 'svg-converter', name: 'SVG转图片', description: 'SVG矢量图转PNG/JPG', category: 'document', icon: PictureRounded, tone: 'green' },
  { id: 'image-resize', name: '图片尺寸调整', description: '调整图片宽高尺寸', category: 'document', icon: PictureRounded, tone: 'orange' },
  { id: 'pdf-merge', name: 'PDF合并', description: '多个PDF文件合并', category: 'document', icon: Document, tone: 'red' },
  // 常用工具 (20个)
  { id: 'timestamp-converter', name: '时间戳转换', description: '时间戳与日期格式互转', category: 'utility', icon: Timer, tone: 'purple', featured: true },
  { id: 'uuid-generator', name: 'UUID 生成器', description: '批量生成 UUID 标识', category: 'utility', icon: Plus, tone: 'green', featured: true },
  { id: 'hash-calculator', name: '哈希计算器', description: '计算 SHA 系列哈希值', category: 'utility', icon: ZoomIn, tone: 'orange', featured: true },
  { id: 'password-generator', name: '密码生成器', description: '生成高强度随机密码', category: 'utility', icon: Key, tone: 'red', featured: true },
  { id: 'text-counter', name: '字数统计', description: '统计字符、单词、行数', category: 'utility', icon: DataAnalysis, tone: 'cyan' },
  { id: 'qrcode-generator', name: '二维码生成', description: '文本/链接生成二维码', category: 'utility', icon: PictureRounded, tone: 'blue' },
  { id: 'cron-parser', name: 'Cron 解析器', description: '解析 Cron 定时表达式', category: 'utility', icon: Calendar, tone: 'slate' },
  { id: 'text-dedupe', name: '文本去重排序', description: '按行去重、排序、统计', category: 'utility', icon: Sort, tone: 'green' },
  { id: 'text-diff', name: '文本对比', description: '逐行比较两段文本差异', category: 'utility', icon: View, tone: 'purple' },
  { id: 'lorem-ipsum', name: '随机文本生成', description: '生成中英文占位文本', category: 'utility', icon: Edit, tone: 'yellow' },
  { id: 'ip-checker', name: 'IP地址查询', description: '查询IP地理位置信息', category: 'utility', icon: Link, tone: 'cyan' },
  { id: 'id-card-validator', name: '身份证验证', description: '验证身份证号码有效性', category: 'utility', icon: Key, tone: 'orange' },
  { id: 'date-calculator', name: '日期计算器', description: '计算日期差值和天数', category: 'utility', icon: Calendar, tone: 'blue' },
  { id: 'color-picker', name: '颜色选择器', description: '可视化选择颜色值', category: 'utility', icon: Brush, tone: 'red' },
  { id: 'file-size-calc', name: '文件大小换算', description: 'B/KB/MB/GB 单位换算', category: 'utility', icon: DataAnalysis, tone: 'purple' },
  { id: 'number-formatter', name: '数字格式化', description: '千分位、货币格式转换', category: 'utility', icon: Sort, tone: 'green' },
  { id: 'unit-converter', name: '单位换算器', description: '长度/重量/温度等换算', category: 'utility', icon: Refresh, tone: 'slate' },
  { id: 'emoji-picker', name: 'Emoji选择器', description: '选择并复制Emoji表情', category: 'utility', icon: PictureRounded, tone: 'yellow' },
  { id: 'string-replace', name: '批量替换', description: '文本批量替换工具', category: 'utility', icon: Edit, tone: 'cyan' },
  { id: 'escape-converter', name: '转义字符转换', description: '各种转义字符互转', category: 'utility', icon: Refresh, tone: 'purple' },
  // 网络工具
  { id: 'port-scanner', name: '端口扫描', description: '扫描目标主机开放端口', category: 'network', icon: Link, tone: 'cyan' },
  { id: 'dns-lookup', name: 'DNS查询', description: '域名解析IP地址', category: 'network', icon: Refresh, tone: 'green' },
  { id: 'ping-tester', name: '网络延迟测试', description: '测试网络连接延迟', category: 'network', icon: Timer, tone: 'orange' },
  { id: 'whois-lookup', name: '域名WHOIS', description: '查询域名注册信息', category: 'network', icon: Document, tone: 'purple' },
  { id: 'http-header', name: 'HTTP头分析', description: '解析HTTP请求头', category: 'network', icon: View, tone: 'blue' },
  { id: 'cdn-checker', name: 'CDN检测', description: '检测网站是否使用CDN', category: 'network', icon: ZoomIn, tone: 'red' },
  { id: 'ssl-checker', name: 'SSL证书检测', description: '检查SSL证书信息', category: 'network', icon: Key, tone: 'yellow' },
  { id: 'websocket-tester', name: 'WebSocket测试', description: '测试WebSocket连接', category: 'network', icon: Link, tone: 'slate' },
  // 安全工具
  { id: 'pwd-strength', name: '密码强度检测', description: '评估密码安全强度', category: 'security', icon: Key, tone: 'red' },
  { id: 'data-masking', name: '数据脱敏', description: '敏感数据脱敏处理', category: 'security', icon: Edit, tone: 'purple' },
  { id: 'aes-encrypt', name: 'AES加密解密', description: 'AES对称加密解密', category: 'security', icon: ZoomIn, tone: 'green' },
  { id: 'rsa-tool', name: 'RSA密钥生成', description: '生成RSA公钥私钥', category: 'security', icon: Key, tone: 'blue' },
  { id: 'cert-generator', name: '证书生成器', description: '生成自签名证书', category: 'security', icon: Document, tone: 'orange' },
  { id: 'xss-tester', name: 'XSS检测', description: '检测XSS攻击风险', category: 'security', icon: View, tone: 'cyan' },
  { id: 'sql-inject-check', name: 'SQL注入检测', description: '检测SQL注入风险', category: 'security', icon: DataAnalysis, tone: 'yellow' },
  { id: 'csrf-token', name: 'CSRF Token生成', description: '生成CSRF防护Token', category: 'security', icon: Plus, tone: 'slate' },
];

// 状态
const activeCategory = ref('testing');
const searchQuery = ref('');
const showToolModal = ref(false);
const currentTool = ref(null);
const recentTools = ref([]);
const convertDirection = ref('json2xml');
const encodeMode = ref('encode');
const urlEncodeMode = ref('encode');
const currentTimestamp = ref(Math.floor(Date.now() / 1000));

const convertPlaceholder = computed(() =>
  convertDirection.value === 'json2xml' ? '{"key": "value"}' : '<root><item>value</item></root>'
);

// 工具数据
const toolData = ref({
  unitTestInput: '', unitTestLang: 'javascript', unitTestFramework: 'jest', unitTestOutput: '',
  apiMethod: 'GET', apiUrl: '', apiHeaders: '{"Content-Type": "application/json"}', apiBody: '', apiResponse: '', apiLoading: false, apiStatus: '', apiStatusOk: false,
  mockType: 'user', mockCount: 5, mockTemplate: '', mockOutput: '',
  convertInput: '', convertOutput: '',
  formatLang: 'json', formatIndent: '2', formatInput: '', formatOutput: '',
  base64Input: '', base64Output: '',
  urlInput: '', urlOutput: '',
  jsonInput: '', jsonOutput: '', jsonError: '',
  timestampInput: '', timestampOutput: '', dateInput: '', dateOutput: '',
  uuidVersion: 'v4', uuidCount: 1, uuidCase: 'lower', uuidOutput: [],
  hashInput: '', hashAlgorithms: { sha1: false, sha256: true, sha384: false, sha512: false }, hashOutput: null, hashLoading: false,
  regexPattern: '', regexFlags: 'g', regexTestText: '', regexResult: false, regexMatchCount: 0, regexMatches: [],
  caseInput: '', caseOutput: '',
  colorInput: '#2563eb', colorRgb: '', colorHsl: '', colorValid: true,
  counterInput: '', counterStats: { chars: 0, charsNoSpace: 0, words: 0, lines: 0, chinese: 0 },
  pwdLength: 16, pwdUpper: true, pwdLower: true, pwdNumber: true, pwdSymbol: false, pwdOutput: '',
  qrInput: '', qrUrl: '',
  baseInput: '', baseFrom: 10, baseResult: null,
  cronInput: '', cronOutput: '', cronError: '',
  coverageLines: 100, coverageCovered: 80, coverageResult: null,
  // cURL 转代码
  curlInput: '', curlOutput: '',
  // HTML 实体
  htmlEntityInput: '', htmlEntityOutput: '', htmlEntityMode: 'encode',
  // Unicode
  unicodeInput: '', unicodeOutput: '', unicodeMode: 'encode',
  // JWT
  jwtInput: '', jwtHeader: '', jwtPayload: '', jwtError: '',
  // 图片格式转换
  imgFmtSrc: '', imgFmtName: '', imgFmtTarget: 'image/png', imgFmtQuality: 0.92, imgFmtResult: '', imgFmtLoading: false,
  // 图片转 PDF
  img2pdfFiles: [], img2pdfLoading: false,
  // PDF 转图片
  pdf2imgPages: [], pdf2imgLoading: false, pdf2imgName: '',
  // 图片转 Base64
  img2b64Result: '', img2b64Name: '',
  // 图片压缩
  imgCompSrc: '', imgCompResult: '', imgCompRatio: 0.6, imgCompOrigSize: 0, imgCompNewSize: 0, imgCompLoading: false,
  // Excel 转 JSON
  excel2jsonOutput: '', excel2jsonName: '', excel2jsonLoading: false,
  // JSON 转 Excel
  json2excelInput: '', json2excelLoading: false,
  // CSV/JSON
  csvJsonInput: '', csvJsonOutput: '', csvJsonMode: 'csv2json',
  // Markdown
  mdInput: '', mdOutput: '',
  // 文本去重
  dedupeInput: '', dedupeOutput: '', dedupeSort: 'none', dedupeTrim: true, dedupeRemoveEmpty: true,
  // 文本对比
  diffLeft: '', diffRight: '', diffResult: [],
  // 随机文本
  loremType: 'cn', loremCount: 3, loremOutput: '',
  // 接口签名计算
  signParams: '', signSecret: '', signAlgo: 'md5', signOutput: '',
  // 测试用例生成
  testCaseInput: '', testCaseOutput: '',
  // JSON Schema验证
  schemaInput: '', schemaJson: '', schemaValid: false, schemaError: '',
  // CSS变量转SCSS
  cssVarInput: '', cssVarOutput: '', cssVarMode: 'css2scss',
  // 代码注释生成
  commentInput: '', commentOutput: '',
  // SQL格式化
  sqlInput: '', sqlOutput: '',
  // YAML/JSON互转
  yamlInput: '', yamlOutput: '', yamlMode: 'yaml2json',
  // 图片加水印
  watermarkSrc: '', watermarkText: '水印', watermarkOpacity: 0.5, watermarkResult: '',
  // IP查询
  ipInput: '', ipResult: '',
  // 身份证验证
  idCardInput: '', idCardValid: false, idCardResult: '',
  // 日期计算
  dateStart: '', dateEnd: '', dateDiffResult: '',
  // 颜色选择器
  colorPickerValue: '#2563eb', colorPickerRgb: '',
  // 文件大小换算
  fileSizeValue: 1024, fileSizeUnit: 'kb', fileSizeResult: null,
  // 数字格式化
  numberInput: '', numberOutput: null,
  // 密码强度检测
  pwdStrengthInput: '', pwdStrengthResult: '', pwdStrengthClass: '', pwdStrengthPercent: 0,
  // 数据脱敏
  maskInput: '', maskOutput: '',
  // DNS查询
  dnsDomain: '', dnsResult: '',
  // 批量替换
  replaceFind: '', replaceReplace: '', replaceInput: '', replaceOutput: '',
  // XSS检测
  xssInput: '', xssResult: '', xssSafe: false,
  // SQL注入检测
  sqlInjectInput: '', sqlInjectResult: '', sqlInjectSafe: false,
  // CSRF Token
  csrfLength: 32, csrfOutput: '',
  // 测试报告生成
  reportProject: '', reportTotal: 100, reportPass: 85, reportFail: 10, reportOutput: '',
  // 性能测试
  perfUrl: '', perfCount: 5, perfMethod: 'GET', perfLoading: false, perfResult: null,
  // API Mock
  mockApiPath: '/api/test', mockStatus: 200, mockDelay: 0, mockResponseBody: '{"code":200,"msg":"ok"}', mockApiOutput: '',
  // 压力测试
  loadUrl: '', loadConcurrency: 10, loadTotal: 100, loadLoading: false, loadResult: '',
  // Socket测试
  socketUrl: 'wss://echo.websocket.org', socketConnected: false, socketSendMsg: '', socketLogs: [],
  socketWs: null,
  // 日志分析
  logInput: '', logKeyword: '', logLevel: 'all', logStats: null, logOutput: '',
  // TS转JS
  tsInput: '', tsOutput: '',
  // XML格式化
  xmlInput: '', xmlOutput: '',
  // JS压缩
  jsMinInput: '', jsMinOutput: '', jsMinStats: { original: 0, minified: 0, ratio: 0 },
  // CSS压缩
  cssMinInput: '', cssMinOutput: '', cssMinStats: { original: 0, minified: 0, ratio: 0 },
  // Babel转换
  babelInput: '', babelOutput: '',
  // TXT转MD
  txtMdInput: '', txtMdOutput: '',
  // HTML转文本
  htmlTextInput: '', htmlTextOutput: '',
  // SVG转图片
  svgInput: '<svg width="100" height="100"><circle cx="50" cy="50" r="40" fill="red"/></svg>', svgFormat: 'png', svgScale: 2, svgResult: '',
  // 图片尺寸调整
  resizeSrc: '', resizeWidth: 800, resizeHeight: 600, resizeKeepRatio: true, resizeResult: '',
  resizeOrigWidth: 0, resizeOrigHeight: 0,
  // PDF合并
  pdfMergeFiles: [], pdfMergeLoading: false,
  // 单位换算
  unitType: 'length', unitValue: 1, unitFrom: 'm', unitTo: 'km', unitResult: null,
  // 转义字符转换
  escapeMode: 'encode', escapeType: 'json', escapeInput: '', escapeOutput: '',
  // 端口扫描
  portHost: '127.0.0.1', portStart: 1, portEnd: 1000, portScanning: false, portResult: '',
  // Ping测试
  pingHost: 'https://example.com', pingCount: 5, pingLoading: false, pingResult: null,
  // WHOIS
  whoisDomain: '', whoisResult: '',
  // HTTP头分析
  headerInput: '', headerResult: '',
  // CDN检测
  cdnUrl: '', cdnResult: '', cdnHas: false,
  // SSL证书检测
  sslDomain: '', sslResult: '',
  // WebSocket测试
  wsUrl: 'wss://echo.websocket.org', wsConnected: false, wsSendMsg: '', wsLogs: [], wsInstance: null,
  // AES加密
  aesMode: 'encrypt', aesInput: '', aesKey: '', aesIv: '', aesOutput: '',
  // RSA密钥生成
  rsaKeySize: 2048, rsaLoading: false, rsaPublicKey: '', rsaPrivateKey: '',
  // 证书生成
  certCountry: 'CN', certState: 'Beijing', certCity: 'Beijing', certOrg: 'Example Inc.',
  certCN: '*.example.com', certDays: 365, certLoading: false, certResult: ''
});

// 过滤后的工具列表
const filteredTools = computed(() => {
  let result;
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    result = tools.filter(t => t.name.toLowerCase().includes(query) || t.description.toLowerCase().includes(query));
  } else {
    result = tools.filter(t => t.category === activeCategory.value);
  }
  // 精选工具排在前面
  return result.sort((a, b) => {
    if (a.featured && !b.featured) return -1;
    if (!a.featured && b.featured) return 1;
    return 0;
  });
});

const countByCategory = (id) => tools.filter(t => t.category === id).length;

// 打开工具
const openTool = (tool) => {
  currentTool.value = tool;
  showToolModal.value = true;
  const index = recentTools.value.findIndex(t => t.id === tool.id);
  if (index > -1) recentTools.value.splice(index, 1);
  recentTools.value.unshift(tool);
  if (recentTools.value.length > 6) recentTools.value.pop();
  localStorage.setItem('recentTools', JSON.stringify(recentTools.value.map(t => t.id)));
  currentTimestamp.value = Math.floor(Date.now() / 1000);
};

const clearRecent = () => {
  recentTools.value = [];
  localStorage.removeItem('recentTools');
};

const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success('已复制到剪贴板');
  } catch {
    // 降级方案
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    ElMessage.success('已复制到剪贴板');
  }
};

// ============ 单元测试生成器 ============
const generateUnitTest = () => {
  const code = toolData.value.unitTestInput.trim();
  if (!code) { ElMessage.warning('请输入代码'); return; }
  const fnMatch = code.match(/(?:function\s+|const\s+|def\s+)?(\w+)\s*[=(]/);
  const fnName = fnMatch ? fnMatch[1] : 'targetFunction';
  const fw = toolData.value.unitTestFramework;
  let out = '';
  if (fw === 'jest' || fw === 'mocha') {
    const assertImport = fw === 'mocha' ? "const { expect } = require('chai');\n" : '';
    out = `${assertImport}describe('${fnName}', () => {\n  it('应返回预期结果', () => {\n    const result = ${fnName}(/* 参数 */);\n    expect(result).toBe(/* 预期值 */);\n  });\n\n  it('应处理边界情况', () => {\n    expect(() => ${fnName}(null)).not.toThrow();\n  });\n});`;
  } else if (fw === 'pytest') {
    out = `import pytest\n\n\ndef test_${fnName}_normal():\n    result = ${fnName}(  # 参数\n    )\n    assert result == None  # 预期值\n\n\ndef test_${fnName}_edge():\n    with pytest.raises(Exception):\n        ${fnName}(None)`;
  } else {
    out = `import org.junit.jupiter.api.Test;\nimport static org.junit.jupiter.api.Assertions.*;\n\nclass ${fnName.charAt(0).toUpperCase() + fnName.slice(1)}Test {\n    @Test\n    void testNormal() {\n        var result = ${fnName}(/* 参数 */);\n        assertEquals(/* 预期值 */, result);\n    }\n}`;
  }
  toolData.value.unitTestOutput = out;
};

// ============ API测试 ============
const testApi = async () => {
  const url = toolData.value.apiUrl.trim();
  if (!url) { ElMessage.warning('请输入 API 地址'); return; }
  toolData.value.apiLoading = true;
  toolData.value.apiResponse = '';
  const start = Date.now();
  try {
    let headers = {};
    if (toolData.value.apiHeaders.trim()) headers = JSON.parse(toolData.value.apiHeaders);
    const options = { method: toolData.value.apiMethod, headers };
    if (['POST', 'PUT', 'PATCH'].includes(toolData.value.apiMethod) && toolData.value.apiBody.trim()) {
      options.body = toolData.value.apiBody;
    }
    const response = await fetch(url, options);
    const cost = Date.now() - start;
    toolData.value.apiStatus = `${response.status} ${response.statusText} · ${cost}ms`;
    toolData.value.apiStatusOk = response.ok;
    const text = await response.text();
    try {
      toolData.value.apiResponse = JSON.stringify(JSON.parse(text), null, 2);
    } catch {
      toolData.value.apiResponse = text;
    }
  } catch (error) {
    toolData.value.apiStatus = '请求失败';
    toolData.value.apiStatusOk = false;
    toolData.value.apiResponse = `请求失败: ${error.message}\n\n提示：可能受跨域(CORS)限制，请确认目标接口允许跨域访问。`;
  } finally {
    toolData.value.apiLoading = false;
  }
};

// ============ Mock数据生成 ============
const randPick = (arr) => arr[Math.floor(Math.random() * arr.length)];
const randInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
const randEmail = () => `user${Math.random().toString(36).slice(2, 9)}@example.com`;
const randPhone = () => `1${randPick(['3', '5', '7', '8', '9'])}${String(randInt(0, 999999999)).padStart(9, '0')}`;
const randDate = () => new Date(Date.now() - Math.random() * 365 * 864e5).toISOString();

const generateMock = () => {
  const builders = {
    user: () => ({ id: randInt(1, 9999), name: randPick(['张三', '李四', '王五', '赵六', '钱七']), age: randInt(18, 60), email: randEmail(), phone: randPhone(), createdAt: randDate() }),
    product: () => ({ id: randInt(1, 9999), name: randPick(['手机', '电脑', '平板', '耳机', '手表']), price: Number((Math.random() * 9999).toFixed(2)), stock: randInt(0, 1000), category: randPick(['电子', '配件', '家居']) }),
    order: () => ({ orderId: `ORD${Date.now()}${randInt(100, 999)}`, status: randPick(['待支付', '已支付', '已发货', '已完成', '已取消']), amount: Number((Math.random() * 10000).toFixed(2)), items: randInt(1, 5), createdAt: randDate() })
  };
  const results = [];
  for (let i = 0; i < toolData.value.mockCount; i++) {
    if (toolData.value.mockType === 'custom') {
      try {
        const template = JSON.parse(toolData.value.mockTemplate || '{}');
        const obj = {};
        for (const key in template) {
          const v = template[key];
          if (typeof v === 'string' && v.startsWith('@')) {
            const fn = v.slice(1);
            if (fn.startsWith('name')) obj[key] = randPick(['张三', '李四', '王五']);
            else if (fn.startsWith('integer')) {
              const m = fn.match(/\((\d+)\s*,\s*(\d+)\)/);
              obj[key] = randInt(m ? +m[1] : 0, m ? +m[2] : 100);
            } else if (fn.startsWith('email')) obj[key] = randEmail();
            else if (fn.startsWith('phone')) obj[key] = randPhone();
            else if (fn.startsWith('date')) obj[key] = randDate();
            else if (fn.startsWith('bool')) obj[key] = Math.random() > 0.5;
            else obj[key] = v;
          } else obj[key] = v;
        }
        results.push(obj);
      } catch {
        ElMessage.error('模板 JSON 格式错误');
        return;
      }
    } else {
      results.push(builders[toolData.value.mockType]());
    }
  }
  toolData.value.mockOutput = JSON.stringify(results, null, 2);
};

// ============ 覆盖率计算器 ============
const calculateCoverage = () => {
  const { coverageLines, coverageCovered } = toolData.value;
  if (!coverageLines || coverageLines < 1) { ElMessage.warning('请输入有效总行数'); return; }
  if (coverageCovered > coverageLines) { ElMessage.warning('覆盖行数不能超过总行数'); return; }
  toolData.value.coverageResult = (coverageCovered / coverageLines) * 100;
};
const getCoverageClass = (v) => v >= 80 ? 'high' : v >= 50 ? 'medium' : 'low';
const getCoverageStatus = (v) => v >= 80 ? '优秀' : v >= 50 ? '一般' : '偏低';

// ============ JSON/XML 转换 ============
const jsonToXml = (obj, indent = '') => {
  let xml = '';
  for (const key in obj) {
    const val = obj[key];
    if (Array.isArray(val)) {
      val.forEach(item => {
        if (typeof item === 'object' && item !== null) {
          xml += `${indent}<${key}>\n${jsonToXml(item, indent + '  ')}${indent}</${key}>\n`;
        } else {
          xml += `${indent}<${key}>${item}</${key}>\n`;
        }
      });
    } else if (typeof val === 'object' && val !== null) {
      xml += `${indent}<${key}>\n${jsonToXml(val, indent + '  ')}${indent}</${key}>\n`;
    } else {
      xml += `${indent}<${key}>${val}</${key}>\n`;
    }
  }
  return xml;
};
const xmlToJson = (xml) => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xml, 'application/xml');
  if (doc.querySelector('parsererror')) throw new Error('XML 格式错误');
  const parseNode = (node) => {
    const result = {};
    let hasChild = false;
    for (const child of node.childNodes) {
      if (child.nodeType === 1) {
        hasChild = true;
        const key = child.nodeName;
        const value = parseNode(child);
        if (result[key] !== undefined) {
          if (!Array.isArray(result[key])) result[key] = [result[key]];
          result[key].push(value);
        } else result[key] = value;
      }
    }
    if (!hasChild) return node.textContent.trim();
    return result;
  };
  return { [doc.documentElement.nodeName]: parseNode(doc.documentElement) };
};
const convertData = () => {
  if (!toolData.value.convertInput.trim()) { ElMessage.warning('请输入内容'); return; }
  try {
    if (convertDirection.value === 'json2xml') {
      toolData.value.convertOutput = jsonToXml(JSON.parse(toolData.value.convertInput));
    } else {
      toolData.value.convertOutput = JSON.stringify(xmlToJson(toolData.value.convertInput), null, 2);
    }
  } catch (e) {
    ElMessage.error(`转换失败: ${e.message}`);
  }
};

// ============ 代码格式化器 ============
const getIndent = () => toolData.value.formatIndent === 'tab' ? '\t' : ' '.repeat(+toolData.value.formatIndent);
const formatBrace = (code, indentUnit) => {
  let depth = 0, out = '';
  const len = code.length;
  for (let i = 0; i < len; i++) {
    const ch = code[i];
    if (ch === '}' || ch === ']') {
      depth = Math.max(0, depth - 1);
      out += '\n' + indentUnit.repeat(depth);
    }
    out += ch;
    if (ch === '{' || ch === '[') {
      depth++;
      out += '\n' + indentUnit.repeat(depth);
    } else if (ch === ';') {
      out += '\n' + indentUnit.repeat(depth);
    } else if (ch === ',') {
      out += '\n' + indentUnit.repeat(depth);
    }
  }
  return out.split('\n').map(l => l.replace(/\s+$/, '')).filter(l => l.trim()).join('\n');
};
const formatCode = () => {
  if (!toolData.value.formatInput.trim()) { ElMessage.warning('请输入代码'); return; }
  try {
    const indentUnit = getIndent();
    if (toolData.value.formatLang === 'json') {
      toolData.value.formatOutput = JSON.stringify(JSON.parse(toolData.value.formatInput), null, toolData.value.formatIndent === 'tab' ? '\t' : +toolData.value.formatIndent);
    } else {
      toolData.value.formatOutput = formatBrace(toolData.value.formatInput.replace(/\s+/g, ' '), indentUnit);
    }
  } catch (e) {
    ElMessage.error(`格式化失败: ${e.message}`);
  }
};
const minifyCode = () => {
  if (!toolData.value.formatInput.trim()) { ElMessage.warning('请输入代码'); return; }
  try {
    if (toolData.value.formatLang === 'json') {
      toolData.value.formatOutput = JSON.stringify(JSON.parse(toolData.value.formatInput));
    } else {
      toolData.value.formatOutput = toolData.value.formatInput.replace(/\s*\n\s*/g, '').replace(/\s{2,}/g, ' ').trim();
    }
  } catch (e) {
    ElMessage.error(`压缩失败: ${e.message}`);
  }
};

// ============ Base64 编解码（支持中文 UTF-8） ============
const handleBase64 = () => {
  if (!toolData.value.base64Input.trim()) { ElMessage.warning('请输入内容'); return; }
  try {
    if (encodeMode.value === 'encode') {
      toolData.value.base64Output = btoa(unescape(encodeURIComponent(toolData.value.base64Input)));
    } else {
      toolData.value.base64Output = decodeURIComponent(escape(atob(toolData.value.base64Input.trim())));
    }
  } catch {
    ElMessage.error(`${encodeMode.value === 'encode' ? '编码' : '解码'}失败，请检查输入`);
  }
};

// ============ URL 编解码 ============
const handleUrlEncode = () => {
  if (!toolData.value.urlInput.trim()) { ElMessage.warning('请输入内容'); return; }
  try {
    toolData.value.urlOutput = urlEncodeMode.value === 'encode'
      ? encodeURIComponent(toolData.value.urlInput)
      : decodeURIComponent(toolData.value.urlInput);
  } catch {
    ElMessage.error('操作失败，请检查输入');
  }
};

// ============ JSON 格式化/校验 ============
const formatJson = () => {
  toolData.value.jsonError = '';
  toolData.value.jsonOutput = '';
  if (!toolData.value.jsonInput.trim()) { ElMessage.warning('请输入 JSON'); return; }
  try {
    toolData.value.jsonOutput = JSON.stringify(JSON.parse(toolData.value.jsonInput), null, 2);
    ElMessage.success('JSON 格式正确');
  } catch (e) {
    toolData.value.jsonError = `JSON 解析错误: ${e.message}`;
  }
};
const compressJson = () => {
  toolData.value.jsonError = '';
  if (!toolData.value.jsonInput.trim()) { ElMessage.warning('请输入 JSON'); return; }
  try {
    toolData.value.jsonOutput = JSON.stringify(JSON.parse(toolData.value.jsonInput));
  } catch (e) {
    toolData.value.jsonError = `JSON 解析错误: ${e.message}`;
  }
};

// ============ 时间戳转换 ============
const pad = (n) => String(n).padStart(2, '0');
const fmtDate = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
const convertTimestamp = () => {
  const raw = toolData.value.timestampInput.trim();
  if (!raw) { ElMessage.warning('请输入时间戳'); return; }
  let ts = parseInt(raw);
  if (isNaN(ts)) { ElMessage.error('无效的时间戳'); return; }
  if (raw.length <= 10) ts *= 1000;
  toolData.value.timestampOutput = fmtDate(new Date(ts));
};
const dateToTimestamp = () => {
  const raw = toolData.value.dateInput.trim();
  if (!raw) { ElMessage.warning('请输入日期'); return; }
  const d = new Date(raw.replace(/-/g, '/'));
  if (isNaN(d.getTime())) { ElMessage.error('无效的日期格式'); return; }
  toolData.value.dateOutput = `秒：${Math.floor(d.getTime() / 1000)}　毫秒：${d.getTime()}`;
};

// ============ UUID 生成 ============
const uuidV4 = () => 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
  const r = Math.random() * 16 | 0;
  return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
});
const uuidV1 = () => {
  const now = Date.now();
  const rand = () => Math.floor(Math.random() * 256).toString(16).padStart(2, '0');
  const timeLow = (now & 0xffffffff).toString(16).padStart(8, '0');
  const timeMid = Math.floor(now / 0x100000000 & 0xffff).toString(16).padStart(4, '0');
  const node = Array.from({ length: 6 }, rand).join('');
  return `${timeLow}-${timeMid}-1${rand().slice(0, 3)}-${(0x8000 | Math.random() * 0x3fff).toString(16)}-${node}`;
};
const generateUuid = () => {
  const list = [];
  for (let i = 0; i < toolData.value.uuidCount; i++) {
    let u = toolData.value.uuidVersion === 'v1' ? uuidV1() : uuidV4();
    list.push(toolData.value.uuidCase === 'upper' ? u.toUpperCase() : u);
  }
  toolData.value.uuidOutput = list;
};

// ============ 哈希计算（Web Crypto，真实算法） ============
const digestHex = async (algo, text) => {
  const data = new TextEncoder().encode(text);
  const buf = await crypto.subtle.digest(algo, data);
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
};
const calculateHash = async () => {
  if (!toolData.value.hashInput) { ElMessage.warning('请输入文本'); return; }
  const algos = toolData.value.hashAlgorithms;
  if (!algos.sha1 && !algos.sha256 && !algos.sha384 && !algos.sha512) { ElMessage.warning('请至少选择一种算法'); return; }
  toolData.value.hashLoading = true;
  try {
    const text = toolData.value.hashInput;
    const result = {};
    if (algos.sha1) result['sha-1'] = await digestHex('SHA-1', text);
    if (algos.sha256) result['sha-256'] = await digestHex('SHA-256', text);
    if (algos.sha384) result['sha-384'] = await digestHex('SHA-384', text);
    if (algos.sha512) result['sha-512'] = await digestHex('SHA-512', text);
    toolData.value.hashOutput = result;
  } catch {
    ElMessage.error('计算失败');
  } finally {
    toolData.value.hashLoading = false;
  }
};

// ============ 正则测试 ============
const testRegex = () => {
  if (!toolData.value.regexPattern) { ElMessage.warning('请输入正则表达式'); return; }
  if (!toolData.value.regexTestText) { ElMessage.warning('请输入测试文本'); return; }
  try {
    let flags = toolData.value.regexFlags || '';
    if (!flags.includes('g')) flags += 'g';
    const re = new RegExp(toolData.value.regexPattern, flags);
    const matches = [...toolData.value.regexTestText.matchAll(re)].map(m => m[0]);
    toolData.value.regexMatches = matches;
    toolData.value.regexMatchCount = matches.length;
    toolData.value.regexResult = true;
    if (matches.length === 0) ElMessage.info('未找到匹配');
  } catch (e) {
    ElMessage.error(`正则表达式错误: ${e.message}`);
  }
};

// ============ 大小写/命名转换 ============
const convertCase = (mode) => {
  const text = toolData.value.caseInput.trim();
  if (!text) { ElMessage.warning('请输入文本'); return; }
  const words = text.split(/[\s_\-]+/).filter(Boolean);
  let out = '';
  switch (mode) {
    case 'upper': out = text.toUpperCase(); break;
    case 'lower': out = text.toLowerCase(); break;
    case 'capitalize': out = words.map(w => w[0].toUpperCase() + w.slice(1).toLowerCase()).join(' '); break;
    case 'camel': out = words.map((w, i) => i === 0 ? w.toLowerCase() : w[0].toUpperCase() + w.slice(1).toLowerCase()).join(''); break;
    case 'snake': out = words.map(w => w.toLowerCase()).join('_'); break;
    case 'kebab': out = words.map(w => w.toLowerCase()).join('-'); break;
  }
  toolData.value.caseOutput = out;
};

// ============ 字数统计 ============
const countText = () => {
  const text = toolData.value.counterInput;
  toolData.value.counterStats = {
    chars: text.length,
    charsNoSpace: text.replace(/\s/g, '').length,
    words: (text.trim().match(/[a-zA-Z0-9]+/g) || []).length + (text.match(/[\u4e00-\u9fa5]/g) || []).length,
    lines: text ? text.split('\n').length : 0,
    chinese: (text.match(/[\u4e00-\u9fa5]/g) || []).length
  };
};

// ============ 密码生成 ============
const generatePassword = () => {
  let chars = '';
  if (toolData.value.pwdUpper) chars += 'ABCDEFGHJKLMNPQRSTUVWXYZ';
  if (toolData.value.pwdLower) chars += 'abcdefghijkmnopqrstuvwxyz';
  if (toolData.value.pwdNumber) chars += '23456789';
  if (toolData.value.pwdSymbol) chars += '!@#$%^&*()_+-=[]{}';
  if (!chars) { ElMessage.warning('请至少选择一种字符类型'); return; }
  let pwd = '';
  const arr = new Uint32Array(toolData.value.pwdLength);
  crypto.getRandomValues(arr);
  for (let i = 0; i < toolData.value.pwdLength; i++) {
    pwd += chars[arr[i] % chars.length];
  }
  toolData.value.pwdOutput = pwd;
};

// ============ 二维码生成（在线 API） ============
const generateQrcode = () => {
  const text = toolData.value.qrInput.trim();
  if (!text) { ElMessage.warning('请输入内容'); return; }
  toolData.value.qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(text)}`;
};

// ============ 进制转换 ============
const convertBase = () => {
  const raw = toolData.value.baseInput.trim();
  if (!raw) { ElMessage.warning('请输入数值'); return; }
  const dec = parseInt(raw, toolData.value.baseFrom);
  if (isNaN(dec)) { ElMessage.error('输入与所选进制不匹配'); return; }
  toolData.value.baseResult = {
    bin: dec.toString(2),
    oct: dec.toString(8),
    dec: dec.toString(10),
    hex: dec.toString(16).toUpperCase()
  };
};

// ============ Cron 解析 ============
const parseCron = () => {
  toolData.value.cronOutput = '';
  toolData.value.cronError = '';
  const parts = toolData.value.cronInput.trim().split(/\s+/);
  if (parts.length !== 5) { toolData.value.cronError = '请输入 5 段式 Cron 表达式（分 时 日 月 周）'; return; }
  const [min, hour, day, month, week] = parts;
  const fields = [
    ['分钟', min, 0, 59], ['小时', hour, 0, 23], ['日期', day, 1, 31], ['月份', month, 1, 12], ['星期', week, 0, 6]
  ];
  const desc = (val, name, lo, hi) => {
    if (val === '*') return `每${name}`;
    if (val.startsWith('*/')) return `每隔 ${val.slice(2)} ${name}`;
    if (val.includes(',')) return `在 ${val} ${name}`;
    if (val.includes('-')) return `${val} ${name}范围`;
    const n = +val;
    if (isNaN(n) || n < lo || n > hi) throw new Error(`${name}字段 "${val}" 超出范围 ${lo}-${hi}`);
    return `第 ${val} ${name}`;
  };
  try {
    toolData.value.cronOutput = fields.map(([n, v, lo, hi]) => desc(v, n, lo, hi)).join('，') + ' 执行';
  } catch (e) {
    toolData.value.cronError = e.message;
  }
};

// ============ 颜色转换 ============
const convertColor = () => {
  const hex = toolData.value.colorInput.trim().replace('#', '');
  if (!/^([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(hex)) {
    toolData.value.colorValid = false;
    toolData.value.colorRgb = '';
    toolData.value.colorHsl = '';
    return;
  }
  toolData.value.colorValid = true;
  const full = hex.length === 3 ? hex.split('').map(c => c + c).join('') : hex;
  const r = parseInt(full.slice(0, 2), 16);
  const g = parseInt(full.slice(2, 4), 16);
  const b = parseInt(full.slice(4, 6), 16);
  toolData.value.colorRgb = `rgb(${r}, ${g}, ${b})`;
  const rn = r / 255, gn = g / 255, bn = b / 255;
  const max = Math.max(rn, gn, bn), min = Math.min(rn, gn, bn);
  let h = 0, s = 0, l = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    if (max === rn) h = (gn - bn) / d + (gn < bn ? 6 : 0);
    else if (max === gn) h = (bn - rn) / d + 2;
    else h = (rn - gn) / d + 4;
    h /= 6;
  }
  toolData.value.colorHsl = `hsl(${Math.round(h * 360)}, ${Math.round(s * 100)}%, ${Math.round(l * 100)}%)`;
};

// ============ cURL 转 fetch 代码 ============
const convertCurl = () => {
  const raw = toolData.value.curlInput.trim();
  if (!raw) { ElMessage.warning('请输入 cURL 命令'); return; }
  try {
    let s = raw.replace(/\\\r?\n/g, ' ').replace(/\s+/g, ' ').trim();
    const urlMatch = s.match(/curl\s+(?:'([^']+)'|"([^"]+)"|(\S+))/);
    let url = urlMatch ? (urlMatch[1] || urlMatch[2] || urlMatch[3]) : '';
    const methodMatch = s.match(/-X\s+(\w+)/i);
    const headers = {};
    const headerRe = /-H\s+(?:'([^']+)'|"([^"]+)")/g;
    let hm;
    while ((hm = headerRe.exec(s)) !== null) {
      const h = hm[1] || hm[2];
      const idx = h.indexOf(':');
      if (idx > -1) headers[h.slice(0, idx).trim()] = h.slice(idx + 1).trim();
    }
    const dataMatch = s.match(/(?:--data|--data-raw|-d)\s+(?:'([^']*)'|"([^"]*)")/);
    const body = dataMatch ? (dataMatch[1] || dataMatch[2]) : null;
    const method = methodMatch ? methodMatch[1].toUpperCase() : (body ? 'POST' : 'GET');
    const opts = { method, headers };
    if (body) opts.body = body;
    toolData.value.curlOutput = `fetch(${JSON.stringify(url)}, ${JSON.stringify(opts, null, 2)})\n  .then(res => res.json())\n  .then(data => console.log(data))\n  .catch(err => console.error(err));`;
  } catch (e) {
    ElMessage.error(`解析失败: ${e.message}`);
  }
};

// ============ HTML 实体编解码 ============
const handleHtmlEntity = () => {
  const input = toolData.value.htmlEntityInput;
  if (!input) { ElMessage.warning('请输入内容'); return; }
  if (toolData.value.htmlEntityMode === 'encode') {
    toolData.value.htmlEntityOutput = input.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  } else {
    const ta = document.createElement('textarea');
    ta.innerHTML = input;
    toolData.value.htmlEntityOutput = ta.value;
  }
};

// ============ Unicode 编解码 ============
const handleUnicode = () => {
  const input = toolData.value.unicodeInput;
  if (!input) { ElMessage.warning('请输入内容'); return; }
  if (toolData.value.unicodeMode === 'encode') {
    toolData.value.unicodeOutput = input.split('').map(c => {
      const code = c.charCodeAt(0);
      return code > 127 ? '\\u' + code.toString(16).padStart(4, '0') : c;
    }).join('');
  } else {
    toolData.value.unicodeOutput = input.replace(/\\u([0-9a-fA-F]{4})/g, (_, g) => String.fromCharCode(parseInt(g, 16)));
  }
};

// ============ JWT 解析 ============
const decodeJwt = () => {
  toolData.value.jwtError = '';
  toolData.value.jwtHeader = '';
  toolData.value.jwtPayload = '';
  const token = toolData.value.jwtInput.trim();
  if (!token) { ElMessage.warning('请输入 JWT Token'); return; }
  const parts = token.split('.');
  if (parts.length !== 3) { toolData.value.jwtError = '无效的 JWT 格式（应包含三段，以.分隔）'; return; }
  try {
    const b64 = (s) => decodeURIComponent(escape(atob(s.replace(/-/g, '+').replace(/_/g, '/'))));
    toolData.value.jwtHeader = JSON.stringify(JSON.parse(b64(parts[0])), null, 2);
    toolData.value.jwtPayload = JSON.stringify(JSON.parse(b64(parts[1])), null, 2);
  } catch (e) {
    toolData.value.jwtError = `解析失败: ${e.message}`;
  }
};

// ============ CSV / JSON 互转 ============
const parseCsv = (text) => {
  const rows = [];
  let row = [], field = '', inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') inQuotes = false;
      else field += c;
    } else {
      if (c === '"') inQuotes = true;
      else if (c === ',') { row.push(field); field = ''; }
      else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
      else if (c === '\r') { /* skip */ }
      else field += c;
    }
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  return rows;
};
const handleCsvJson = () => {
  const input = toolData.value.csvJsonInput.trim();
  if (!input) { ElMessage.warning('请输入内容'); return; }
  try {
    if (toolData.value.csvJsonMode === 'csv2json') {
      const rows = parseCsv(input);
      const headers = rows.shift();
      const arr = rows.filter(r => r.length && r.some(c => c !== '')).map(r => {
        const obj = {};
        headers.forEach((h, i) => { obj[h] = r[i] ?? ''; });
        return obj;
      });
      toolData.value.csvJsonOutput = JSON.stringify(arr, null, 2);
    } else {
      const arr = JSON.parse(input);
      if (!Array.isArray(arr)) throw new Error('JSON 须为数组');
      const headers = [...new Set(arr.flatMap(o => Object.keys(o)))];
      const esc = (v) => {
        const s = v == null ? '' : String(v);
        return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
      };
      const lines = [headers.join(',')];
      arr.forEach(o => lines.push(headers.map(h => esc(o[h])).join(',')));
      toolData.value.csvJsonOutput = lines.join('\n');
    }
  } catch (e) {
    ElMessage.error(`转换失败: ${e.message}`);
  }
};

// ============ Markdown 转 HTML（轻量实现） ============
const convertMarkdown = () => {
  let md = toolData.value.mdInput;
  if (!md.trim()) { ElMessage.warning('请输入 Markdown'); return; }
  const escapeHtml = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  // 代码块
  md = md.replace(/```([\s\S]*?)```/g, (_, c) => `<pre><code>${escapeHtml(c.trim())}</code></pre>`);
  const lines = md.split('\n');
  let html = '', inList = false;
  for (let line of lines) {
    if (/^#{1,6}\s/.test(line)) {
      if (inList) { html += '</ul>'; inList = false; }
      const level = line.match(/^#+/)[0].length;
      html += `<h${level}>${line.replace(/^#+\s/, '')}</h${level}>`;
    } else if (/^[-*+]\s/.test(line)) {
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${line.replace(/^[-*+]\s/, '')}</li>`;
    } else if (line.trim() === '') {
      if (inList) { html += '</ul>'; inList = false; }
    } else if (!/^<(pre|h\d)/.test(line)) {
      if (inList) { html += '</ul>'; inList = false; }
      html += `<p>${line}</p>`;
    } else {
      html += line;
    }
  }
  if (inList) html += '</ul>';
  // 行内：加粗、斜体、行内代码、链接
  html = html
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+?)`/g, '<code>$1</code>')
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2">$1</a>');
  toolData.value.mdOutput = html;
};

// ============ 文本去重排序 ============
const handleDedupe = () => {
  const input = toolData.value.dedupeInput;
  if (!input.trim()) { ElMessage.warning('请输入文本'); return; }
  let lines = input.split('\n');
  if (toolData.value.dedupeTrim) lines = lines.map(l => l.trim());
  if (toolData.value.dedupeRemoveEmpty) lines = lines.filter(l => l !== '');
  const before = lines.length;
  lines = [...new Set(lines)];
  if (toolData.value.dedupeSort === 'asc') lines.sort((a, b) => a.localeCompare(b, 'zh'));
  else if (toolData.value.dedupeSort === 'desc') lines.sort((a, b) => b.localeCompare(a, 'zh'));
  toolData.value.dedupeOutput = lines.join('\n');
  ElMessage.success(`去重前 ${before} 行，去重后 ${lines.length} 行`);
};

// ============ 文本对比 ============
const handleDiff = () => {
  const left = toolData.value.diffLeft.split('\n');
  const right = toolData.value.diffRight.split('\n');
  const max = Math.max(left.length, right.length);
  const result = [];
  for (let i = 0; i < max; i++) {
    const l = left[i] ?? '';
    const r = right[i] ?? '';
    result.push({ line: i + 1, left: l, right: r, same: l === r });
  }
  toolData.value.diffResult = result;
};

// ============ 随机文本生成 ============
const generateLorem = () => {
  const cnPool = '在这个快速发展的时代里软件测试质量保证显得尤为重要我们需要持续不断地优化流程提升效率确保每一个功能都能稳定可靠地运行从而为用户带来更好的体验和价值';
  const enWords = 'lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore et dolore magna aliqua enim ad minim veniam quis nostrud'.split(' ');
  const paras = [];
  for (let p = 0; p < toolData.value.loremCount; p++) {
    if (toolData.value.loremType === 'cn') {
      let para = '';
      const sentences = randInt(3, 6);
      for (let s = 0; s < sentences; s++) {
        const len = randInt(10, 30);
        let sent = '';
        for (let i = 0; i < len; i++) sent += cnPool[randInt(0, cnPool.length - 1)];
        para += sent + '。';
      }
      paras.push(para);
    } else {
      const len = randInt(30, 60);
      let words = [];
      for (let i = 0; i < len; i++) words.push(enWords[randInt(0, enWords.length - 1)]);
      let para = words.join(' ');
      paras.push(para.charAt(0).toUpperCase() + para.slice(1) + '.');
    }
  }
  toolData.value.loremOutput = paras.join('\n\n');
};

// ============ 文件读取辅助 ============
const readFileAsDataURL = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(reader.result);
  reader.onerror = reject;
  reader.readAsDataURL(file);
});
const readFileAsArrayBuffer = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(reader.result);
  reader.onerror = reject;
  reader.readAsArrayBuffer(file);
});
const loadImage = (src) => new Promise((resolve, reject) => {
  const img = new Image();
  img.onload = () => resolve(img);
  img.onerror = reject;
  img.src = src;
});
const formatBytes = (bytes) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(2) + ' MB';
};
const downloadDataUrl = (dataUrl, filename) => {
  const a = document.createElement('a');
  a.href = dataUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

// ============ 图片格式转换 ============
const onImgFmtChange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  toolData.value.imgFmtName = file.name;
  toolData.value.imgFmtSrc = await readFileAsDataURL(file);
  toolData.value.imgFmtResult = '';
};
const convertImageFormat = async () => {
  if (!toolData.value.imgFmtSrc) { ElMessage.warning('请先选择图片'); return; }
  toolData.value.imgFmtLoading = true;
  try {
    const img = await loadImage(toolData.value.imgFmtSrc);
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext('2d');
    if (toolData.value.imgFmtTarget === 'image/jpeg') {
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
    ctx.drawImage(img, 0, 0);
    toolData.value.imgFmtResult = canvas.toDataURL(toolData.value.imgFmtTarget, toolData.value.imgFmtQuality);
  } catch {
    ElMessage.error('转换失败，请检查图片');
  } finally {
    toolData.value.imgFmtLoading = false;
  }
};
const downloadImgFmt = () => {
  const ext = toolData.value.imgFmtTarget.split('/')[1];
  const base = toolData.value.imgFmtName.replace(/\.[^.]+$/, '');
  downloadDataUrl(toolData.value.imgFmtResult, `${base}.${ext}`);
};

// ============ 图片转 PDF ============
const onImg2pdfChange = async (e) => {
  const files = [...e.target.files];
  for (const f of files) {
    toolData.value.img2pdfFiles.push({ name: f.name, src: await readFileAsDataURL(f) });
  }
  e.target.value = '';
};
const removeImg2pdf = (idx) => toolData.value.img2pdfFiles.splice(idx, 1);
const exportImg2pdf = async () => {
  if (!toolData.value.img2pdfFiles.length) { ElMessage.warning('请先添加图片'); return; }
  toolData.value.img2pdfLoading = true;
  try {
    const { jsPDF } = await import('jspdf');
    const pdf = new jsPDF({ unit: 'pt', format: 'a4' });
    const pw = pdf.internal.pageSize.getWidth();
    const ph = pdf.internal.pageSize.getHeight();
    for (let i = 0; i < toolData.value.img2pdfFiles.length; i++) {
      const img = await loadImage(toolData.value.img2pdfFiles[i].src);
      const ratio = Math.min(pw / img.naturalWidth, ph / img.naturalHeight);
      const w = img.naturalWidth * ratio;
      const h = img.naturalHeight * ratio;
      if (i > 0) pdf.addPage();
      const fmt = toolData.value.img2pdfFiles[i].src.includes('image/png') ? 'PNG' : 'JPEG';
      pdf.addImage(toolData.value.img2pdfFiles[i].src, fmt, (pw - w) / 2, (ph - h) / 2, w, h);
    }
    pdf.save('images.pdf');
    ElMessage.success('PDF 已生成');
  } catch (e) {
    ElMessage.error(`生成失败: ${e.message}`);
  } finally {
    toolData.value.img2pdfLoading = false;
  }
};

// ============ PDF 转图片 ============
const onPdf2imgChange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  toolData.value.pdf2imgName = file.name;
  toolData.value.pdf2imgPages = [];
  toolData.value.pdf2imgLoading = true;
  try {
    const pdfjs = await import('pdfjs-dist');
    pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();
    const data = await readFileAsArrayBuffer(file);
    const pdf = await pdfjs.getDocument({ data }).promise;
    const pages = [];
    for (let n = 1; n <= pdf.numPages; n++) {
      const page = await pdf.getPage(n);
      const viewport = page.getViewport({ scale: 2 });
      const canvas = document.createElement('canvas');
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise;
      pages.push({ page: n, url: canvas.toDataURL('image/png') });
    }
    toolData.value.pdf2imgPages = pages;
    ElMessage.success(`已转换 ${pages.length} 页`);
  } catch (e) {
    ElMessage.error(`转换失败: ${e.message}`);
  } finally {
    toolData.value.pdf2imgLoading = false;
  }
};
const downloadPdfPage = (p) => {
  const base = toolData.value.pdf2imgName.replace(/\.[^.]+$/, '');
  downloadDataUrl(p.url, `${base}-${p.page}.png`);
};

// ============ 图片转 Base64 ============
const onImg2b64Change = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  toolData.value.img2b64Name = file.name;
  toolData.value.img2b64Result = await readFileAsDataURL(file);
};

// ============ 图片压缩 ============
const onImgCompChange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  toolData.value.imgCompOrigSize = file.size;
  toolData.value.imgCompSrc = await readFileAsDataURL(file);
  toolData.value.imgCompResult = '';
};
const compressImage = async () => {
  if (!toolData.value.imgCompSrc) { ElMessage.warning('请先选择图片'); return; }
  toolData.value.imgCompLoading = true;
  try {
    const img = await loadImage(toolData.value.imgCompSrc);
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    const result = canvas.toDataURL('image/jpeg', toolData.value.imgCompRatio);
    toolData.value.imgCompResult = result;
    toolData.value.imgCompNewSize = Math.round((result.length - result.indexOf(',') - 1) * 0.75);
  } catch {
    ElMessage.error('压缩失败');
  } finally {
    toolData.value.imgCompLoading = false;
  }
};
const downloadImgComp = () => downloadDataUrl(toolData.value.imgCompResult, 'compressed.jpg');

// ============ Excel 转 JSON ============
const onExcel2jsonChange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  toolData.value.excel2jsonName = file.name;
  toolData.value.excel2jsonLoading = true;
  try {
    const XLSX = await import('xlsx');
    const data = await readFileAsArrayBuffer(file);
    const wb = XLSX.read(data, { type: 'array' });
    const result = {};
    wb.SheetNames.forEach(name => {
      result[name] = XLSX.utils.sheet_to_json(wb.Sheets[name]);
    });
    const single = wb.SheetNames.length === 1 ? result[wb.SheetNames[0]] : result;
    toolData.value.excel2jsonOutput = JSON.stringify(single, null, 2);
    ElMessage.success('转换成功');
  } catch (e) {
    ElMessage.error(`转换失败: ${e.message}`);
  } finally {
    toolData.value.excel2jsonLoading = false;
  }
};

// ============ JSON 转 Excel ============
const exportJson2excel = async () => {
  const input = toolData.value.json2excelInput.trim();
  if (!input) { ElMessage.warning('请输入 JSON 数组'); return; }
  toolData.value.json2excelLoading = true;
  try {
    const arr = JSON.parse(input);
    if (!Array.isArray(arr)) throw new Error('JSON 须为数组');
    const XLSX = await import('xlsx');
    const ws = XLSX.utils.json_to_sheet(arr);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
    XLSX.writeFile(wb, 'data.xlsx');
    ElMessage.success('Excel 已导出');
  } catch (e) {
    ElMessage.error(`导出失败: ${e.message}`);
  } finally {
    toolData.value.json2excelLoading = false;
  }
};

// ============ 接口签名计算 ============
const calculateSign = () => {
  if (!toolData.value.signParams.trim()) { ElMessage.warning('请输入参数'); return; }
  if (!toolData.value.signSecret.trim()) { ElMessage.warning('请输入密钥'); return; }
  try {
    const params = JSON.parse(toolData.value.signParams);
    const sorted = Object.keys(params).sort().map(k => `${k}=${params[k]}`).join('&');
    const raw = sorted + '&key=' + toolData.value.signSecret;
    if (toolData.value.signAlgo === 'md5') {
      toolData.value.signOutput = md5(raw);
    } else {
      crypto.subtle.digest('SHA-256', new TextEncoder().encode(raw)).then(hash => {
        toolData.value.signOutput = Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
      });
    }
  } catch (e) {
    ElMessage.error('参数格式错误');
  }
};

// ============ 测试用例生成 ============
const generateTestCase = () => {
  const input = toolData.value.testCaseInput.trim();
  if (!input) { ElMessage.warning('请输入需求描述'); return; }
  
  const cases = [];
  const keywords = ['登录', '注册', '查询', '添加', '删除', '修改', '密码', '用户名', '手机号', '邮箱'];
  const inputs = ['空', '有效', '超长', '特殊字符', '边界值'];
  
  keywords.forEach(k => {
    if (input.includes(k)) {
      inputs.forEach(i => {
        cases.push(`【${k}】${i}输入测试`);
      });
    }
  });
  
  if (cases.length === 0) {
    cases.push('正常流程测试');
    cases.push('异常流程测试');
    cases.push('边界条件测试');
    cases.push('性能测试');
  }
  
  toolData.value.testCaseOutput = cases.map((c, i) => `${i + 1}. ${c}`).join('\n');
};

// ============ JSON Schema验证 ============
const validateSchema = () => {
  if (!toolData.value.schemaInput.trim()) { ElMessage.warning('请输入 Schema'); return; }
  if (!toolData.value.schemaJson.trim()) { ElMessage.warning('请输入待验证 JSON'); return; }
  try {
    const schema = JSON.parse(toolData.value.schemaInput);
    const data = JSON.parse(toolData.value.schemaJson);
    
    const validate = (obj, sch) => {
      if (sch.type === 'object') {
        if (typeof obj !== 'object' || obj === null) return false;
        if (sch.properties) {
          for (const [k, propSch] of Object.entries(sch.properties)) {
            if (!validate(obj[k], propSch)) return false;
          }
        }
      } else if (sch.type === 'array') {
        if (!Array.isArray(obj)) return false;
        if (sch.items) {
          for (const item of obj) {
            if (!validate(item, sch.items)) return false;
          }
        }
      } else if (typeof obj !== sch.type) {
        return false;
      }
      return true;
    };
    
    const valid = validate(data, schema);
    toolData.value.schemaValid = valid;
    toolData.value.schemaError = valid ? '' : '验证失败';
    toolData.value.schemaResult = valid;
  } catch (e) {
    toolData.value.schemaValid = false;
    toolData.value.schemaError = e.message;
    toolData.value.schemaResult = true;
  }
};

// ============ CSS变量转SCSS ============
const convertCssVars = () => {
  const input = toolData.value.cssVarInput.trim();
  if (!input) { ElMessage.warning('请输入内容'); return; }
  
  if (toolData.value.cssVarMode === 'css2scss') {
    const vars = input.match(/--(\w+)\s*:\s*([^;]+)/g) || [];
    const result = vars.map(v => {
      const match = v.match(/--(\w+)\s*:\s*([^;]+)/);
      return `$${match[1]}: ${match[2].trim()};`;
    }).join('\n');
    toolData.value.cssVarOutput = result || '未找到CSS变量';
  } else {
    const vars = input.match(/\$(\w+)\s*:\s*([^;]+)/g) || [];
    const result = vars.map(v => {
      const match = v.match(/\$(\w+)\s*:\s*([^;]+)/);
      return `--${match[1]}: ${match[2].trim()};`;
    }).join('\n');
    toolData.value.cssVarOutput = result || '未找到SCSS变量';
  }
};

// ============ 代码注释生成 ============
const generateComment = () => {
  const input = toolData.value.commentInput.trim();
  if (!input) { ElMessage.warning('请输入代码'); return; }
  
  const funcMatch = input.match(/function\s+(\w+)\s*\(([^)]*)\)/);
  if (funcMatch) {
    const name = funcMatch[1];
    const params = funcMatch[2].split(',').map(p => p.trim()).filter(Boolean);
    toolData.value.commentOutput = `/**\n * ${name} 函数\n * @description 描述此函数的功能\n${params.map(p => ` * @param {*} ${p} 参数说明`).join('\n')}\n * @returns {*} 返回值说明\n */`;
  } else {
    toolData.value.commentOutput = `/**\n * 代码注释\n * @description 描述此代码的功能\n */\n${input}`;
  }
};

// ============ SQL格式化 ============
const formatSql = () => {
  const input = toolData.value.sqlInput.trim();
  if (!input) { ElMessage.warning('请输入SQL'); return; }
  
  const keywords = ['SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'ORDER BY', 'GROUP BY', 'LIMIT', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'JOIN', 'ON', 'LEFT', 'RIGHT', 'INNER'];
  let result = input;
  
  for (const kw of keywords) {
    const regex = new RegExp(`\\b${kw}\\b`, 'gi');
    result = result.replace(regex, '\n' + kw);
  }
  
  result = result.split('\n').map((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) return '';
    if (i === 0) return trimmed;
    if (['AND', 'OR', 'ON'].includes(trimmed.split(' ')[0])) return '  ' + trimmed;
    return trimmed;
  }).join('\n');
  
  toolData.value.sqlOutput = result;
};

// ============ YAML/JSON互转 ============
const convertYamlJson = () => {
  const input = toolData.value.yamlInput.trim();
  if (!input) { ElMessage.warning('请输入内容'); return; }
  
  try {
    if (toolData.value.yamlMode === 'yaml2json') {
      const lines = input.split('\n');
      const result = {};
      let depth = 0;
      const stack = [result];
      
      for (const line of lines) {
        const match = line.match(/^(\s*)-?\s*([^:]+?)\s*:(.*)/);
        if (match) {
          const lineDepth = match[1].length / 2;
          const key = match[2].trim();
          let value = match[3].trim();
          
          while (depth >= lineDepth) {
            stack.pop();
            depth--;
          }
          
          if (value === '') {
            stack[depth][key] = {};
            stack.push(stack[depth][key]);
            depth++;
          } else {
            if (!isNaN(value)) value = Number(value);
            else if (value === 'true') value = true;
            else if (value === 'false') value = false;
            stack[depth][key] = value;
          }
        }
      }
      
      toolData.value.yamlOutput = JSON.stringify(result, null, 2);
    } else {
      const obj = JSON.parse(input);
      const yaml = (o, d = 0) => {
        const indent = '  '.repeat(d);
        let result = '';
        for (const [k, v] of Object.entries(o)) {
          if (typeof v === 'object' && v !== null) {
            result += `${indent}${k}:\n${yaml(v, d + 1)}`;
          } else {
            result += `${indent}${k}: ${v}\n`;
          }
        }
        return result;
      };
      toolData.value.yamlOutput = yaml(obj);
    }
  } catch (e) {
    ElMessage.error(`转换失败: ${e.message}`);
  }
};

// ============ 图片加水印 ============
const onWatermarkImgChange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  toolData.value.watermarkSrc = await readFileAsDataURL(file);
  toolData.value.watermarkResult = '';
};
const addWatermark = async () => {
  if (!toolData.value.watermarkSrc) { ElMessage.warning('请先选择图片'); return; }
  try {
    const img = await loadImage(toolData.value.watermarkSrc);
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0);
    
    ctx.font = '24px Arial';
    ctx.fillStyle = `rgba(0, 0, 0, ${toolData.value.watermarkOpacity})`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    const step = 80;
    for (let x = 0; x < canvas.width; x += step) {
      for (let y = 0; y < canvas.height; y += step) {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(-Math.PI / 4);
        ctx.fillText(toolData.value.watermarkText, 0, 0);
        ctx.restore();
      }
    }
    
    toolData.value.watermarkResult = canvas.toDataURL('image/png');
  } catch (e) {
    ElMessage.error('添加水印失败');
  }
};
const downloadWatermark = () => downloadDataUrl(toolData.value.watermarkResult, 'watermark.png');

// ============ IP查询 ============
const queryIp = () => {
  const ip = toolData.value.ipInput.trim();
  if (!ip) { ElMessage.warning('请输入IP地址'); return; }
  
  const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
  
  if (!ipv4Regex.test(ip)) {
    toolData.value.ipResult = '无效的IPv4地址';
    return;
  }
  
  if (ip.startsWith('192.168.') || ip.startsWith('10.') || ip.startsWith('172.16.')) {
    toolData.value.ipResult = `${ip}\n类型: 内网IP\n范围: 私有地址段`;
  } else if (ip.startsWith('127.')) {
    toolData.value.ipResult = `${ip}\n类型: 本地回环地址\n说明: 本机地址`;
  } else {
    toolData.value.ipResult = `${ip}\n类型: 公网IP\n说明: 需要联网查询获取详细信息`;
  }
};

// ============ 身份证验证 ============
const validateIdCard = () => {
  const id = toolData.value.idCardInput.trim();
  
  if (id.length !== 18) {
    toolData.value.idCardValid = false;
    toolData.value.idCardResult = '身份证号码必须为18位';
    return;
  }
  
  const regex = /^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/;
  if (!regex.test(id)) {
    toolData.value.idCardValid = false;
    toolData.value.idCardResult = '身份证格式不正确';
    return;
  }
  
  const weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2];
  const codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2'];
  
  let sum = 0;
  for (let i = 0; i < 17; i++) {
    sum += parseInt(id[i]) * weights[i];
  }
  
  const checkCode = codes[sum % 11];
  const lastChar = id[17].toUpperCase();
  
  if (checkCode !== lastChar) {
    toolData.value.idCardValid = false;
    toolData.value.idCardResult = '校验码不正确';
  } else {
    toolData.value.idCardValid = true;
    const province = id.substring(0, 2);
    const year = id.substring(6, 10);
    const month = id.substring(10, 12);
    const day = id.substring(12, 14);
    const gender = parseInt(id[16]) % 2 === 1 ? '男' : '女';
    toolData.value.idCardResult = `✓ 验证通过\n省份代码: ${province}\n出生: ${year}年${month}月${day}日\n性别: ${gender}`;
  }
};

// ============ 日期计算 ============
const calculateDateDiff = () => {
  const start = toolData.value.dateStart.trim();
  const end = toolData.value.dateEnd.trim();
  
  if (!start || !end) {
    ElMessage.warning('请输入完整日期');
    return;
  }
  
  const startDate = new Date(start);
  const endDate = new Date(end);
  
  if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
    toolData.value.dateDiffResult = '日期格式错误';
    return;
  }
  
  const diff = Math.abs(endDate.getTime() - startDate.getTime());
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const months = Math.floor(days / 30.44);
  const years = Math.floor(months / 12);
  
  toolData.value.dateDiffResult = `${start} 至 ${end}\n相隔 ${days} 天\n约 ${months} 个月\n约 ${years} 年`;
};

// ============ 文件大小换算 ============
const convertFileSize = () => {
  const value = toolData.value.fileSizeValue;
  let bytes = value;
  
  switch (toolData.value.fileSizeUnit) {
    case 'kb': bytes *= 1024; break;
    case 'mb': bytes *= 1024 * 1024; break;
    case 'gb': bytes *= 1024 * 1024 * 1024; break;
  }
  
  toolData.value.fileSizeResult = {
    b: bytes,
    kb: (bytes / 1024).toFixed(2),
    mb: (bytes / (1024 * 1024)).toFixed(4),
    gb: (bytes / (1024 * 1024 * 1024)).toFixed(6)
  };
};

// ============ 数字格式化 ============
const formatNumber = () => {
  const input = toolData.value.numberInput.trim();
  if (!input) { ElMessage.warning('请输入数字'); return; }
  
  const num = parseFloat(input);
  if (isNaN(num)) {
    toolData.value.numberOutput = null;
    ElMessage.warning('请输入有效数字');
    return;
  }
  
  toolData.value.numberOutput = {
    thousand: num.toLocaleString(),
    currency: num.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' }),
    percent: (num * 100).toFixed(2) + '%'
  };
};

// ============ 密码强度检测 ============
const checkPwdStrength = () => {
  const pwd = toolData.value.pwdStrengthInput;
  
  let score = 0;
  let result = '';
  let cls = '';
  let percent = 0;
  
  if (pwd.length >= 8) score++;
  if (pwd.length >= 12) score++;
  if (pwd.length >= 16) score++;
  
  if (/[a-z]/.test(pwd)) score++;
  if (/[A-Z]/.test(pwd)) score++;
  if (/[0-9]/.test(pwd)) score++;
  if (/[^a-zA-Z0-9]/.test(pwd)) score++;
  
  if (score <= 2) {
    result = '弱';
    cls = 'weak';
    percent = 25;
  } else if (score <= 4) {
    result = '中等';
    cls = 'medium';
    percent = 50;
  } else if (score <= 6) {
    result = '强';
    cls = 'strong';
    percent = 75;
  } else {
    result = '非常强';
    cls = 'very-strong';
    percent = 100;
  }
  
  toolData.value.pwdStrengthResult = result;
  toolData.value.pwdStrengthClass = cls;
  toolData.value.pwdStrengthPercent = percent;
};

// ============ 数据脱敏 ============
const maskData = () => {
  let input = toolData.value.maskInput.trim();
  if (!input) { ElMessage.warning('请输入内容'); return; }
  
  input = input.replace(/1[3-9]\d{9}/g, (m) => m.substring(0, 3) + '****' + m.substring(7));
  input = input.replace(/(\d{6})\d{8}(\d{4})/g, '$1********$2');
  input = input.replace(/([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+)\.([a-zA-Z]{2,})/g, (_, u, d, t) => {
    const masked = u.length > 3 ? u[0] + '***' + u[u.length - 1] : u;
    return masked + '@' + d + '.' + t;
  });
  
  toolData.value.maskOutput = input;
};

// ============ DNS查询（模拟） ============
const lookupDns = () => {
  const domain = toolData.value.dnsDomain.trim();
  if (!domain) { ElMessage.warning('请输入域名'); return; }
  
  const fakeRecords = {
    'example.com': ['93.184.216.34', '2606:2800:220:1:248:1893:25c8:1946'],
    'baidu.com': ['39.156.66.10', '110.242.68.66'],
    'google.com': ['142.250.185.142', '2607:f8b0:4004:809::200e'],
    'github.com': ['140.82.113.4', '2606:50c0:8000::153']
  };
  
  if (fakeRecords[domain]) {
    toolData.value.dnsResult = `${domain}\nA记录: ${fakeRecords[domain][0]}\nAAAA记录: ${fakeRecords[domain][1]}`;
  } else {
    toolData.value.dnsResult = `${domain}\n提示: 此工具为演示版本，仅支持部分域名查询\n实际使用时需要联网查询`;
  }
};

// ============ 批量替换 ============
const stringReplace = () => {
  const find = toolData.value.replaceFind;
  const replace = toolData.value.replaceReplace;
  const input = toolData.value.replaceInput;
  
  if (!find || !input) { ElMessage.warning('请填写完整'); return; }
  
  toolData.value.replaceOutput = input.split(find).join(replace);
};

// ============ Emoji选择器 ============
const emojiList = [
  '😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '😊',
  '😇', '🥰', '😍', '🤩', '😘', '😗', '😚', '😙', '🥲', '😋',
  '😛', '😜', '🤪', '😝', '🤑', '🤗', '🤭', '🤫', '🤔', '🤐',
  '🤨', '😐', '😑', '😶', '😏', '😒', '🙄', '😬', '🤥', '😌',
  '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔',
  '⭐', '🔥', '💯', '✨', '💪', '👏', '🙌', '🎉', '🎊', '🎁',
  '🚀', '💻', '📱', '🎯', '💡', '🔧', '⚙️', '🔩', '🛠️', '🔬',
  '🌟', '🌈', '🌙', '☀️', '⭐', '🌊', '🍎', '🍕', '🍔', '🍦'
];
const copyEmoji = (emoji) => {
  navigator.clipboard.writeText(emoji);
  ElMessage.success('已复制');
};

// ============ XSS检测 ============
const testXss = () => {
  const input = toolData.value.xssInput.trim();
  if (!input) { ElMessage.warning('请输入内容'); return; }
  
  const xssPatterns = [
    /<script[^>]*>.*?<\/script>/gi,
    /on\w+\s*=\s*["']?[^"'>]+["']?/gi,
    /javascript:/gi,
    /data:text\/html/gi,
    /<iframe[^>]*>/gi,
    /<img[^>]*src\s*=\s*["']?javascript:/gi
  ];
  
  const found = xssPatterns.some(p => p.test(input));
  
  toolData.value.xssSafe = !found;
  toolData.value.xssResult = found ? '⚠️ 检测到XSS风险' : '✓ 未检测到XSS风险';
};

// ============ SQL注入检测 ============
const checkSqlInject = () => {
  const input = toolData.value.sqlInjectInput.trim();
  if (!input) { ElMessage.warning('请输入内容'); return; }
  
  const sqlPatterns = [
    /('|(\%27))/g,
    /((\%3D)|(=))[^\n]*((\%27)|(')|(--)|((\%3B)|(;)))/gi,
    /\w*((\%27)|('))((\%6F)|o|(\%4F))((\%72)|r|(\%52))/gi,
    /((\%27)|('))union/gi,
    /exec(\s|\+)+(s|x)p\w+/gi,
    /insert(\s|\+)+into/gi,
    /delete(\s|\+)+from/gi,
    /drop(\s|\+)+table/gi
  ];
  
  const found = sqlPatterns.some(p => p.test(input.toLowerCase()));
  
  toolData.value.sqlInjectSafe = !found;
  toolData.value.sqlInjectResult = found ? '⚠️ 检测到SQL注入风险' : '✓ 未检测到SQL注入风险';
};

// ============ CSRF Token生成 ============
const generateCsrfToken = () => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let token = '';
  for (let i = 0; i < toolData.value.csrfLength; i++) {
    token += chars[Math.floor(Math.random() * chars.length)];
  }
  toolData.value.csrfOutput = token;
};

// ============ 计算属性：颜色选择器RGB值 ============
const colorPickerRgb = computed(() => {
  const hex = toolData.value.colorPickerValue;
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgb(${r}, ${g}, ${b})`;
});

// ============ 测试报告生成 ============
const generateReport = () => {
  const { reportProject, reportTotal, reportPass, reportFail } = toolData.value;
  if (!reportProject.trim()) { ElMessage.warning('请输入项目名称'); return; }
  const passRate = ((reportPass / reportTotal) * 100).toFixed(2);
  const failRate = ((reportFail / reportTotal) * 100).toFixed(2);
  const skip = reportTotal - reportPass - reportFail;
  const now = new Date().toLocaleString('zh-CN');
  toolData.value.reportOutput =
`====================================
        测试报告
====================================
项目名称: ${reportProject}
生成时间: ${now}
------------------------------------
用例总数: ${reportTotal}
通过用例: ${reportPass}  (${passRate}%)
失败用例: ${reportFail}  (${failRate}%)
跳过用例: ${skip}
------------------------------------
通过率: ${passRate}%
状态: ${passRate >= 90 ? '✓ 优秀' : passRate >= 70 ? '⚠ 合格' : '✗ 不合格'}
====================================`;
};

// ============ 性能测试工具 ============
const runPerfTest = async () => {
  if (!toolData.value.perfUrl.trim()) { ElMessage.warning('请输入目标URL'); return; }
  toolData.value.perfLoading = true;
  const times = [];
  let success = 0;
  for (let i = 0; i < toolData.value.perfCount; i++) {
    const start = Date.now();
    try {
      await fetch(toolData.value.perfUrl, {
        method: toolData.value.perfMethod,
        mode: 'no-cors'
      });
      success++;
    } catch {
      // 跨域不影响计时
    }
    times.push(Date.now() - start);
  }
  const total = times.reduce((a, b) => a + b, 0);
  const avg = Math.round(total / times.length);
  const min = Math.min(...times);
  const max = Math.max(...times);
  toolData.value.perfResult = { avg, min, max, success, total: toolData.value.perfCount };
  toolData.value.perfLoading = false;
};

// ============ API Mock工具 ============
const generateMockApi = () => {
  const { mockApiPath, mockStatus, mockDelay, mockResponseBody } = toolData.value;
  if (!mockApiPath.trim()) { ElMessage.warning('请输入接口路径'); return; }
  let body = mockResponseBody;
  try {
    body = JSON.stringify(JSON.parse(mockResponseBody), null, 2);
  } catch {}
  toolData.value.mockApiOutput =
`// Mock 配置
{
  "url": "${mockApiPath}",
  "method": "GET/POST",
  "status": ${mockStatus},
  "delay": ${mockDelay},
  "response": ${body}
}

// 使用示例（MockServer）
app.get('${mockApiPath}', (req, res) => {
  setTimeout(() => {
    res.status(${mockStatus}).json(${mockResponseBody});
  }, ${mockDelay});
});`;
};

// ============ 压力测试工具 ============
const runLoadTest = async () => {
  if (!toolData.value.loadUrl.trim()) { ElMessage.warning('请输入目标URL'); return; }
  toolData.value.loadLoading = true;
  const total = toolData.value.loadTotal;
  const concurrency = toolData.value.loadConcurrency;
  let completed = 0;
  let failed = 0;
  const times = [];

  const runOne = async () => {
    const start = Date.now();
    try {
      await fetch(toolData.value.loadUrl, { mode: 'no-cors' });
      completed++;
    } catch {
      failed++;
    }
    times.push(Date.now() - start);
  };

  const workers = [];
  for (let w = 0; w < concurrency; w++) {
    workers.push((async () => {
      for (let i = 0; i < Math.ceil(total / concurrency) && completed + failed < total; i++) {
        await runOne();
      }
    })());
  }
  await Promise.all(workers);

  const avg = times.length ? Math.round(times.reduce((a, b) => a + b, 0) / times.length) : 0;
  toolData.value.loadResult =
`压力测试结果
==================================
目标URL: ${toolData.value.loadUrl}
并发数: ${concurrency}
总请求: ${total}
成功: ${completed}
失败: ${failed}
平均响应: ${avg}ms
QPS: ${Math.round(completed / (avg / 1000 * concurrency) * concurrency)}`;
  toolData.value.loadLoading = false;
};

// ============ Socket测试工具 ============
const getNowTime = () => new Date().toLocaleTimeString('zh-CN', { hour12: false });
const connectSocket = () => {
  if (!toolData.value.socketUrl.trim()) { ElMessage.warning('请输入WebSocket地址'); return; }
  try {
    const ws = new WebSocket(toolData.value.socketUrl);
    toolData.value.socketWs = ws;
    ws.onopen = () => {
      toolData.value.socketConnected = true;
      toolData.value.socketLogs.push({ type: 'sys', time: getNowTime(), content: '连接成功' });
    };
    ws.onmessage = (e) => {
      toolData.value.socketLogs.push({ type: 'recv', time: getNowTime(), content: e.data });
    };
    ws.onclose = () => {
      toolData.value.socketConnected = false;
      toolData.value.socketLogs.push({ type: 'sys', time: getNowTime(), content: '连接已断开' });
    };
    ws.onerror = () => {
      toolData.value.socketLogs.push({ type: 'sys', time: getNowTime(), content: '连接错误，请检查地址' });
    };
  } catch (e) {
    ElMessage.error('连接失败');
  }
};
const disconnectSocket = () => {
  if (toolData.value.socketWs) {
    toolData.value.socketWs.close();
    toolData.value.socketWs = null;
  }
};
const sendSocketMsg = () => {
  if (!toolData.value.socketConnected) { ElMessage.warning('请先连接'); return; }
  if (!toolData.value.socketSendMsg.trim()) return;
  toolData.value.socketWs.send(toolData.value.socketSendMsg);
  toolData.value.socketLogs.push({ type: 'send', time: getNowTime(), content: toolData.value.socketSendMsg });
  toolData.value.socketSendMsg = '';
};

// ============ 日志分析工具 ============
const analyzeLog = () => {
  const input = toolData.value.logInput.trim();
  if (!input) { ElMessage.warning('请输入日志内容'); return; }
  const lines = input.split('\n');
  const stats = { total: lines.length, error: 0, warn: 0, info: 0, debug: 0 };
  let filtered = lines;
  if (toolData.value.logLevel !== 'all') {
    const lv = toolData.value.logLevel;
    filtered = lines.filter(l => l.toUpperCase().includes(lv));
  }
  if (toolData.value.logKeyword.trim()) {
    filtered = filtered.filter(l => l.includes(toolData.value.logKeyword));
  }
  lines.forEach(l => {
    const up = l.toUpperCase();
    if (up.includes('ERROR')) stats.error++;
    if (up.includes('WARN') || up.includes('WARNING')) stats.warn++;
    if (up.includes('INFO')) stats.info++;
    if (up.includes('DEBUG')) stats.debug++;
  });
  toolData.value.logStats = stats;
  toolData.value.logOutput = filtered.slice(0, 500).join('\n');
};

// ============ TypeScript转JS（简易：移除类型注解） ============
const convertTsToJs = () => {
  const input = toolData.value.tsInput;
  if (!input.trim()) { ElMessage.warning('请输入TypeScript代码'); return; }
  let result = input;
  // 移除 interface / type 定义
  result = result.replace(/(export\s+)?(interface|type)\s+\w+[^}]*\}/gs, '');
  // 移除变量类型注解: xxx: Type
  result = result.replace(/(:\s*(string|number|boolean|any|void|unknown|never|null|undefined|Array<[^>]+>|\w+\[\]))/g, '');
  // 移除泛型
  result = result.replace(/<\w+>/g, '');
  // 移除 as Type
  result = result.replace(/\s+as\s+\w+/g, '');
  toolData.value.tsOutput = result;
};

// ============ XML格式化 ============
const formatXml = () => {
  const input = toolData.value.xmlInput.trim();
  if (!input) { ElMessage.warning('请输入XML代码'); return; }
  let formatted = '';
  let indent = '';
  input.replace(/(>)(<)(\/*)/g, '$1\n$2$3').split('\n').forEach(node => {
    let pad = 0;
    if (node.match(/.+<\/\w[^>]*>$/)) {
      pad = 0;
    } else if (node.match(/^<\/\w/)) {
      if (indent.length >= 2) indent = indent.substring(2);
      pad = 0;
    } else if (node.match(/^<\w[^>]*[^\/]>.*$/)) {
      pad = 1;
    } else {
      pad = 0;
    }
    formatted += indent + node + '\n';
    if (pad) indent += '  ';
  });
  toolData.value.xmlOutput = formatted.trim();
};
const minifyXml = () => {
  const input = toolData.value.xmlInput.trim();
  if (!input) { ElMessage.warning('请输入XML代码'); return; }
  toolData.value.xmlOutput = input.replace(/>\s+</g, '><').replace(/\s+/g, ' ').trim();
};

// ============ JS压缩工具 ============
const minifyJs = () => {
  const input = toolData.value.jsMinInput;
  if (!input.trim()) { ElMessage.warning('请输入JavaScript代码'); return; }
  const original = input.length;
  let result = input;
  // 移除多行注释
  result = result.replace(/\/\*[\s\S]*?\*\//g, '');
  // 移除单行注释
  result = result.replace(/\/\/[^\n]*/g, '');
  // 移除多余空格
  result = result.replace(/\s+/g, ' ');
  result = result.replace(/\s*([{};,=:+\-*\/<>!&|?])\s*/g, '$1');
  result = result.trim();
  const minified = result.length;
  const ratio = ((1 - minified / original) * 100).toFixed(1);
  toolData.value.jsMinOutput = result;
  toolData.value.jsMinStats = { original, minified, ratio };
};

// ============ CSS压缩工具 ============
const minifyCss = () => {
  const input = toolData.value.cssMinInput;
  if (!input.trim()) { ElMessage.warning('请输入CSS代码'); return; }
  const original = input.length;
  let result = input;
  // 移除注释
  result = result.replace(/\/\*[\s\S]*?\*\//g, '');
  // 移除多余空白
  result = result.replace(/\s+/g, ' ');
  result = result.replace(/\s*([{};:,])\s*/g, '$1');
  result = result.replace(/;}/g, '}');
  result = result.trim();
  const minified = result.length;
  const ratio = ((1 - minified / original) * 100).toFixed(1);
  toolData.value.cssMinOutput = result;
  toolData.value.cssMinStats = { original, minified, ratio };
};

// ============ Babel转换（简易ES6+转ES5） ============
const convertBabel = () => {
  const input = toolData.value.babelInput;
  if (!input.trim()) { ElMessage.warning('请输入ES6+代码'); return; }
  let result = input;
  // 箭头函数转普通函数
  result = result.replace(/const\s+(\w+)\s*=\s*\(([^)]*)\)\s*=>\s*/g, 'function $1($2) { return ');
  result = result.replace(/\(([^)]*)\)\s*=>\s*/g, 'function($1) { return ');
  result = result.replace(/(\w+)\s*=>\s*/g, 'function($1) { return ');
  // let/const 转 var
  result = result.replace(/\bconst\b/g, 'var');
  result = result.replace(/\blet\b/g, 'var');
  // 模板字符串转字符串拼接
  result = result.replace(/`([^`]*)`/g, (_, s) => {
    return '"' + s.replace(/\$\{([^}]+)\}/g, '" + $1 + "') + '"';
  });
  // 解构赋值转普通赋值（简易）
  result = result.replace(/const\s*\{\s*([^}]+)\s*\}\s*=\s*(\w+)/g, (m, props, obj) => {
    return props.split(',').map(p => `var ${p.trim()} = ${obj}.${p.trim()}`).join('; ');
  });
  toolData.value.babelOutput = result;
};

// ============ TXT转Markdown ============
const convertTxtToMd = () => {
  const input = toolData.value.txtMdInput;
  if (!input.trim()) { ElMessage.warning('请输入纯文本'); return; }
  const lines = input.split('\n');
  const md = lines.map((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) return '';
    if (/^\d+[.、]/.test(trimmed)) return trimmed;
    if (/^[一二三四五六七八九十]+[.、]/.test(trimmed)) return trimmed;
    if (trimmed.length < 20 && i < 5) return '# ' + trimmed;
    return trimmed;
  });
  toolData.value.txtMdOutput = md.join('\n');
};

// ============ HTML转文本 ============
const convertHtmlToText = () => {
  const input = toolData.value.htmlTextInput;
  if (!input.trim()) { ElMessage.warning('请输入HTML代码'); return; }
  const tmp = document.createElement('div');
  tmp.innerHTML = input;
  toolData.value.htmlTextOutput = tmp.innerText.trim();
};

// ============ SVG转图片 ============
const convertSvgToImage = async () => {
  const svg = toolData.value.svgInput.trim();
  if (!svg) { ElMessage.warning('请输入SVG代码'); return; }
  try {
    const svgBlob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const scale = toolData.value.svgScale;
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      const ctx = canvas.getContext('2d');
      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0);
      URL.revokeObjectURL(url);
      const fmt = toolData.value.svgFormat === 'png' ? 'image/png' : 'image/jpeg';
      toolData.value.svgResult = canvas.toDataURL(fmt, 0.92);
    };
    img.onerror = () => { ElMessage.error('SVG解析失败'); URL.revokeObjectURL(url); };
    img.src = url;
  } catch (e) {
    ElMessage.error('转换失败');
  }
};
const downloadSvgImage = () => downloadDataUrl(toolData.value.svgResult, `svg-export.${toolData.value.svgFormat}`);

// ============ 图片尺寸调整 ============
const onResizeImgChange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  toolData.value.resizeSrc = await readFileAsDataURL(file);
  toolData.value.resizeResult = '';
  const img = await loadImage(toolData.value.resizeSrc);
  toolData.value.resizeOrigWidth = img.naturalWidth;
  toolData.value.resizeOrigHeight = img.naturalHeight;
  toolData.value.resizeWidth = img.naturalWidth;
  toolData.value.resizeHeight = img.naturalHeight;
};
const resizeImage = async () => {
  if (!toolData.value.resizeSrc) { ElMessage.warning('请先选择图片'); return; }
  try {
    const img = await loadImage(toolData.value.resizeSrc);
    const canvas = document.createElement('canvas');
    canvas.width = toolData.value.resizeWidth;
    canvas.height = toolData.value.resizeHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    toolData.value.resizeResult = canvas.toDataURL('image/png');
  } catch {
    ElMessage.error('调整尺寸失败');
  }
};
const downloadResizedImg = () => downloadDataUrl(toolData.value.resizeResult, 'resized.png');

// ============ PDF合并（演示版） ============
const onPdfMergeChange = async (e) => {
  const files = [...e.target.files];
  for (const f of files) {
    toolData.value.pdfMergeFiles.push({ name: f.name, file: f });
  }
  e.target.value = '';
};
const removePdfMerge = (idx) => toolData.value.pdfMergeFiles.splice(idx, 1);
const mergePdfFiles = async () => {
  if (toolData.value.pdfMergeFiles.length < 2) { ElMessage.warning('请至少选择2个PDF文件'); return; }
  toolData.value.pdfMergeLoading = true;
  try {
    const { jsPDF } = await import('jspdf');
    const pdfjs = await import('pdfjs-dist');
    pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();
    const out = new jsPDF({ unit: 'pt', format: 'a4' });
    for (let i = 0; i < toolData.value.pdfMergeFiles.length; i++) {
      const f = toolData.value.pdfMergeFiles[i].file;
      const data = await readFileAsArrayBuffer(f);
      const pdf = await pdfjs.getDocument({ data }).promise;
      for (let n = 1; n <= pdf.numPages; n++) {
        const page = await pdf.getPage(n);
        const viewport = page.getViewport({ scale: 2 });
        const canvas = document.createElement('canvas');
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise;
        if (i > 0 || n > 1) out.addPage();
        const pw = out.internal.pageSize.getWidth();
        const ph = out.internal.pageSize.getHeight();
        out.addImage(canvas.toDataURL('image/jpeg'), 'JPEG', 0, 0, pw, ph);
      }
    }
    out.save('merged.pdf');
    ElMessage.success('合并成功');
  } catch (e) {
    ElMessage.error(`合并失败: ${e.message}`);
  } finally {
    toolData.value.pdfMergeLoading = false;
  }
};

// ============ 单位换算器 ============
const unitMap = {
  length: [
    { label: '米 (m)', value: 'm', factor: 1 },
    { label: '千米 (km)', value: 'km', factor: 1000 },
    { label: '厘米 (cm)', value: 'cm', factor: 0.01 },
    { label: '毫米 (mm)', value: 'mm', factor: 0.001 },
    { label: '英寸 (in)', value: 'in', factor: 0.0254 },
    { label: '英尺 (ft)', value: 'ft', factor: 0.3048 },
    { label: '码 (yd)', value: 'yd', factor: 0.9144 },
    { label: '英里 (mi)', value: 'mi', factor: 1609.344 }
  ],
  weight: [
    { label: '克 (g)', value: 'g', factor: 1 },
    { label: '千克 (kg)', value: 'kg', factor: 1000 },
    { label: '毫克 (mg)', value: 'mg', factor: 0.001 },
    { label: '吨 (t)', value: 't', factor: 1000000 },
    { label: '磅 (lb)', value: 'lb', factor: 453.592 },
    { label: '盎司 (oz)', value: 'oz', factor: 28.3495 }
  ],
  temperature: [
    { label: '摄氏度 (°C)', value: 'c', factor: 1 },
    { label: '华氏度 (°F)', value: 'f', factor: 1 },
    { label: '开尔文 (K)', value: 'k', factor: 1 }
  ],
  area: [
    { label: '平方米 (m²)', value: 'm2', factor: 1 },
    { label: '平方千米 (km²)', value: 'km2', factor: 1000000 },
    { label: '平方厘米 (cm²)', value: 'cm2', factor: 0.0001 },
    { label: '公顷 (ha)', value: 'ha', factor: 10000 },
    { label: '英亩 (ac)', value: 'ac', factor: 4046.86 },
    { label: '平方英尺 (ft²)', value: 'ft2', factor: 0.0929 }
  ],
  volume: [
    { label: '升 (L)', value: 'l', factor: 1 },
    { label: '毫升 (mL)', value: 'ml', factor: 0.001 },
    { label: '立方米 (m³)', value: 'm3', factor: 1000 },
    { label: '加仑 (gal)', value: 'gal', factor: 3.785 },
    { label: '夸脱 (qt)', value: 'qt', factor: 0.946 },
    { label: '立方英尺 (ft³)', value: 'ft3', factor: 28.3168 }
  ]
};
const unitOptions = computed(() => unitMap[toolData.value.unitType] || []);
const resetUnitValues = () => {
  const opts = unitMap[toolData.value.unitType];
  if (opts && opts.length >= 2) {
    toolData.value.unitFrom = opts[0].value;
    toolData.value.unitTo = opts[1].value;
  }
  toolData.value.unitResult = null;
};
const convertUnit = () => {
  const { unitType, unitValue, unitFrom, unitTo } = toolData.value;
  if (unitType === 'temperature') {
    let celsius;
    if (unitFrom === 'c') celsius = unitValue;
    else if (unitFrom === 'f') celsius = (unitValue - 32) * 5 / 9;
    else celsius = unitValue - 273.15;
    let result;
    if (unitTo === 'c') result = celsius;
    else if (unitTo === 'f') result = celsius * 9 / 5 + 32;
    else result = celsius + 273.15;
    toolData.value.unitResult = result.toFixed(4).replace(/\.?0+$/, '');
    return;
  }
  const fromUnit = unitMap[unitType].find(u => u.value === unitFrom);
  const toUnit = unitMap[unitType].find(u => u.value === unitTo);
  if (!fromUnit || !toUnit) return;
  const base = unitValue * fromUnit.factor;
  const result = base / toUnit.factor;
  toolData.value.unitResult = result.toFixed(6).replace(/\.?0+$/, '');
};

// ============ 转义字符转换 ============
const convertEscape = () => {
  const { escapeMode, escapeType, escapeInput } = toolData.value;
  if (!escapeInput.trim()) { ElMessage.warning('请输入内容'); return; }
  let result = '';
  if (escapeMode === 'encode') {
    if (escapeType === 'json') {
      result = JSON.stringify(escapeInput).slice(1, -1);
    } else if (escapeType === 'regex') {
      result = escapeInput.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    } else if (escapeType === 'shell') {
      result = escapeInput.replace(/(['"\\$`!#&*?[\](){}|;<>])/g, '\\$1');
    }
  } else {
    if (escapeType === 'json') {
      try { result = JSON.parse('"' + escapeInput + '"'); }
      catch { result = escapeInput; }
    } else if (escapeType === 'regex') {
      result = escapeInput.replace(/\\(.)/g, '$1');
    } else if (escapeType === 'shell') {
      result = escapeInput.replace(/\\(.)/g, '$1');
    }
  }
  toolData.value.escapeOutput = result;
};

// ============ 端口扫描 ============
const scanPorts = () => {
  if (!toolData.value.portHost.trim()) { ElMessage.warning('请输入目标主机'); return; }
  toolData.value.portScanning = true;
  const commonPorts = [
    { port: 21, name: 'FTP' },
    { port: 22, name: 'SSH' },
    { port: 23, name: 'Telnet' },
    { port: 25, name: 'SMTP' },
    { port: 53, name: 'DNS' },
    { port: 80, name: 'HTTP' },
    { port: 110, name: 'POP3' },
    { port: 143, name: 'IMAP' },
    { port: 443, name: 'HTTPS' },
    { port: 3306, name: 'MySQL' },
    { port: 5432, name: 'PostgreSQL' },
    { port: 6379, name: 'Redis' },
    { port: 27017, name: 'MongoDB' },
    { port: 8080, name: 'HTTP-Proxy' }
  ];
  const results = [];
  const range = toolData.value.portEnd - toolData.value.portStart + 1;
  let scanned = 0;
  const simulate = () => {
    if (scanned >= 5) {
      toolData.value.portScanning = false;
      return;
    }
    const p = commonPorts[scanned];
    if (p.port >= toolData.value.portStart && p.port <= toolData.value.portEnd) {
      const open = Math.random() > 0.4;
      results.push(`端口 ${p.port} (${p.name}): ${open ? 'OPEN' : 'CLOSED'}`);
    }
    scanned++;
    toolData.value.portResult = `扫描目标: ${toolData.value.portHost}\n端口范围: ${toolData.value.portStart} - ${toolData.value.portEnd}\n\n扫描结果:\n${results.join('\n')}\n\n[模拟扫描，浏览器无法真实探测]`;
    setTimeout(simulate, 300);
  };
  simulate();
};

// ============ 网络延迟测试 ============
const runPingTest = async () => {
  if (!toolData.value.pingHost.trim()) { ElMessage.warning('请输入目标地址'); return; }
  toolData.value.pingLoading = true;
  const times = [];
  for (let i = 0; i < toolData.value.pingCount; i++) {
    const start = Date.now();
    try {
      await fetch(toolData.value.pingHost + '?t=' + Date.now(), { mode: 'no-cors', cache: 'no-store' });
    } catch {}
    times.push(Date.now() - start);
  }
  const avg = Math.round(times.reduce((a, b) => a + b, 0) / times.length);
  const min = Math.min(...times);
  const max = Math.max(...times);
  const jitter = Math.round(max - min);
  toolData.value.pingResult = { avg, min, max, jitter };
  toolData.value.pingLoading = false;
};

// ============ WHOIS查询 ============
const lookupWhois = () => {
  const domain = toolData.value.whoisDomain.trim();
  if (!domain) { ElMessage.warning('请输入域名'); return; }
  toolData.value.whoisResult =
`域名: ${domain}
注册商: Example Registrar
注册日期: 2020-03-15
到期日期: 2026-03-15
状态: active
DNS:
  ns1.example.com
  ns2.example.com
注册人:
  组织: Privacy Protection
  邮箱: privacy@example.com

[提示: 此为演示数据，实际WHOIS需通过服务端查询]`;
};

// ============ HTTP头分析 ============
const analyzeHeaders = () => {
  const input = toolData.value.headerInput.trim();
  if (!input) { ElMessage.warning('请输入HTTP头内容'); return; }
  const lines = input.split('\n').map(l => l.trim()).filter(Boolean);
  const headers = {};
  lines.forEach(line => {
    const idx = line.indexOf(':');
    if (idx > 0) {
      const key = line.substring(0, idx).trim();
      const value = line.substring(idx + 1).trim();
      headers[key] = value;
    }
  });
  let analysis = '解析结果:\n';
  let count = 0;
  for (const [k, v] of Object.entries(headers)) {
    count++;
    analysis += `  ${k}: ${v}\n`;
  }
  analysis += `\n共 ${count} 个请求头`;
  toolData.value.headerResult = analysis;
};

// ============ CDN检测 ============
const checkCdn = () => {
  const url = toolData.value.cdnUrl.trim();
  if (!url) { ElMessage.warning('请输入网站URL'); return; }
  const cdnKeywords = ['cloudflare', 'akamai', 'aliyun', 'tencent', 'qiniu', 'upyun', 'fastly', 'cdn', 'cache'];
  const hasCdn = cdnKeywords.some(k => url.toLowerCase().includes(k));
  toolData.value.cdnHas = hasCdn;
  toolData.value.cdnResult = hasCdn
    ? '✓ 检测到CDN特征（基于URL关键词判断）'
    : '未检测到明确CDN特征（建议通过DNS和响应头综合判断）';
};

// ============ SSL证书检测 ============
const checkSsl = () => {
  const domain = toolData.value.sslDomain.trim();
  if (!domain) { ElMessage.warning('请输入域名'); return; }
  toolData.value.sslResult =
`域名: ${domain}
证书状态: 检测中...

SSL证书信息（演示）:
  颁发者: Let's Encrypt Authority X3
  主体: CN=${domain}
  有效期: 2024-01-01 至 2024-03-31
  剩余天数: 45 天
  证书类型: DV SSL
  加密算法: RSA 2048位
  指纹(SHA256): ...

[提示: 浏览器端无法直接读取SSL证书，此为演示数据]`;
};

// ============ WebSocket测试 ============
const wsConnect = () => {
  if (!toolData.value.wsUrl.trim()) { ElMessage.warning('请输入WebSocket URL'); return; }
  try {
    const ws = new WebSocket(toolData.value.wsUrl);
    toolData.value.wsInstance = ws;
    const addLog = (type, content) => {
      toolData.value.wsLogs.push({ type, time: getNowTime(), content });
    };
    ws.onopen = () => {
      toolData.value.wsConnected = true;
      addLog('sys', '连接成功');
    };
    ws.onmessage = (e) => addLog('recv', e.data);
    ws.onclose = () => {
      toolData.value.wsConnected = false;
      addLog('sys', '连接已关闭');
    };
    ws.onerror = () => {
      addLog('sys', '连接失败，请检查地址');
      toolData.value.wsConnected = false;
    };
  } catch (e) {
    ElMessage.error('连接失败');
  }
};
const wsDisconnect = () => {
  if (toolData.value.wsInstance) {
    toolData.value.wsInstance.close();
    toolData.value.wsInstance = null;
  }
};
const wsSend = () => {
  if (!toolData.value.wsConnected) { ElMessage.warning('请先连接'); return; }
  if (!toolData.value.wsSendMsg.trim()) return;
  toolData.value.wsInstance.send(toolData.value.wsSendMsg);
  toolData.value.wsLogs.push({ type: 'sent', time: getNowTime(), content: toolData.value.wsSendMsg });
  toolData.value.wsSendMsg = '';
};
const wsClearLog = () => { toolData.value.wsLogs = []; };

// ============ AES加密解密（Web Crypto API） ============
const str2ab = (str) => new TextEncoder().encode(str);
const ab2b64 = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf)));
const b642ab = (b64) => Uint8Array.from(atob(b64), c => c.charCodeAt(0));

const doAes = async () => {
  const { aesMode, aesInput, aesKey, aesIv } = toolData.value;
  if (!aesInput.trim()) { ElMessage.warning('请输入内容'); return; }
  if (aesKey.length !== 16 && aesKey.length !== 24 && aesKey.length !== 32) {
    ElMessage.warning('密钥长度必须为16/24/32位'); return;
  }
  try {
    const keyData = str2ab(aesKey.padEnd(32, '\0')).slice(0, aesKey.length);
    const iv = aesIv ? str2ab(aesIv.padEnd(16, '\0')).slice(0, 16) : new Uint8Array(16);
    const key = await crypto.subtle.importKey(
      'raw', keyData, { name: 'AES-CBC' }, false, ['encrypt', 'decrypt']
    );
    if (aesMode === 'encrypt') {
      const encrypted = await crypto.subtle.encrypt(
        { name: 'AES-CBC', iv }, key, str2ab(aesInput)
      );
      toolData.value.aesOutput = ab2b64(encrypted);
    } else {
      const decrypted = await crypto.subtle.decrypt(
        { name: 'AES-CBC', iv }, key, b642ab(aesInput)
      );
      toolData.value.aesOutput = new TextDecoder().decode(decrypted);
    }
  } catch (e) {
    ElMessage.error(`${aesMode === 'encrypt' ? '加密' : '解密'}失败: ${e.message}`);
  }
};

// ============ RSA密钥生成 ============
const generateRsaKeys = async () => {
  toolData.value.rsaLoading = true;
  toolData.value.rsaPublicKey = '';
  toolData.value.rsaPrivateKey = '';
  try {
    const keyPair = await crypto.subtle.generateKey(
      {
        name: 'RSA-OAEP',
        modulusLength: toolData.value.rsaKeySize,
        publicExponent: new Uint8Array([0x01, 0x00, 0x01]),
        hash: 'SHA-256'
      },
      true,
      ['encrypt', 'decrypt']
    );
    const pub = await crypto.subtle.exportKey('spki', keyPair.publicKey);
    const priv = await crypto.subtle.exportKey('pkcs8', keyPair.privateKey);
    const pubB64 = ab2b64(pub);
    const privB64 = ab2b64(priv);
    const formatKey = (b64, type) => {
      const lines = [];
      lines.push(`-----BEGIN ${type}-----`);
      for (let i = 0; i < b64.length; i += 64) lines.push(b64.slice(i, i + 64));
      lines.push(`-----END ${type}-----`);
      return lines.join('\n');
    };
    toolData.value.rsaPublicKey = formatKey(pubB64, 'PUBLIC KEY');
    toolData.value.rsaPrivateKey = formatKey(privB64, 'PRIVATE KEY');
  } catch (e) {
    ElMessage.error(`生成失败: ${e.message}`);
  } finally {
    toolData.value.rsaLoading = false;
  }
};

// ============ 证书生成器 ============
const generateCertificate = () => {
  const { certCountry, certState, certCity, certOrg, certCN, certDays } = toolData.value;
  if (!certCN.trim()) { ElMessage.warning('请输入通用名(CN)'); return; }
  toolData.value.certLoading = true;
  const now = new Date();
  const end = new Date(now.getTime() + certDays * 24 * 3600 * 1000);
  const serial = Math.floor(Math.random() * 100000000).toString(16).toUpperCase();

  const subject = `/C=${certCountry}/ST=${certState}/L=${certCity}/O=${certOrg}/CN=${certCN}`;

  setTimeout(() => {
    toolData.value.certResult =
`服务器证书 (Certificate):
====================================
序列号: ${serial}
签名算法: SHA256WithRSAEncryption
颁发者 (Issuer): ${subject}
主体 (Subject): ${subject}
有效期:
  开始: ${now.toUTCString()}
  结束: ${end.toUTCString()}
  天数: ${certDays} 天
主体公钥: RSA ${toolData.value.rsaKeySize || 2048} bit
指纹 (SHA256):
  ${Array(8).fill(0).map(() => Math.floor(Math.random()*256).toString(16).padStart(2,'0').toUpperCase()).join(':')}

-----BEGIN CERTIFICATE-----
${btoa('CERTIFICATE_DEMO_' + serial + '_' + certCN).match(/.{1,64}/g).join('\n')}
-----END CERTIFICATE-----

[提示: 此为演示证书，实际使用需专业工具生成]`;
    toolData.value.certLoading = false;
  }, 500);
};

// ============ 初始化：恢复最近使用 ============
onMounted(() => {
  try {
    const saved = JSON.parse(localStorage.getItem('recentTools') || '[]');
    recentTools.value = saved.map(id => tools.find(t => t.id === id)).filter(Boolean);
  } catch {
    recentTools.value = [];
  }
});
</script>

<style scoped lang="scss">
.toolbox-page {
  padding: var(--spacing-xl);
  max-width: 1280px;
  margin: 0 auto;
}

/* 页头 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
  flex-wrap: wrap;

  .header-text h1 {
    margin: 0 0 6px;
    font-size: 24px;
    font-weight: 700;
    color: var(--color-text);
  }
  .header-title-row {
    margin-bottom: 8px;
  }
  .back-btn {
    padding: 4px 8px;
    height: auto;
    font-size: 13px;
    color: var(--color-text-secondary);
    span { margin-left: 4px; }
    &:hover { color: var(--color-primary); }
  }
  .header-text p {
    margin: 0;
    font-size: 14px;
    color: var(--color-text-secondary);
  }
  .header-stats {
    display: flex;
    gap: var(--spacing-lg);
  }
  .stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 8px 18px;
    background: var(--color-bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    .stat-num { font-size: 22px; font-weight: 700; color: var(--color-primary); }
    .stat-label { font-size: 12px; color: var(--color-text-muted); }
  }
}

/* 搜索栏 */
.search-section { margin-bottom: var(--spacing-lg); }
.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  height: 44px;
  background: var(--color-bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
  &:focus-within {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px var(--color-primary-bg);
  }
  .search-icon { color: var(--color-text-muted); font-size: 18px; }
  .clear-icon { color: var(--color-text-muted); cursor: pointer; &:hover { color: var(--color-danger); } }
  input {
    flex: 1;
    border: none;
    outline: none;
    background: transparent;
    font-size: 14px;
    color: var(--color-text);
    &::placeholder { color: var(--color-text-placeholder); }
  }
}

/* 最近使用 */
.recent-section { margin-bottom: var(--spacing-lg); }
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  h3 {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    color: var(--color-text);
  }
}
.recent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
}
.recent-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--color-bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  &:hover { border-color: var(--color-primary); transform: translateY(-2px); box-shadow: var(--shadow-md); }
  span { font-size: 13px; color: var(--color-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .recent-icon {
    width: 28px; height: 28px;
    display: flex; align-items: center; justify-content: center;
    border-radius: var(--radius-sm);
    flex-shrink: 0;
  }
}

/* 分类标签 */
.category-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: var(--spacing-lg);
  flex-wrap: wrap;
}
.category-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--color-bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  font-size: 14px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  &:hover { border-color: var(--color-primary); color: var(--color-primary); }
  &.active {
    background: var(--color-primary);
    border-color: var(--color-primary);
    color: #fff;
    .tab-count { background: rgba(255,255,255,0.25); color: #fff; }
  }
  .tab-count {
    padding: 1px 7px;
    font-size: 12px;
    background: var(--color-bg-surface);
    border-radius: var(--radius-full);
    color: var(--color-text-muted);
  }
}

/* 工具网格 */
.tools-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-md);
}
.tool-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
  background: var(--color-bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  cursor: pointer;
  transition: all var(--transition-normal);
  box-shadow: var(--shadow-sm);
  &:hover {
    transform: translateY(-3px);
    box-shadow: var(--shadow-lg);
    border-color: var(--color-primary-border);
    .tool-action { color: var(--color-primary); transform: translateX(3px); }
  }
  .tool-icon {
    width: 48px; height: 48px;
    display: flex; align-items: center; justify-content: center;
    border-radius: var(--radius-lg);
    flex-shrink: 0;
  }
  .tool-info {
    flex: 1; min-width: 0;
    h4 { margin: 0 0 4px; font-size: 15px; font-weight: 600; color: var(--color-text); }
    p { margin: 0; font-size: 13px; color: var(--color-text-muted); line-height: 1.4; }
  }
  .tool-action { color: var(--color-text-muted); transition: all var(--transition-fast); }
}
.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 0;
  color: var(--color-text-muted);
  p { margin: 0; font-size: 14px; }
}

/* 色调（图标背景） */
.blue { background: var(--color-tone-blue-bg); color: var(--color-tone-blue); }
.green { background: var(--color-tone-green-bg); color: var(--color-tone-green); }
.purple { background: var(--color-tone-purple-bg); color: var(--color-tone-purple); }
.orange { background: var(--color-tone-orange-bg); color: var(--color-tone-orange); }
.cyan { background: var(--color-tone-cyan-bg); color: var(--color-tone-cyan); }
.yellow { background: var(--color-tone-yellow-bg); color: var(--color-tone-yellow); }
.red { background: var(--color-tone-red-bg); color: var(--color-tone-red); }
.slate { background: var(--color-tone-slate-bg); color: var(--color-tone-slate); }

/* 弹窗内容 */
.tool-modal-content { padding: 4px 2px; }
.tool-panel { display: flex; flex-direction: column; gap: 16px; }
.panel-row { display: flex; gap: 14px; flex-wrap: wrap; }
.panel-section {
  flex: 1; min-width: 180px;
  display: flex; flex-direction: column;
  label {
    font-size: 13px; font-weight: 600;
    color: var(--color-text-secondary); margin-bottom: 8px;
  }
  textarea, input {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--color-text);
    background: var(--color-bg-card);
    outline: none;
    resize: vertical;
    transition: all var(--transition-fast);
    &:focus { border-color: var(--color-primary); box-shadow: 0 0 0 2px var(--color-primary-bg); }
  }
}
.panel-actions {
  display: flex;
  gap: 10px;
  &.wrap { flex-wrap: wrap; }
}
.output-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  label { margin-bottom: 0; }
}
.code-output {
  margin: 0;
  padding: 14px;
  background: var(--color-bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-text);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 360px;
  overflow: auto;
  line-height: 1.5;
}
.result-box {
  padding: 12px 14px;
  background: var(--color-primary-bg);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--color-text);
  word-break: break-all;
  margin-top: 6px;
  &.big { font-size: 18px; font-weight: 600; letter-spacing: 1px; }
}
.info-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--color-info-bg);
  border: 1px solid var(--color-info-border);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--color-text-secondary);
  strong { font-family: var(--font-mono); color: var(--color-text); }
}
.error-box {
  padding: 10px 14px;
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--color-danger);
}

/* 分段切换 */
.seg-tabs {
  display: inline-flex;
  padding: 3px;
  background: var(--color-bg-surface);
  border-radius: var(--radius-md);
  button {
    padding: 6px 18px;
    border: none;
    background: transparent;
    border-radius: var(--radius-sm);
    font-size: 13px;
    color: var(--color-text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);
    &.active { background: var(--color-bg-card); color: var(--color-primary); box-shadow: var(--shadow-sm); font-weight: 600; }
  }
}

/* hash / uuid 列表 */
.hash-checkboxes { display: flex; gap: 18px; flex-wrap: wrap; }
.hash-results, .uuid-list { display: flex; flex-direction: column; gap: 8px; }
.hash-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--color-bg-surface);
  border-radius: var(--radius-md);
  .hash-label { flex: 0 0 70px; font-size: 12px; font-weight: 600; color: var(--color-primary); }
  .hash-value { flex: 1; font-family: var(--font-mono); font-size: 12px; color: var(--color-text); word-break: break-all; }
}
.uuid-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 12px;
  background: var(--color-bg-surface);
  border-radius: var(--radius-md);
  span { font-family: var(--font-mono); font-size: 13px; color: var(--color-text); }
}

/* 正则结果 */
.regex-result {
  padding: 12px;
  background: var(--color-bg-surface);
  border-radius: var(--radius-md);
  .match-count { font-size: 13px; font-weight: 600; color: var(--color-primary); margin-bottom: 8px; }
  .match-item {
    display: flex; gap: 8px; padding: 4px 0;
    .match-index { color: var(--color-text-muted); font-size: 12px; flex: 0 0 24px; }
    .match-text { font-family: var(--font-mono); font-size: 13px; color: var(--color-text); word-break: break-all; }
  }
}

/* 覆盖率 */
.coverage-result { display: flex; flex-direction: column; gap: 10px; }
.coverage-bar {
  width: 100%; height: 16px;
  background: var(--color-bg-surface);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.coverage-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
  &.high { background: var(--color-success); }
  &.medium { background: var(--color-warning); }
  &.low { background: var(--color-danger); }
}
.coverage-meta { display: flex; align-items: center; gap: 12px; }
.coverage-value { font-size: 22px; font-weight: 700; color: var(--color-text); }
.coverage-status {
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-size: 12px;
  &.high { background: var(--color-success-bg); color: var(--color-success); }
  &.medium { background: var(--color-warning-bg); color: var(--color-warning); }
  &.low { background: var(--color-danger-bg); color: var(--color-danger); }
}

/* 状态徽章 */
.status-badge {
  padding: 1px 8px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-family: var(--font-mono);
  &.ok { background: var(--color-success-bg); color: var(--color-success); }
  &.err { background: var(--color-danger-bg); color: var(--color-danger); }
}

/* 字数统计网格 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}
.stat-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  background: var(--color-bg-surface);
  border-radius: var(--radius-md);
  .num { font-size: 24px; font-weight: 700; color: var(--color-primary); }
  .lbl { font-size: 12px; color: var(--color-text-muted); margin-top: 4px; }
}

/* 颜色预览 */
.color-preview {
  width: 100%; height: 40px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

/* 二维码 */
.qr-preview {
  display: flex;
  justify-content: center;
  padding: 16px;
  img { border: 1px solid var(--border-color); border-radius: var(--radius-md); }
}

/* 文件类工具：图片预览/缩略图/Markdown/对比 */
.img-preview {
  display: flex;
  justify-content: center;
  padding: 12px;
  background: var(--color-bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  img { max-width: 100%; max-height: 280px; border-radius: var(--radius-sm); }
}
.thumb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 12px;
}
.thumb-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 8px;
  background: var(--color-bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  img { width: 100%; height: 120px; object-fit: contain; background: #fff; border-radius: var(--radius-sm); }
  .thumb-name { font-size: 12px; color: var(--color-text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
}
.md-preview {
  padding: 14px;
  background: var(--color-bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  max-height: 360px;
  overflow: auto;
  font-size: 14px;
  line-height: 1.6;
  color: var(--color-text);
  :deep(h1), :deep(h2), :deep(h3) { margin: 12px 0 8px; font-weight: 700; }
  :deep(p) { margin: 6px 0; }
  :deep(ul) { padding-left: 22px; margin: 6px 0; }
  :deep(code) { padding: 1px 5px; background: var(--color-bg-surface); border-radius: 4px; font-family: var(--font-mono); font-size: 13px; }
  :deep(pre) { padding: 12px; background: var(--color-bg-surface); border-radius: var(--radius-md); overflow: auto; }
  :deep(a) { color: var(--color-primary); }
}
.diff-result {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: auto;
  max-height: 360px;
  font-family: var(--font-mono);
  font-size: 13px;
}
.diff-row {
  display: grid;
  grid-template-columns: 44px 1fr 1fr;
  border-bottom: 1px solid var(--border-color-light);
  &.diff { background: var(--color-warning-bg); }
  .diff-ln { padding: 4px 8px; color: var(--color-text-muted); text-align: center; background: var(--color-bg-surface); }
  .diff-col { padding: 4px 8px; white-space: pre-wrap; word-break: break-all; border-left: 1px solid var(--border-color-light); color: var(--color-text); }
}

/* 文件 input 美化 */
.panel-section input[type="file"] {
  padding: 8px;
  font-family: var(--font-sans);
  cursor: pointer;
}

/* 响应式 */
@media (max-width: 768px) {
  .toolbox-page { padding: var(--spacing-md); }
  .page-header { flex-direction: column; align-items: flex-start; }
  .tools-grid { grid-template-columns: 1fr; }
  .panel-row { flex-direction: column; }
  .panel-section { min-width: 0; }
}

/* 提示框 */
.tip-box {
  background: var(--color-bg-soft);
  border-left: 3px solid var(--color-warning);
  padding: 10px 14px;
  color: var(--color-text-secondary);
  font-size: 13px;
  border-radius: 4px;
  margin-top: 8px;
}

/* 文件列表 */
.file-list {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden;
}
.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
}
.file-item:last-child { border-bottom: none; }

/* WebSocket日志 */
.ws-log, .socket-log {
  background: var(--color-bg-soft);
  border-radius: 6px;
  padding: 10px;
  max-height: 300px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}
.ws-log-item, .log-item {
  padding: 4px 0;
  border-bottom: 1px dashed var(--color-border);
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.ws-log-item:last-child, .log-item:last-child { border-bottom: none; }
.ws-log-time, .log-time { color: var(--color-text-secondary); }
.ws-log-label.sent, .log-type.send { color: var(--color-primary); }
.ws-log-label.recv, .log-type.recv { color: var(--color-success); }
.ws-log-label.sys, .log-type.sys { color: var(--color-warning); }
.ws-log-content, .log-content { word-break: break-all; flex: 1; }

/* result-box info */
.result-box.info {
  background: var(--color-info) !important;
  color: var(--color-primary) !important;
  border: 1px solid var(--color-primary) !important;
}
</style>