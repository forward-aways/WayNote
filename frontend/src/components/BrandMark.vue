<script lang="ts">
// 模块级序号：同一页面可能渲染多个品牌标，避免 SVG 渐变 id 冲突
let seq = 0
</script>

<script setup lang="ts">
/** 品牌标：与标签页 favicon 同款图形（圆角方块 + 虚线路线 + 起点/终点）。
    渐变固定为品牌色（不随主题变化），与 favicon 完全一致。
    注意：填充/描边必须走 CSS（SVG 表现属性不支持 var()，写属性会静默失效）。 */
withDefaults(defineProps<{ size?: number }>(), { size: 28 })

const gradientId = `wy-brand-mark-${(seq += 1)}`
</script>

<template>
  <svg
    class="brand-mark"
    :width="size"
    :height="size"
    viewBox="0 0 32 32"
    aria-hidden="true"
    focusable="false"
  >
    <defs>
      <linearGradient :id="gradientId" x1="0" y1="0" x2="1" y2="1">
        <stop class="mark-from" offset="0" />
        <stop class="mark-to" offset="1" />
      </linearGradient>
    </defs>
    <rect
      class="mark-tile"
      width="32"
      height="32"
      rx="9"
      :style="{ fill: `url(#${gradientId})` }"
    />
    <path
      class="mark-line"
      d="M8 22c4-9 10-13.4 16-13.6"
      stroke-width="2"
      stroke-linecap="round"
      stroke-dasharray="3.2 3.2"
    />
    <circle class="mark-dot" cx="8" cy="22" r="1.7" />
    <circle class="mark-ring" cx="24" cy="8.4" r="3.4" />
    <circle class="mark-core" cx="24" cy="8.4" r="1.3" />
  </svg>
</template>

<style scoped>
.brand-mark {
  display: block;
  flex-shrink: 0;
}
.mark-from {
  stop-color: var(--wy-brand-mark-from);
}
.mark-to {
  stop-color: var(--wy-brand-mark-to);
}
.mark-line {
  fill: none;
  stroke: var(--wy-surface);
}
.mark-dot,
.mark-ring {
  fill: var(--wy-surface);
}
.mark-core {
  fill: var(--wy-brand-mark-from);
}
</style>
