<template>
  <div class="error-boundary">
    <slot v-if="!hasError" />
    <div v-else class="error-boundary-fallback">
      <el-result
        icon="error"
        title="页面渲染异常"
        :sub-title="errorMessage || '组件发生错误，请刷新页面或返回重试'"
      >
        <template #extra>
          <el-button type="primary" @click="handleRetry">重新加载</el-button>
          <el-button v-if="errorDetails" text @click="showDetails = !showDetails">
            {{ showDetails ? '隐藏详情' : '查看详情' }}
          </el-button>
        </template>
      </el-result>
      <pre v-if="showDetails && errorDetails" class="error-details">{{ errorDetails }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue'

const hasError = ref(false)
const errorMessage = ref('')
const errorDetails = ref('')
const showDetails = ref(false)

onErrorCaptured((err, instance, info) => {
  hasError.value = true
  errorMessage.value = err?.message || '未知错误'
  errorDetails.value = `${err?.stack || ''}\n\n错误来源: ${info}`
  // 阻止错误继续冒泡，避免应用崩溃
  return false
})

const handleRetry = () => {
  window.location.reload()
}
</script>

<style scoped>
.error-boundary {
  width: 100%;
  height: 100%;
}

.error-boundary-fallback {
  padding: 40px 20px;
}

.error-details {
  margin: 20px auto 0;
  max-width: 800px;
  padding: 16px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  color: #d32f2f;
  font-size: 12px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
