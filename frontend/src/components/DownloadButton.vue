<template>
  <div class="container">
    <label class="label" :class="{ 'label--small': size === 'small' }">
      <input class="input" type="checkbox" :checked="checked" @change="onToggle" />
      <div class="circle">
        <svg
          class="icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
        <div class="square">
          <svg viewBox="0 0 24 24" fill="none" stroke="#15181f" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
      </div>
      <span class="title">{{ label }}</span>
      <span class="title">{{ doneText }}</span>
    </label>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'

const props = withDefaults(
  defineProps<{ label?: string; doneText?: string; size?: 'normal' | 'small' }>(),
  { label: '下载', doneText: '完成', size: 'normal' },
)

const emit = defineEmits<{ (e: 'download'): void }>()

const checked = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null

function onToggle() {
  checked.value = true
  emit('download')
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    checked.value = false
  }, 4000)
}

onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})
</script>

<style>
/* From Uiverse.io by nazar-gavrylyk */
.container {
  padding: 0;
  margin: 0;
  box-sizing: border-box;
  font-family: Arial, Helvetica, sans-serif;
  display: flex;
  justify-content: center;
  align-items: center;
}

.label {
  --w: 122px;
  --w-checked: 44px;
  --w-installed: 116px;
  --circle: 34px;
  --pad: 4px;
  --font: 14px;
  --icon: 20px;
  --square: 12px;
  --orbit: 20px;

  background-color: transparent;
  border: 2px solid rgb(91, 91, 240);
  display: flex;
  align-items: center;
  border-radius: 50px;
  width: var(--w);
  cursor: pointer;
  transition: all 0.4s ease;
  padding: var(--pad);
  position: relative;
}

.label--small {
  --w: 92px;
  --w-checked: 36px;
  --w-installed: 88px;
  --circle: 26px;
  --pad: 3px;
  --font: 12px;
  --icon: 15px;
  --square: 9px;
  --orbit: 14px;
}

.label::before {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
  background-color: #fff;
  width: 8px;
  height: 8px;
  transition: all 0.4s ease;
  border-radius: 100%;
  margin: auto;
  opacity: 0;
  visibility: hidden;
}

.label .input {
  display: none;
}

.label .title {
  font-size: var(--font);
  color: #15181f;
  transition: all 0.4s ease;
  position: absolute;
  left: calc(var(--circle) + var(--pad) * 2);
  right: var(--pad);
  top: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

.label .title:last-child {
  opacity: 0;
  visibility: hidden;
}

.label .circle {
  height: var(--circle);
  width: var(--circle);
  border-radius: 50%;
  background-color: rgb(91, 91, 240);
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.4s ease;
  position: relative;
  box-shadow: 0 0 0 0 rgb(255, 255, 255);
  overflow: hidden;
}

.label .circle .icon {
  color: #fff;
  width: var(--icon);
  height: var(--icon);
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  transition: all 0.4s ease;
}

.label .circle .square {
  aspect-ratio: 1;
  width: var(--square);
  border-radius: 2px;
  background-color: #fff;
  opacity: 0;
  visibility: hidden;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  transition: all 0.4s ease;
  display: flex;
  justify-content: center;
  align-items: center;
}

.label .circle .square svg {
  width: 100%;
  height: 100%;
}

.label .circle::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  background-color: #3333a8;
  width: 100%;
  height: 0;
  transition: all 0.4s ease;
}

.label:has(.input:checked) {
  width: var(--w-checked);
  animation: installed 0.4s ease 3.5s forwards;
}

.label:has(.input:checked)::before {
  animation: rotate 3s ease-in-out 0.4s forwards;
}

.label .input:checked + .circle {
  animation:
    pulse 1s forwards,
    circleDelete 0.2s ease 3.5s forwards;
  rotate: 180deg;
}

.label .input:checked + .circle::before {
  animation: installing 3s ease-in-out forwards;
}

.label .input:checked + .circle .icon {
  opacity: 0;
  visibility: hidden;
}

.label .input:checked ~ .circle .square {
  opacity: 1;
  visibility: visible;
}

.label .input:checked ~ .title {
  opacity: 0;
  visibility: hidden;
}

.label .input:checked ~ .title:last-child {
  animation: showInstalledMessage 0.4s ease 3.5s forwards;
}

@keyframes pulse {
  0% {
    scale: 0.95;
    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.7);
  }
  70% {
    scale: 1;
    box-shadow: 0 0 0 16px rgba(255, 255, 255, 0);
  }
  100% {
    scale: 0.95;
    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0);
  }
}

@keyframes installing {
  from {
    height: 0;
  }
  to {
    height: 100%;
  }
}

@keyframes rotate {
  0% {
    transform: rotate(-90deg) translate(var(--orbit)) rotate(0);
    opacity: 1;
    visibility: visible;
  }
  99% {
    transform: rotate(270deg) translate(var(--orbit)) rotate(270deg);
    opacity: 1;
    visibility: visible;
  }
  100% {
    opacity: 0;
    visibility: hidden;
  }
}

@keyframes installed {
  100% {
    width: var(--w-installed);
    border-color: rgb(35, 174, 35);
  }
}

@keyframes circleDelete {
  100% {
    opacity: 0;
    visibility: hidden;
  }
}

@keyframes showInstalledMessage {
  100% {
    opacity: 1;
    visibility: visible;
  }
}
</style>