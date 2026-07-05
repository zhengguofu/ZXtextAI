/**
 * ============================================================
 * 全局错误处理与页面稳定性守护
 * ------------------------------------------------------------
 * 目标：解决"某处出错后其他按钮点击无响应/路由不跳转"的问题
 *
 * 核心思路：
 * 1. Vue 组件级异常统一兜底，不让异常污染响应式系统
 * 2. window 全局 unhandledrejection / error 捕获
 * 3. 弹窗/加载遮罩泄漏时的强制清理（Element Plus 常见问题）
 * 4. 路由跳转失败的诊断与恢复
 * ============================================================
 */

import { ElMessage, ElNotification } from 'element-plus'

// 错误去重节流（避免同一错误刷屏）
const errorCache = new Map()
const ERROR_THROTTLE_MS = 3000

/**
 * 统一错误上报入口
 * @param {string} scope 错误来源标识
 * @param {Error|any} err 错误对象
 * @param {object} [extra] 附加上下文
 */
export function reportError(scope, err, extra = {}) {
  const message = (err && (err.message || err.toString())) || '未知错误'
  const key = `${scope}::${message}`
  const now = Date.now()
  const last = errorCache.get(key)

  if (last && now - last < ERROR_THROTTLE_MS) {
    return // 节流去重
  }
  errorCache.set(key, now)

  // 控制台完整堆栈，便于开发定位
  // eslint-disable-next-line no-console
  console.error(`[${scope}]`, err, extra)

  // 生产环境可对接 Sentry / 自研上报服务
  // if (import.meta.env.PROD) sendToRemote({ scope, message, stack: err?.stack, extra })
}

/**
 * 强制清理泄漏的遮罩层 / 加载态
 * 这是"点击无响应"最常见的元凶：
 * - Element Plus 的 v-loading / ElMessageBox / ElDialog 异常关闭后
 *   .el-overlay 或 .el-loading-mask 未被移除，遮挡所有点击事件
 */
export function purgeOrphanOverlays() {
  try {
    // 1. 全屏加载遮罩（loading.service 泄漏时）
    document
      .querySelectorAll('.el-loading-mask.is-fullscreen')
      .forEach((el) => {
        if (!el.dataset.keep) el.remove()
      })

    // 2. 孤儿 overlay（没有子对话框的空遮罩）
    document.querySelectorAll('.el-overlay').forEach((overlay) => {
      const hasVisibleChild = overlay.querySelector(
        '.el-dialog, .el-message-box, .el-drawer, .el-popover'
      )
      if (!hasVisibleChild) overlay.remove()
    })

    // 3. body 被锁死（弹窗关闭后 overflow:hidden 残留）
    const body = document.body
    if (
      body.style.overflow === 'hidden' &&
      !document.querySelector('.el-overlay, .el-dialog__wrapper')
    ) {
      body.style.overflow = ''
      body.style.paddingRight = ''
      body.classList.remove('el-popup-parent--hidden')
    }
  } catch (e) {
    // 兜底：清理动作本身出错也不能让业务崩溃
    // eslint-disable-next-line no-console
    console.warn('[purgeOrphanOverlays] 清理时异常', e)
  }
}

/**
 * 安装 Vue 全局错误处理
 * @param {import('vue').App} app
 */
export function installVueErrorHandler(app) {
  app.config.errorHandler = (err, instance, info) => {
    reportError('vue', err, {
      component: instance?.$options?.name || instance?.$options?.__name || 'Anonymous',
      info,
    })
    // 组件级异常兜底：清理可能残留的遮罩，保证后续交互能继续
    purgeOrphanOverlays()

    // 温和提示用户，不打断流程
    const msg = err?.message || '当前操作出现异常'
    if (!/ResizeObserver|NavigationDuplicated/i.test(msg)) {
      ElMessage.closeAll()
      ElMessage({
        message: `操作异常已被拦截，可继续使用其他功能`,
        type: 'warning',
        duration: 2500,
        showClose: true,
      })
    }
  }

  // Vue Warn 只在开发环境打印
  if (import.meta.env.DEV) {
    app.config.warnHandler = (msg, instance, trace) => {
      // 过滤已知无害告警
      if (/Extraneous non-props attributes/.test(msg)) return
      // eslint-disable-next-line no-console
      console.warn('[vue-warn]', msg, trace)
    }
  }
}

/**
 * 安装 window 级全局错误监听
 */
export function installWindowErrorHandler() {
  // 未捕获的 Promise 异常（axios reject 忘记 catch 时常见）
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason
    reportError('unhandledrejection', reason)
    // 开发环境：不阻止默认打印，方便定位问题
    // 生产环境：阻止浏览器控制台默认报错刷屏
    if (!import.meta.env.DEV) {
      event.preventDefault()
    }
    // 关键：出现未捕获异常后主动清理遮罩，避免"卡死"感
    purgeOrphanOverlays()
  })

  // 未捕获的同步异常
  window.addEventListener('error', (event) => {
    // 过滤资源加载错误（图片、脚本等），只处理脚本运行错误
    if (event.error) {
      reportError('window-error', event.error, {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      })
      purgeOrphanOverlays()
    }
  })

  // ResizeObserver 循环告警——已知无害，直接吞掉
  const origError = window.console.error
  window.console.error = (...args) => {
    const first = args[0]
    if (
      typeof first === 'string' &&
      (first.includes('ResizeObserver loop') ||
        first.includes('ResizeObserver loop completed'))
    ) {
      return
    }
    origError.apply(window.console, args)
  }
}

/**
 * 定时巡检兜底（每 5s 检查一次是否有孤儿遮罩）
 * 极端情况下即使前面所有兜底都失效，也能自愈
 */
let purgeTimer = null
export function startOverlayWatchdog() {
  if (purgeTimer) return
  purgeTimer = setInterval(() => {
    // 只清理确定孤儿的遮罩，不影响正常弹窗
    const overlays = document.querySelectorAll('.el-overlay')
    overlays.forEach((overlay) => {
      const hasChild = overlay.querySelector(
        '.el-dialog, .el-message-box, .el-drawer, .el-popover'
      )
      // 空 overlay 存在超过 1 秒 → 判定为泄漏
      if (!hasChild) {
        const bornAt = Number(overlay.dataset.bornAt || 0)
        if (!bornAt) {
          overlay.dataset.bornAt = String(Date.now())
        } else if (Date.now() - bornAt > 1000) {
          overlay.remove()
        }
      }
    })
  }, 5000)
}

export function stopOverlayWatchdog() {
  if (purgeTimer) {
    clearInterval(purgeTimer)
    purgeTimer = null
  }
}

/**
 * 网络异常统一提示（供 axios 拦截器调用）
 */
export function notifyNetworkError(error) {
  const status = error?.response?.status
  const url = error?.config?.url || ''

  if (error.code === 'ERR_CANCELED' || error.message === 'canceled') {
    return // 主动取消不提示
  }

  ElMessage.closeAll()

  if (!error.response) {
    // 无响应：断网 / 后端未启动 / CORS
    ElNotification({
      title: '网络异常',
      message: '无法连接到服务器，请检查网络或后端服务是否启动',
      type: 'error',
      duration: 4000,
    })
    return
  }

  if (status === 401) {
    ElMessage.warning('登录状态已过期，请重新登录')
    return
  }
  if (status === 403) {
    ElMessage.warning('您没有权限访问该资源')
    return
  }
  if (status === 404) {
    ElMessage.warning(`接口不存在：${url}`)
    return
  }
  if (status >= 500) {
    // 交给业务侧决定文案（api.js 已处理），此处不重复
    return
  }
}
