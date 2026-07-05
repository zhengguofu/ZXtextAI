import axios from 'axios'
import { ElMessage } from 'element-plus'
import {
  reportError,
  notifyNetworkError,
  purgeOrphanOverlays,
} from './errorHandler'

/**
 * ============================================================
 * axios 实例 —— 统一封装 & 稳定性兜底
 * ------------------------------------------------------------
 * 关键改进：
 * 1. 所有异常都在拦截器内被"消费"或"降级"，不裸抛
 * 2. 请求出错时主动清理泄漏遮罩，避免"点击无响应"
 * 3. 401/403/404/5xx/超时/网络中断 各自友好文案
 * 4. 保留 reject 以支持业务侧 .catch，但绝不影响全局
 * ============================================================
 */

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ---------- 请求拦截器 ----------
api.interceptors.request.use(
  (config) => {
    // 携带 token（若存在）
    try {
      const token = localStorage.getItem('access_token')
      if (token && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`
      }
    } catch {
      /* localStorage 不可用时忽略 */
    }
    return config
  },
  (error) => {
    reportError('axios-request', error)
    return Promise.reject(error)
  }
)

// ---------- 响应拦截器 ----------
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // 关键：出错立即清理可能泄漏的遮罩，防止界面"卡死"
    purgeOrphanOverlays()

    const status = error?.response?.status
    const url = error?.config?.url || ''
    const code = error?.code

    // 超时
    if (code === 'ECONNABORTED' || /timeout/i.test(error?.message || '')) {
      ElMessage.closeAll()
      ElMessage.warning('请求超时，请稍后重试')
      reportError('axios-timeout', error, { url })
      return Promise.reject(error)
    }

    // 主动取消
    if (code === 'ERR_CANCELED' || axios.isCancel?.(error)) {
      return Promise.reject(error)
    }

    // 网络层错误（无 response）
    if (!error.response) {
      notifyNetworkError(error)
      reportError('axios-network', error, { url })
      return Promise.reject(error)
    }

    // 5xx —— 保留原有 UI/AI 场景的友好提示
    if (status >= 500) {
      if (
        url.includes('ui-automation') ||
        url.includes('automation') ||
        url.includes('browser')
      ) {
        ElMessage.warning('AI 模型服务暂不可用，已自动使用内置 AI 模型，请稍后重试')
      } else {
        ElMessage.error('服务器错误，请稍后重试')
      }
      reportError('axios-5xx', error, { url, status })
      return Promise.reject(error)
    }

    // 401 / 403 / 404 由统一通知处理
    if (status === 401 || status === 403 || status === 404) {
      notifyNetworkError(error)
      reportError(`axios-${status}`, error, { url })
      return Promise.reject(error)
    }

    // 其他 4xx 交由业务层决定文案
    reportError('axios-4xx', error, { url, status })
    return Promise.reject(error)
  }
)

export default api
