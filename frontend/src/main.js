import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import i18n from './locales'

import App from './App.vue'
import router from './router'
import './assets/css/global.scss'
import { installVueErrorHandler, installWindowErrorHandler, startOverlayWatchdog } from './utils/errorHandler'

const app = createApp(App)

const pinia = createPinia()
app.use(pinia)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(router)
app.use(i18n)

// Element Plus 语言由 App.vue 的 el-config-provider 动态配置
app.use(ElementPlus)

// ========== 全局错误处理安装 ==========
installVueErrorHandler(app)
installWindowErrorHandler()
startOverlayWatchdog()

app.mount('#app')
