<template>
  <!-- 键盘用户可用 Tab 直接跳到主内容，跳过侧栏导航 -->
  <a class="app-skip-link" href="#main-content">跳转到主要内容</a>

  <!-- 路由懒加载期间的顶部进度反馈，避免切页「无响应」体感 -->
  <div v-if="routeLoading" class="route-progress" aria-hidden="true" />

  <router-view v-slot="{ Component }">
    <transition name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup lang="ts">
import { onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const routeLoading = ref(false)
let hideTimer: number | undefined

// 仅在不同路由间切换时显示；afterEach 稍作延迟，等新页面首帧渲染完再收起
const removeBefore = router.beforeEach((to, from) => {
  if (to.fullPath === from.fullPath) return
  window.clearTimeout(hideTimer)
  routeLoading.value = true
})
const removeAfter = router.afterEach(() => {
  window.clearTimeout(hideTimer)
  hideTimer = window.setTimeout(() => {
    routeLoading.value = false
  }, 260)
})

onUnmounted(() => {
  window.clearTimeout(hideTimer)
  removeBefore()
  removeAfter()
})
</script>

<style>
html,
body,
#app {
  height: 100%;
  margin: 0;
  padding: 0;
  background: var(--notion-bg-page, #f5f7fa);
  font-family: var(--notion-font, -apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif);
}

/* 路由切换：轻微淡入上移。prefers-reduced-motion 由 notion.css 全局兜底关闭 */
.page-enter-active,
.page-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

::selection {
  background: rgba(47, 91, 216, 0.2);
}

/* 路由加载进度条：纯装饰，不影响布局与点击 */
.route-progress {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  z-index: var(--z-skip-link);
  overflow: hidden;
  pointer-events: none;
}
.route-progress::after {
  content: '';
  display: block;
  width: 36%;
  height: 100%;
  border-radius: var(--radius-pill);
  background: var(--app-focus-color);
  animation: route-slide 900ms ease-in-out infinite;
}
@keyframes route-slide {
  from { transform: translateX(-100%); }
  to { transform: translateX(380%); }
}
</style>
