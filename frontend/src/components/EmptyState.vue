<script setup lang="ts">
withDefaults(defineProps<{ title: string; description?: string }>(), { description: '' })
</script>

<template>
  <div class="empty">
    <div class="empty-art" aria-hidden="true">
      <svg
        viewBox="0 0 160 96"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <rect x="16" y="50" width="46" height="30" rx="6" />
        <path d="M30 50v-6a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v6" />
        <path d="M39 58v14" />
        <path d="M70 74C92 52 114 40 134 36" stroke-dasharray="5 7" />
        <g class="pin">
          <path d="M134 12a14 14 0 0 1 14 14c0 10-14 24-14 24s-14-14-14-24a14 14 0 0 1 14-14Z" />
          <path d="M134 32a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z" />
        </g>
      </svg>
    </div>
    <p class="empty-title wy-display">{{ title }}</p>
    <p v-if="description" class="empty-desc">{{ description }}</p>
    <div class="empty-action">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--wy-s3);
  padding: var(--wy-s12) var(--wy-s4);
  text-align: center;
}
.empty-art {
  color: var(--wy-line-strong);
}
.empty-art .pin {
  color: var(--wy-cinnabar);
}
.empty-art svg {
  width: 160px;
  height: 96px;
}
.empty-title {
  color: var(--wy-ink-2);
  font-size: var(--wy-text-md);
  letter-spacing: 1px;
}
.empty-desc {
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
}
.empty-action {
  margin-top: var(--wy-s2);
}
</style>
