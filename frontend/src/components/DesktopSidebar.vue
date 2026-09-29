<script setup lang="ts">
/** 桌面端常驻左侧栏（染色玻璃 + 与内容的分层阴影） */
import SideNavContent from '@/components/SideNavContent.vue'
</script>

<template>
  <aside class="desktop-side" aria-label="侧边导航">
    <SideNavContent />
  </aside>
</template>

<style scoped>
.desktop-side {
  position: sticky;
  top: 0;
  display: none;
  flex-direction: column;
  flex-shrink: 0;
  width: 248px;
  height: 100vh;
  padding: var(--wy-s4) var(--wy-s3) var(--wy-s6);
  overflow-y: auto;
  background:
    var(--wy-sheen),
    var(--wy-glass-chrome-bg);
  /* 液态玻璃：右侧边缘反光 + 极柔侧向投影 */
  border-right: 1px solid rgba(255, 255, 255, 0.42);
  box-shadow:
    inset -1px 0 0 rgba(255, 255, 255, 0.5),
    8px 0 24px rgba(6, 60, 46, 0.06);
  -webkit-backdrop-filter: blur(var(--wy-glass-chrome-blur)) saturate(var(--wy-glass-chrome-saturate));
  backdrop-filter: blur(var(--wy-glass-chrome-blur)) saturate(var(--wy-glass-chrome-saturate));
}
@media (min-width: 768px) {
  .desktop-side {
    display: flex;
  }
}
</style>
