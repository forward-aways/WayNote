<script setup lang="ts">
/** 移动端底部胶囊导航：概览 / 地图 / 日历 / 我的
   激活态由一块"玻璃胶囊"滑过去（弹簧缓动，非线性 = 物理惯性 + 落定）
   稳健性：①函数式 ref 经过 resolveElement 解析（router-link 是组件）；
           ②量不到时降级为"激活项自带背景"，激活态永不丢失 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '@/components/AppIcon.vue'
import { resolveElement } from '@/utils/dom'

const route = useRoute()

const ITEMS = [
  { to: '/trips', icon: 'compass', label: '概览' },
  { to: '/map', icon: 'map', label: '地图' },
  { to: '/calendar', icon: 'calendar', label: '日历' },
  { to: '/me', icon: 'user', label: '我的' },
] as const

const active = computed(() => ITEMS.find((item) => route.path.startsWith(item.to))?.to ?? '')

const navRef = ref<HTMLElement | null>(null)
const itemRefs: Array<HTMLElement | null> = []
const indicator = ref({ x: 0, width: 0 })
const ready = ref(false)
const measured = ref(false)

function setItemRef(el: unknown, index: number) {
  itemRefs[index] = resolveElement(el)
}

function measure() {
  const index = ITEMS.findIndex((item) => item.to === active.value)
  const el = resolveElement(itemRefs[index])
  if (!el || el.offsetWidth === 0) return
  indicator.value = { x: el.offsetLeft, width: el.offsetWidth }
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
  window.addEventListener('orientationchange', measure)
  if (typeof ResizeObserver !== 'undefined' && navRef.value) {
    resizeObserver = new ResizeObserver(measure)
    resizeObserver.observe(navRef.value)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', measure)
  window.removeEventListener('orientationchange', measure)
  resizeObserver?.disconnect()
  resizeObserver = null
})
</script>

<template>
  <nav ref="navRef" class="bottom-nav glass-float" :class="{ measured }" aria-label="主导航">
    <span
      class="indicator"
      :class="{ ready }"
      :style="{ transform: `translateX(${indicator.x}px)`, width: `${indicator.width}px` }"
      aria-hidden="true"
    />
    <router-link
      v-for="(item, index) in ITEMS"
      :key="item.to"
      :ref="(el) => setItemRef(el, index)"
      :to="item.to"
      class="nav-item"
      :class="{ active: active === item.to }"
    >
      <AppIcon :name="item.icon" :size="20" />
      <span class="nav-label">{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<style scoped>
.bottom-nav {
  position: fixed;
  left: 50%;
  bottom: calc(12px + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  z-index: 40;
  display: flex;
  /* 宽度跟随屏幕（留 28px 边距）并封顶，项目等分：小屏不溢出，大屏不空旷 */
  width: min(calc(100% - 28px), 400px);
  gap: 6px;
  padding: 7px;
  border-radius: var(--wy-r-full);
  box-shadow: var(--wy-float-shadow);
}
.indicator {
  position: absolute;
  top: 7px;
  bottom: 7px;
  left: 0;
  border-radius: var(--wy-r-full);
  /* 淡雅翡翠玻璃（配方见 tokens 的 --wy-nav-active-*；与侧栏同款） */
  background:
    var(--wy-sheen-soft),
    var(--wy-nav-active-bg);
  border: 1px solid var(--wy-nav-active-rim);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.45),
    var(--wy-nav-active-glow);
}
/* 首帧直接落位，之后启用弹簧滑动（非线性：惯性 + 轻微回弹落定） */
.indicator.ready {
  transition:
    transform var(--wy-dur-slide) var(--wy-spring),
    width var(--wy-dur-slide) var(--wy-spring);
}
.nav-item {
  position: relative;
  z-index: 1;
  flex: 1;
  min-width: 0;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 9px 12px 6px;
  border-radius: var(--wy-r-full);
  /* 通透悬浮层：文字用最深墨色 */
  color: var(--wy-ink-1);
  transition: color 260ms var(--wy-ease);
}
.nav-item:hover {
  text-decoration: none;
  color: var(--wy-ink-1);
}
.nav-item.active {
  color: var(--wy-ink-1);
}
.nav-item:active {
  transform: scale(0.96);
}
/* 降级保障：指示器量不到位置时，激活项自带淡雅翡翠底（激活态永不丢失） */
.bottom-nav:not(.measured) .nav-item.active {
  background:
    var(--wy-sheen-soft),
    var(--wy-nav-active-bg);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.45);
}

/* 放大镜：激活项被"放大"（纯几何放大，字形不变形） */
.nav-item > :deep(svg),
.nav-item > span {
  transition: transform var(--wy-dur) var(--wy-spring);
}
.nav-item.active > span {
  transform: scale(1.12);
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.45);
}
.nav-item.active > :deep(svg) {
  transform: scale(1.14);
}
.nav-label {
  font-size: 12px;
  line-height: 1.15;
  letter-spacing: 0.5px;
}
@media (min-width: 768px) {
  .bottom-nav {
    display: none;
  }
}
</style>
