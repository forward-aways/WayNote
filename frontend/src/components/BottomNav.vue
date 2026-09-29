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
  gap: 2px;
  padding: 6px;
  border-radius: var(--wy-r-full);
  box-shadow: var(--wy-float-shadow);
}
.indicator {
  position: absolute;
  top: 6px;
  bottom: 6px;
  left: 0;
  border-radius: var(--wy-r-full);
  /* 淡雅翡翠玻璃（与侧栏激活态同款，保持两端一致；不用发光） */
  background:
    var(--wy-sheen-soft),
    color-mix(in srgb, var(--wy-accent-base) 14%, rgba(255, 255, 255, 0.74));
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.5),
    0 0 0 1px color-mix(in srgb, var(--wy-accent-base) 14%, transparent),
    0 6px 16px rgba(6, 60, 46, 0.12);
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
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-width: 62px;
  padding: 7px 10px 5px;
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
    color-mix(in srgb, var(--wy-accent-base) 14%, rgba(255, 255, 255, 0.74));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5);
}
.nav-label {
  font-size: 11px;
  letter-spacing: 0.5px;
}
@media (min-width: 768px) {
  .bottom-nav {
    display: none;
  }
}
</style>
