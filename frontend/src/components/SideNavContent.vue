<script setup lang="ts">
/** 导航内容（侧边栏与移动端抽屉共用，避免两套代码漂移）
    激活态由一块"淡雅翡翠玻璃"滑过去（非线性弹簧：惯性 + 落定）
    稳健性：①函数式 ref 经过 resolveElement 解析；②量不到时降级为"激活项自带背景" */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppearanceStore } from '@/stores/appearance'
import AppIcon from '@/components/AppIcon.vue'
import BrandMark from '@/components/BrandMark.vue'
import { resolveElement } from '@/utils/dom'

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

/* ===== 激活态滑动指示器（纵向） ===== */
const navRef = ref<HTMLElement | null>(null)
const itemRefs: Array<HTMLElement | null> = []
const indicator = ref({ y: 0, height: 0 })
const ready = ref(false)
const measured = ref(false)

function setItemRef(el: unknown, index: number) {
  itemRefs[index] = resolveElement(el)
}

function measure() {
  const index = ITEMS.findIndex((item) => item.to === active.value)
  const el = resolveElement(itemRefs[index])
  if (!el || el.offsetHeight === 0) return
  indicator.value = { y: el.offsetTop, height: el.offsetHeight }
  measured.value = true
  if (!ready.value) {
    requestAnimationFrame(() => {
      ready.value = true
    })
  }
}

let resizeObserver: ResizeObserver | null = null

function scheduleMeasure() {
  void nextTick(() => {
    measure()
    // 布局/字体延迟落位时再校一次，避免量到中间态
    window.setTimeout(measure, 120)
  })
}

watch(active, scheduleMeasure)

onMounted(() => {
  scheduleMeasure()
  window.addEventListener('resize', measure)
  if (typeof ResizeObserver !== 'undefined' && navRef.value) {
    resizeObserver = new ResizeObserver(measure)
    resizeObserver.observe(navRef.value)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', measure)
  resizeObserver?.disconnect()
  resizeObserver = null
})

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
      <BrandMark :size="32" />
      <span class="brand-name wy-display">途笺</span>
      <span class="brand-en">Waynote</span>
    </p>

    <nav ref="navRef" class="side-nav" :class="{ measured }" aria-label="主导航">
      <span
        class="side-indicator"
        :class="{ ready }"
        :style="{ transform: `translateY(${indicator.y}px)`, height: `${indicator.height}px` }"
        aria-hidden="true"
      />
      <button
        v-for="(item, index) in ITEMS"
        :key="item.to"
        :ref="(el) => setItemRef(el, index)"
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
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
/* 激活态：淡雅翡翠玻璃（与全站内容卡同族；不用发光、不用纯绿实心） */
.side-indicator {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  border-radius: var(--wy-r-sm);
  background:
    var(--wy-sheen-soft),
    color-mix(in srgb, var(--wy-accent-base) 12%, rgba(255, 255, 255, 0.74));
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.5),
    0 0 0 1px color-mix(in srgb, var(--wy-accent-base) 14%, transparent),
    0 6px 16px rgba(6, 60, 46, 0.1);
  pointer-events: none;
}
/* 首帧直接落位，之后非线性滑动（弹簧落定：先快后慢带一丝回弹，与底栏同款） */
.side-indicator.ready {
  transition:
    transform var(--wy-dur-slide) var(--wy-spring),
    height var(--wy-dur-slide) var(--wy-spring);
}
.side-item {
  position: relative;
  z-index: 1;
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
.side-item.active:hover {
  /* 激活项的底由指示器提供，避免 hover 白块盖在翡翠玻璃上 */
  background: transparent;
}
.side-item:active {
  transform: scale(0.98);
}
/* 降级保障：指示器量不到位置时，激活项自带淡雅翡翠底（激活态永不丢失） */
.side-nav:not(.measured) .side-item.active {
  background:
    var(--wy-sheen-soft),
    color-mix(in srgb, var(--wy-accent-base) 12%, rgba(255, 255, 255, 0.74));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5);
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
