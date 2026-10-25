<template>
  <router-view v-slot="{ Component }">
    <transition name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup lang="ts">
// 根组件：仅承载路由出口
</script>

<style>
html,
body,
#app {
  height: 100%;
  margin: 0;
  padding: 0;
  background: #f5f7fa;
  font-family: -apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", Helvetica, Arial, sans-serif;
}

/* 路由切换：轻微淡入上移 */
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
</style>
