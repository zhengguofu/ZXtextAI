<template>
  <el-config-provider :locale="elementLocale">
    <!-- 全局错误边界：捕获路由组件渲染异常，保证应用不崩溃 -->
    <ErrorBoundary>
      <router-view v-slot="{ Component }">
        <Transition name="fade-slide" mode="out-in">
          <component :is="Component" :key="route.fullPath" />
        </Transition>
      </router-view>
    </ErrorBoundary>
  </el-config-provider>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'
import { purgeOrphanOverlays } from '@/utils/errorHandler'
import ErrorBoundary from '@/components/ErrorBoundary.vue'

const appStore = useAppStore()
const route = useRoute()

const elementLocale = computed(() => {
  return appStore.language === 'zh-cn' ? zhCn : en
})

// 页面挂载时清理可能残留的遮罩（应对刷新/前进后退后残留）
onMounted(() => {
  purgeOrphanOverlays()
})

onUnmounted(() => {
  purgeOrphanOverlays()
})
</script>

<style lang="scss">
@use '@/assets/css/global.scss';

#app {
  min-height: 100vh;
  width: 100%;
  overflow: visible;
}

/* 路由切换过渡动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-5px);
}
</style>
