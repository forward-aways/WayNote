<script setup lang="ts">
/** 登录/注册共用：居中玻璃面板（背景由全局 BackgroundStage 提供） */
import BrandMark from '@/components/BrandMark.vue'

defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <div class="auth-wrap">
    <section class="panel glass-panel-strong wy-rise">
      <p class="panel-brand">
        <BrandMark :size="26" />
        途笺 Waynote
      </p>
      <h1 class="panel-title wy-display">{{ title }}</h1>
      <p v-if="subtitle" class="panel-sub">{{ subtitle }}</p>
      <slot />
    </section>
  </div>
</template>

<style scoped>
.auth-wrap {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: var(--wy-s6) var(--wy-s4);
}
.panel {
  width: 100%;
  max-width: 420px;
  padding: var(--wy-s8) var(--wy-s6) var(--wy-s6);
  border-radius: var(--wy-r-lg);
}
.panel-brand {
  display: flex;
  align-items: center;
  gap: var(--wy-s2);
  margin: 0;
  color: var(--wy-ink-2);
  font-size: var(--wy-text-sm);
  letter-spacing: 1px;
}
.panel-title {
  margin: var(--wy-s5) 0 var(--wy-s1);
  font-size: var(--wy-text-xl);
}
.panel-sub {
  margin: 0 0 var(--wy-s5);
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
}
</style>
