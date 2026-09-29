<script setup lang="ts">
/** 胶囊标签：主题色（宝石）/ 暖阳 / 中性；gem = 亮宝石面 + 深色字 */
withDefaults(
  defineProps<{
    text: string
    tone?: 'primary' | 'sun' | 'ink' | 'gem'
    size?: 'sm' | 'md'
  }>(),
  { tone: 'ink', size: 'sm' },
)
</script>

<template>
  <span class="chip" :class="[`tone-${tone}`, `size-${size}`]">{{ text }}</span>
</template>

<style scoped>
.chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: var(--wy-r-full);
  background: var(--tone-weak);
  color: var(--tone);
  font-size: var(--wy-text-xs);
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: 0.3px;
  white-space: nowrap;
}
.size-md {
  padding: 5px 12px;
  font-size: var(--wy-text-sm);
}
.tone-primary {
  --tone: var(--wy-primary-strong);
  --tone-weak: var(--wy-primary-weak);
}
.tone-sun {
  --tone: var(--wy-sun-strong);
  --tone-weak: var(--wy-sun-weak);
}
.tone-ink {
  --tone: var(--wy-ink-3);
  --tone-weak: rgba(255, 255, 255, 0.6);
}
/* 宝石胶囊：亮主题色表面 + 深色字（不叠内沿高光线，避免读成"边框"） */
.tone-gem {
  background: var(--wy-jade-surface);
  color: var(--wy-on-jade);
  box-shadow: var(--wy-gem-glow-sm);
}
</style>
