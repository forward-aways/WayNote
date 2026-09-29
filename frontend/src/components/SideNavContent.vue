<script setup lang="ts">
/** 导航内容（侧边栏与移动端抽屉共用，避免两套代码漂移） */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppearanceStore } from '@/stores/appearance'
import AppIcon from '@/components/AppIcon.vue'

const emit = defineEmits<{ navigate: [] }>()

const route = useRoute()
const router = useRouter()
const appearance = useAppearanceStore()

const ITEMS = [
  { to: '/trips', icon: 'compass', label: '概览' },
  { to: '/map', icon: 'map', label: '地图' },
  { to: '/calendar', icon: 'calendar', label: '日历' },
  { to: '/me', icon: 'user', label: '我的' },
] as const

const active = computed(() => ITEMS.find((item) => route.path.startsWith(item.to))?.to ?? '')

function go(path: string) {
  router.push(path)
  emit('navigate')
}

function openAppearance() {
  appearance.sheetOpen = true
  emit('navigate')
}
</script>

<template>
  <div class="side">
    <p class="side-brand">
      <span class="brand-tile" aria-hidden="true">途</span>
      <span class="brand-name wy-display">途笺</span>
      <span class="brand-en">Waynote</span>
    </p>

    <nav class="side-nav" aria-label="主导航">
      <button
        v-for="item in ITEMS"
        :key="item.to"
        type="button"
        class="side-item"
        :class="{ active: active === item.to }"
        @click="go(item.to)"
      >
        <AppIcon :name="item.icon" :size="18" />
        <span>{{ item.label }}</span>
      </button>
    </nav>

    <div class="side-divider" />

    <button type="button" class="side-item" @click="openAppearance">
      <AppIcon name="image" :size="18" />
      <span>外观设置</span>
    </button>
  </div>
</template>

<style scoped>
.side {
  display: flex;
  flex-direction: column;
  gap: var(--wy-s2);
  height: 100%;
}
.side-brand {
  display: flex;
  align-items: center;
  gap: var(--wy-s2);
  padding: var(--wy-s2) var(--wy-s3) var(--wy-s4);
  margin: 0;
}
.brand-tile {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: var(--wy-jade-surface);
  color: var(--wy-on-jade);
  font-size: var(--wy-text-base);
  font-weight: 700;
  box-shadow:
    var(--wy-gem-highlight),
    var(--wy-gem-glow);
}
.brand-name {
  font-size: var(--wy-text-lg);
  color: var(--wy-ink-1);
}
.brand-en {
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  letter-spacing: 1.5px;
  text-transform: uppercase;
}
.side-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.side-item {
  display: flex;
  align-items: center;
  gap: var(--wy-s3);
  width: 100%;
  padding: 11px var(--wy-s3);
  border: none;
  border-radius: var(--wy-r-sm);
  background: transparent;
  /* 通透悬浮层上必须用最深墨色（浅色文字在低不透明度下不达标） */
  color: var(--wy-ink-1);
  font-size: var(--wy-text-base);
  text-align: left;
  cursor: pointer;
  transition:
    background var(--wy-dur) var(--wy-ease),
    color var(--wy-dur) var(--wy-ease),
    transform var(--wy-dur) var(--wy-spring);
}
.side-item:hover {
  background: rgba(255, 255, 255, 0.5);
}
.side-item:active {
  transform: scale(0.98);
}
.side-item.active {
  /* 透明淡绿光玻璃：主题色轻染 + 描边光 + 外发光（替代纯绿实心胶囊） */
  background: color-mix(in srgb, var(--wy-accent-base) 16%, rgba(255, 255, 255, 0.28));
  border: 1px solid color-mix(in srgb, var(--wy-accent-base) 32%, rgba(255, 255, 255, 0.5));
  color: var(--wy-ink-1);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.5),
    0 0 0 1px color-mix(in srgb, var(--wy-accent-base) 10%, transparent),
    0 8px 22px color-mix(in srgb, var(--wy-accent-base) 26%, transparent);
  -webkit-backdrop-filter: blur(10px) saturate(160%);
  backdrop-filter: blur(10px) saturate(160%);
}
.side-divider {
  height: 1px;
  margin: var(--wy-s2) var(--wy-s3);
  background: var(--wy-line);
}
@media (max-width: 480px) {
  .brand-en {
    display: none;
  }
}
</style>
