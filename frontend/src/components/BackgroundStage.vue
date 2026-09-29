<script setup lang="ts">
/** L0/L1 背景舞台：用户背景 + 可读性遮罩 + 极光光斑（固定层，位于所有内容之下） */
import { useAppearanceStore } from '@/stores/appearance'

const appearance = useAppearanceStore()
</script>

<template>
  <div class="stage" aria-hidden="true">
    <div class="stage-bg" />
    <div class="stage-scrim" />
    <div v-if="appearance.aurora" class="stage-aurora">
      <span class="blob blob-a" />
      <span class="blob blob-b" />
      <span class="blob blob-c" />
    </div>
  </div>
</template>

<style scoped>
.stage {
  position: fixed;
  inset: 0;
  z-index: -1;
  overflow: hidden;
  pointer-events: none;
}
.stage-bg {
  position: absolute;
  inset: 0;
  background-image: var(--wy-user-bg), var(--wy-user-bg-fallback);
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}
.stage-scrim {
  position: absolute;
  inset: 0;
  background: var(--wy-scrim);
}
.stage-aurora .blob {
  position: absolute;
  width: 58vmax;
  height: 58vmax;
  border-radius: 50%;
  filter: blur(56px);
  opacity: 0.78;
  will-change: transform;
}
.blob-a {
  top: -18vmax;
  left: -12vmax;
  background: var(--wy-aurora-1);
  animation: wy-drift-a 22s var(--wy-ease) infinite;
}
.blob-b {
  right: -16vmax;
  bottom: -22vmax;
  background: var(--wy-aurora-2);
  animation: wy-drift-b 26s var(--wy-ease) infinite;
}
.blob-c {
  top: 28%;
  left: 44%;
  width: 40vmax;
  height: 40vmax;
  background: var(--wy-aurora-3);
  animation: wy-drift-a 30s var(--wy-ease) infinite reverse;
}
</style>
