<template>
  <!--
    统一状态反馈组件：loading / empty / error 三态。
    - loading：骨架屏，避免「白屏等待」
    - empty  ：空态，说明为什么空、下一步能做什么
    - error  ：错误态 + 重试按钮，slot 可替换操作区
    无障碍：状态容器为 live region，加载中标记 aria-busy，纯装饰图标 aria-hidden。
  -->
  <div
    class="state-block"
    :class="[`state-block--${state}`, { 'is-compact': compact }]"
    role="status"
    aria-live="polite"
    :aria-busy="state === 'loading'"
  >
    <template v-if="state === 'loading'">
      <div class="sk-row" :style="{ width: skeletonWidths[i % skeletonWidths.length] }" v-for="i in skeletonRows" :key="i" />
      <span class="sr-only">{{ title || '内容加载中' }}</span>
    </template>

    <template v-else>
      <div class="state-icon" aria-hidden="true">
        <slot name="icon">
          <el-icon :size="22"><component :is="state === 'error' ? WarningFilled : FolderOpened" /></el-icon>
        </slot>
      </div>
      <div class="state-title">{{ title || defaultTitle }}</div>
      <p v-if="description" class="state-desc">{{ description }}</p>
      <div v-if="state === 'error' || $slots.default" class="state-actions">
        <slot>
          <el-button size="small" @click="emit('retry')">{{ retryText }}</el-button>
        </slot>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { FolderOpened, WarningFilled } from '@element-plus/icons-vue'

const props = withDefaults(
  defineProps<{
    /** 当前状态 */
    state: 'loading' | 'empty' | 'error'
    /** 主文案，缺省时按状态给出默认文案 */
    title?: string
    /** 补充说明，建议写清「下一步能做什么」 */
    description?: string
    /** 骨架行数 */
    skeletonRows?: number
    /** 重试按钮文案 */
    retryText?: string
    /** 紧凑模式：用于卡片内嵌的小块区域 */
    compact?: boolean
  }>(),
  {
    skeletonRows: 4,
    retryText: '重新加载',
    compact: false,
  },
)

const emit = defineEmits<{ (e: 'retry'): void }>()

const defaultTitle = computed(() => (props.state === 'error' ? '加载失败' : '暂无内容'))
const skeletonWidths = ['92%', '76%', '84%', '60%', '88%']
</script>

<style scoped>
.state-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: 180px;
  padding: var(--space-8) var(--space-4);
  text-align: center;
  color: var(--notion-text-secondary);
}
.state-block.is-compact {
  min-height: 120px;
  padding: var(--space-6) var(--space-3);
}

/* ---- 骨架屏 ---- */
.sk-row {
  height: 12px;
  border-radius: var(--radius-sm);
  background: linear-gradient(
    90deg,
    var(--notion-hover) 25%,
    #e9edf3 50%,
    var(--notion-hover) 75%
  );
  background-size: 200% 100%;
  animation: sk-shimmer 1.4s ease-in-out infinite;
}
.state-block--loading {
  align-items: flex-start;
  justify-content: flex-start;
  gap: var(--space-3);
  min-height: 0;
  padding: var(--space-4);
}
@keyframes sk-shimmer {
  from { background-position: 200% 0; }
  to { background-position: -200% 0; }
}

/* ---- 空态 / 错误态 ---- */
.state-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  margin-bottom: var(--space-1);
  border-radius: var(--radius-md);
  background: var(--notion-bg-page);
  border: 1px solid var(--notion-border);
  color: var(--notion-text-muted);
}
.state-block--error .state-icon {
  background: var(--el-color-danger-light-9);
  border-color: var(--el-color-danger-light-7);
  color: var(--notion-red);
}
.state-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--notion-text);
}
.state-desc {
  max-width: 380px;
  margin: 0;
  font-size: 12px;
  line-height: 1.7;
  color: var(--notion-text-muted);
}
.state-actions {
  margin-top: var(--space-2);
}

/* 屏幕阅读器专用文本 */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
