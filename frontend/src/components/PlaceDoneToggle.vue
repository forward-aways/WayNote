<script setup lang="ts">
/** 地点完成勾选圆钮（ADR-20261012）：
 *  呈现 + 无障碍语义（role=checkbox），状态迁移与乐观更新由父组件负责。 */
import AppIcon from '@/components/AppIcon.vue'

defineProps<{
  done: boolean
  /** 无障碍名称的主体（地点名） */
  name: string
  /** 请求在途：禁用防连点 */
  busy?: boolean
}>()

const emit = defineEmits<{ toggle: [] }>()
</script>

<template>
  <button
    class="done-toggle"
    :class="{ 'is-on': done }"
    type="button"
    role="checkbox"
    :aria-checked="done"
    :aria-label="`${done ? '取消完成' : '标记完成'}：${name}`"
    :disabled="busy"
    @click.stop="emit('toggle')"
  >
    <AppIcon v-if="done" name="check" :size="13" />
  </button>
</template>

<style scoped>
.done-toggle {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1.5px solid var(--wy-line-strong);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.55);
  color: var(--wy-on-jade);
  cursor: pointer;
  transition:
    background var(--wy-dur) var(--wy-ease),
    border-color var(--wy-dur) var(--wy-ease),
    transform var(--wy-dur) var(--wy-spring);
}
.done-toggle:hover:not(:disabled) {
  transform: scale(1.06);
}
.done-toggle:hover:not(:disabled):not(.is-on) {
  border-color: var(--wy-primary);
}
.done-toggle.is-on:hover:not(:disabled) {
  filter: brightness(1.06);
}
.done-toggle:active:not(:disabled) {
  transform: scale(0.92);
}
/* 勾选态 = 宝石表面 + 宝石面墨色（与主按钮同款配方）：
   ① background-origin: border-box —— 否则渐变只铺 padding-box、边框区平铺出"深绿假边框"；
   ② 只叠中性近距投影，不叠彩色光晕（见 tokens.css 的教训） */
.done-toggle.is-on {
  background: var(--wy-jade-surface);
  background-origin: border-box;
  border-color: transparent;
  box-shadow: var(--wy-gem-glow-sm);
  animation: done-pop var(--wy-dur) var(--wy-spring);
}
.done-toggle:disabled {
  opacity: 0.55;
  cursor: progress;
}

@keyframes done-pop {
  0% {
    transform: scale(0.82);
  }
  60% {
    transform: scale(1.08);
  }
  100% {
    transform: scale(1);
  }
}
</style>
