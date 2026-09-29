<script setup lang="ts">
/** 印章风格标签：状态、分类等短标记 */
withDefaults(
  defineProps<{
    text: string
    tone?: 'cinnabar' | 'indigo' | 'moss' | 'gold' | 'ink'
    filled?: boolean
    size?: 'sm' | 'md'
  }>(),
  { tone: 'ink', filled: false, size: 'sm' },
)
</script>

<template>
  <span class="seal" :class="[`tone-${tone}`, `size-${size}`, { filled }]">{{ text }}</span>
</template>

<style scoped>
.seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 3px 7px;
  border: 1px solid color-mix(in srgb, var(--tone) 45%, transparent);
  border-radius: 6px;
  background: var(--tone-weak);
  color: var(--tone);
  font-size: var(--wy-text-xs);
  line-height: 1.2;
  letter-spacing: 1px;
  white-space: nowrap;
  transform: rotate(-1.5deg);
}
.size-md {
  padding: 4px 9px;
  font-size: var(--wy-text-sm);
}
.filled {
  border-color: var(--tone);
  background: var(--tone);
  color: var(--wy-paper-card);
}
.tone-cinnabar {
  --tone: var(--wy-cinnabar);
  --tone-weak: var(--wy-cinnabar-weak);
}
.tone-indigo {
  --tone: var(--wy-indigo);
  --tone-weak: var(--wy-indigo-weak);
}
.tone-moss {
  --tone: var(--wy-moss);
  --tone-weak: var(--wy-moss-weak);
}
.tone-gold {
  --tone: var(--wy-gold);
  --tone-weak: var(--wy-gold-weak);
}
.tone-ink {
  --tone: var(--wy-ink-3);
  --tone-weak: var(--wy-paper-sunken);
}
</style>
