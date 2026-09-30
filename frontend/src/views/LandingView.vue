<script setup lang="ts">
/** 首屏路线起始动画（图钉沿弧线行进 + 标题逐字淡入）+ 下滑三屏特性（左右结构 + 示例卡 + 专属图标动画） */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import BrandMark from '@/components/BrandMark.vue'

const FEATURES = [
  { title: '行程规划', desc: '按天安排地点，时间与备注一目了然' },
  { title: '日历与地图', desc: '月视图纵览行程，坐标地点一键跳转' },
  { title: '随心外观', desc: '自定义背景与光斑，界面属于你自己' },
] as const

const TITLE_LINES = ['把想去的地方', '变成下一段旅途'] as const

/** 标题按字拆分（带全局序号，用于逐字延迟） */
const TITLE_CHARS = (() => {
  let index = 0
  return TITLE_LINES.map((line) => [...line].map((ch) => ({ ch, index: index++ })))
})()

const CHAR_COUNT = TITLE_CHARS.reduce((sum, line) => sum + line.length, 0)

/** 首屏起始动画时序（毫秒）：一处定义，模板与样式共用 */
const TIMING = {
  draw: 1500, // 弧线绘制 + 图钉行进时长
  textStart: 140, // 标题开始逐字淡入
  charStep: 62, // 每个字的间隔
  cta: 1560, // 按钮淡入（图钉抵达后）
}

const heroTimingVars = {
  '--pn-draw': `${TIMING.draw}ms`,
  '--pn-text-start': `${TIMING.textStart}ms`,
  '--pn-char-step': `${TIMING.charStep}ms`,
  '--pn-cta-delay': `${TIMING.cta}ms`,
}

/** 副标题跟在标题最后一字之后 */
const subDelay = `${TIMING.textStart + CHAR_COUNT * TIMING.charStep + 80}ms`

/** 示例卡：一天的行程 */
const DEMO_PLAN = [
  { time: '09:00', place: '断桥残雪' },
  { time: '11:30', place: '楼外楼午餐' },
  { time: '14:00', place: '苏堤春晓' },
  { time: '16:30', place: '雷峰夕照' },
] as const

/** 示例卡：月视图（高亮一段行程） */
const DEMO_WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日'] as const
const DEMO_DAYS = Array.from({ length: 28 }, (_, i) => i + 2)
const DEMO_TRIP_DAYS = new Set([10, 11, 12])

/** 示例卡：主题色与预设背景（直接用真实令牌，换主题时演示同步变化） */
const DEMO_ACCENTS = [
  { name: '翡翠', color: 'var(--wy-accent-preset-emerald)' },
  { name: '青玉', color: 'var(--wy-accent-preset-teal)' },
  { name: '蓝宝石', color: 'var(--wy-accent-preset-sapphire)' },
  { name: '紫水晶', color: 'var(--wy-accent-preset-amethyst)' },
  { name: '琥珀', color: 'var(--wy-accent-preset-amber)' },
  { name: '珊瑚', color: 'var(--wy-accent-preset-coral)' },
] as const

/** 示例里"当前选中"的主题色 */
const DEMO_ACTIVE_ACCENT = '翡翠'

const DEMO_WALLS = [
  { name: '极光', color: 'var(--wy-bg-preset-aurora)' },
  { name: '翡翠', color: 'var(--wy-bg-preset-emerald)' },
  { name: '蓝宝石', color: 'var(--wy-bg-preset-sapphire)' },
  { name: '日出', color: 'var(--wy-bg-preset-sunrise)' },
] as const

/** 下滑三屏：进入视口时依次浮出（显示后保持，回滚不消失） */
const revealed = ref<boolean[]>(FEATURES.map(() => false))
const paneEls: HTMLElement[] = []
let observer: IntersectionObserver | null = null

const setPaneRef = (el: Element | ComponentPublicInstance | null, index: number) => {
  if (el instanceof HTMLElement) paneEls[index] = el
}

onMounted(() => {
  // 不支持 IntersectionObserver：直接全部显示，绝不把内容藏死
  if (!('IntersectionObserver' in window)) {
    revealed.value = FEATURES.map(() => true)
    return
  }
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue
        const index = paneEls.indexOf(entry.target as HTMLElement)
        if (index >= 0) revealed.value[index] = true
      }
    },
    { threshold: 0.35 },
  )
  for (const el of paneEls) observer.observe(el)
})

onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <div class="landing">
    <!-- 第一屏：地图动画 + 标题 + 按钮（整屏居中） -->
    <section class="pane pane-hero" :style="heroTimingVars">
      <header class="hero-top">
        <span class="brand">
          <BrandMark :size="30" />
          <span class="brand-name wy-display">途笺</span>
          <span class="brand-en">Waynote</span>
        </span>
      </header>

      <div class="hero wy-container">
        <div class="hero-art" aria-hidden="true">
          <!-- 弧线整体下移留出头部空间：图钉针尖贴路径时钉身不会再跳出视窗 -->
          <svg viewBox="0 0 320 156" fill="none">
            <path
              class="route"
              pathLength="100"
              d="M16 132C76 48 178 26 270 54"
              stroke-linecap="round"
            />
            <circle class="dot" cx="16" cy="132" r="6" />
            <g class="pin">
              <path d="M270 32a15 15 0 0 1 15 15c0 11-15 26-15 26s-15-15-15-26a15 15 0 0 1 15-15Z" />
              <circle cx="270" cy="47" r="5" />
            </g>
          </svg>
        </div>

        <h1 class="hero-title wy-display">
          <span v-for="(chars, line) in TITLE_CHARS" :key="line" class="title-line">
            <span
              v-for="item in chars"
              :key="item.index"
              class="title-ch"
              :style="{ '--i': item.index }"
              >{{ item.ch }}</span
            >
          </span>
        </h1>
        <p class="hero-sub" :style="{ animationDelay: subDelay }">规划行程 · 安排地点 · 记录沿途</p>

        <div class="hero-cta">
          <el-button type="primary" size="large" @click="$router.push('/register')">
            开始规划
          </el-button>
          <el-button size="large" @click="$router.push('/login')">我已有账号</el-button>
        </div>
      </div>

      <div class="hero-cue" aria-hidden="true"><span /></div>
    </section>

    <!-- 第二/三/四屏：左右结构 + 示例卡，滚动进入时逐项浮起 -->
    <section
      v-for="(feature, index) in FEATURES"
      :key="feature.title"
      :ref="(el) => setPaneRef(el, index)"
      class="pane pane-feature"
      :class="{ 'is-in': revealed[index], 'is-flipped': index % 2 === 1 }"
    >
      <div class="feature-stage wy-container">
        <div class="feature-copy">
          <span class="feature-step wy-num">{{ String(index + 1).padStart(2, '0') }}</span>
          <!-- 三个特性各有一套专属图标动画（滚动进入时播放，之后保留极轻微持续动画） -->
          <span class="feature-icon">
            <!-- 01 行程规划：罗盘外圈描出 → 指针从 -150° 摆入找北 → 缓慢微摆 -->
            <svg
              v-if="index === 0"
              class="icon-anim"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path
                class="ic-ring"
                pathLength="100"
                d="M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z"
              />
              <g class="ic-spin ic-needle">
                <g class="ic-spin ic-sway">
                  <path d="m15.5 8.5-2.2 5.3-5.3 2.2 2.2-5.3 5.3-2.2Z" />
                </g>
              </g>
            </svg>

            <!-- 02 日历与地图：日历描出 → 三个"行程日"依次弹亮 → 循环推进 -->
            <svg
              v-else-if="index === 1"
              class="icon-anim"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path class="ic-cal-top" d="M8 2v4" />
              <path class="ic-cal-top" d="M16 2v4" />
              <path
                class="ic-cal-body"
                pathLength="100"
                d="M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"
              />
              <path class="ic-cal-line" pathLength="100" d="M3 10h18" />
              <rect class="ic-scale ic-day" x="6" y="14.5" width="3" height="3" rx="0.9" />
              <rect class="ic-scale ic-day" x="10.5" y="14.5" width="3" height="3" rx="0.9" />
              <rect class="ic-scale ic-day" x="15" y="14.5" width="3" height="3" rx="0.9" />
            </svg>

            <!-- 03 随心外观：双星转出 → 大星缓慢转动、小星闪烁并轮换主题色 -->
            <svg
              v-else
              class="icon-anim"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.7"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <g class="ic-scale ic-star-big">
                <path d="m12 3 1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3Z" />
              </g>
              <g class="ic-scale ic-star-small">
                <path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15Z" />
              </g>
            </svg>
          </span>
          <h2 class="feature-title wy-display">{{ feature.title }}</h2>
          <p class="feature-desc">{{ feature.desc }}</p>
        </div>

        <!-- 示例卡：装饰性演示（真实令牌配色，不参与交互） -->
        <div class="feature-demo" aria-hidden="true">
          <!-- ① 一天的行程 -->
          <div v-if="index === 0" class="demo-card glass-panel">
            <div class="demo-head">
              <span class="demo-head-title">第 1 天 · 杭州</span>
              <span class="demo-chip">4 个地点</span>
            </div>
            <ul class="demo-plan">
              <li v-for="item in DEMO_PLAN" :key="item.time">
                <span class="demo-time wy-num">{{ item.time }}</span>
                <span class="demo-dot" />
                <span class="demo-place">{{ item.place }}</span>
              </li>
            </ul>
          </div>

          <!-- ② 月视图 -->
          <div v-else-if="index === 1" class="demo-card glass-panel">
            <div class="demo-head">
              <span class="demo-head-title">十月 2026</span>
              <span class="demo-chip">月视图</span>
            </div>
            <div class="demo-week">
              <span v-for="day in DEMO_WEEKDAYS" :key="day">{{ day }}</span>
            </div>
            <div class="demo-days">
              <span
                v-for="day in DEMO_DAYS"
                :key="day"
                class="demo-day wy-num"
                :class="{ 'is-trip': DEMO_TRIP_DAYS.has(day) }"
                >{{ day }}</span
              >
            </div>
          </div>

          <!-- ③ 主题色与背景 -->
          <div v-else class="demo-card glass-panel">
            <div class="demo-head">
              <span class="demo-head-title">主题色</span>
              <span class="demo-chip">翡翠</span>
            </div>
            <div class="demo-swatches">
              <span
                v-for="accent in DEMO_ACCENTS"
                :key="accent.name"
                class="demo-swatch"
                :class="{ 'is-active': accent.name === DEMO_ACTIVE_ACCENT }"
                :style="{ background: accent.color }"
                :title="accent.name"
              />
            </div>
            <div class="demo-head">
              <span class="demo-head-title">背景</span>
            </div>
            <div class="demo-walls">
              <span
                v-for="wall in DEMO_WALLS"
                :key="wall.name"
                class="demo-wall"
                :style="{ background: wall.color }"
                :title="wall.name"
              />
            </div>
          </div>
        </div>
      </div>
    </section>

    <footer class="landing-foot">途笺 Waynote · 让每次出发更从容</footer>
  </div>
</template>

<style scoped>
.landing {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
}

/* 每一屏：占满一屏，内容居中 */
.pane {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  min-height: 100dvh;
  padding: var(--wy-s8) 0;
}

/* ===== 第一屏 ===== */
.hero-top {
  position: absolute;
  inset: 0 0 auto;
  max-width: 1080px;
  margin: 0 auto;
  padding: var(--wy-s5) var(--wy-s4) 0;
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: var(--wy-s2);
}
.brand-name {
  font-size: var(--wy-text-lg);
  color: var(--wy-ink-1);
  letter-spacing: 1px;
}
.brand-en {
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  letter-spacing: 1.5px;
  text-transform: uppercase;
}
.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}
.hero-art svg {
  display: block;
  /* 首屏主视觉：同时受宽度与高度约束，矮屏自动收、大屏给足 */
  width: min(400px, 76vw);
  width: min(400px, 76vw, 46vh);
  height: auto;
  /* 图钉针尖贴路径时钉身略高于视窗，overflow 兜底不裁切 */
  overflow: visible;
}
/* 弧线：与图钉行进同步绘制（pathLength=100 → 按比例精确） */
.route {
  stroke: var(--wy-jade);
  stroke-width: 3;
  stroke-dasharray: 100;
  --route-draw-length: 100;
  animation: wy-draw var(--pn-draw, 1500ms) var(--wy-ease) backwards;
}
.dot {
  fill: var(--wy-primary);
  animation: pin-pop 320ms var(--wy-spring) backwards;
}
/* 图钉：以针尖为跟随点，沿弧线从起点走到终点（offset-distance 100% 即静态位置） */
.pin {
  transform-box: fill-box;
  transform-origin: 50% 100%;
  offset-path: path('M16 132C76 48 178 26 270 54');
  offset-rotate: 0deg;
  offset-distance: 100%;
  animation: pin-travel var(--pn-draw, 1500ms) var(--wy-ease) backwards;
}
.pin path {
  fill: var(--wy-primary);
}
.pin circle {
  fill: var(--wy-surface);
}
@keyframes pin-travel {
  from {
    offset-distance: 0%;
  }
  to {
    offset-distance: 100%;
  }
}
@keyframes pin-pop {
  from {
    opacity: 0;
    transform: scale(0.4);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.hero-title {
  margin: clamp(24px, 3.8vh, 38px) 0 clamp(10px, 1.6vh, 16px);
  font-size: clamp(28px, 5.4vw, 50px);
  font-size: clamp(28px, min(5.4vw, 7vh), 50px);
  line-height: 1.32;
}
.title-line {
  display: block;
}
/* 标题逐字淡入：与图钉行进同步，最后一字完成时图钉刚好抵达 */
.title-ch {
  display: inline-block;
  animation: char-in 520ms var(--wy-ease) backwards;
  animation-delay: calc(var(--pn-text-start, 140ms) + var(--i) * var(--pn-char-step, 62ms));
}
@keyframes char-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.hero-sub {
  margin: 0;
  color: var(--wy-ink-2);
  font-size: clamp(13px, 1vw + 9px, 15px);
  font-size: clamp(13px, min(1vw + 9px, 2.6vh), 15px);
  letter-spacing: 3px;
  animation: char-in 420ms var(--wy-ease) backwards;
}
.hero-cta {
  display: flex;
  justify-content: center;
  gap: var(--wy-s4);
  margin-top: clamp(20px, 3.4vh, 34px);
  /* 图钉抵达后：按钮先淡入 */
  animation: fade-up 420ms var(--wy-ease) backwards;
  animation-delay: var(--pn-cta-delay, 1560ms);
}
.hero-cta :deep(.el-button) {
  height: 46px;
  padding: 0 26px;
  font-size: var(--wy-text-base);
}
@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
/* 下滑提示 */
.hero-cue {
  position: absolute;
  left: 50%;
  bottom: var(--wy-s5);
  width: 1px;
  height: 40px;
  transform: translateX(-50%);
  background: linear-gradient(to bottom, transparent, color-mix(in srgb, var(--wy-jade) 55%, transparent));
  overflow: hidden;
}
.hero-cue span {
  position: absolute;
  left: -1.5px;
  top: 0;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--wy-primary);
  animation: cue-drop 2.6s var(--wy-ease) 2.2s infinite;
}
@keyframes cue-drop {
  0% {
    transform: translateY(-5px);
    opacity: 0;
  }
  25%,
  75% {
    opacity: 1;
  }
  100% {
    transform: translateY(40px);
    opacity: 0;
  }
}

/* ===== 第二/三/四屏：左右结构 ===== */
.feature-stage {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
  align-items: center;
  gap: clamp(28px, 4.5vw, 64px);
  text-align: left;
}
/* 每屏的淡雅翡翠光斑 */
.feature-stage::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: min(720px, 88vw);
  aspect-ratio: 1;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: radial-gradient(
    closest-side,
    color-mix(in srgb, var(--wy-jade) 16%, transparent),
    transparent 72%
  );
  opacity: 0;
  transition: opacity 900ms var(--wy-ease);
  pointer-events: none;
}
/* 单数屏左右对调，形成交错节奏（文字列仍在 DOM 前，移动端堆叠顺序不变） */
.pane-feature.is-flipped .feature-copy {
  order: 2;
}
/* 进入视口后逐项浮起（transition，不会锁死后续 transform） */
.feature-copy > * {
  position: relative;
  opacity: 0;
  transform: translateY(24px);
  transition:
    opacity 560ms var(--wy-ease),
    transform 660ms var(--wy-spring);
}
.feature-copy > *:nth-child(2) {
  transition-delay: 90ms;
}
.feature-copy > *:nth-child(3) {
  transition-delay: 180ms;
}
.feature-copy > *:nth-child(4) {
  transition-delay: 260ms;
}
.feature-demo {
  position: relative;
  opacity: 0;
  transform: translateY(28px);
  /* 示例卡跟在文字之后浮起 */
  transition:
    opacity 620ms var(--wy-ease) 320ms,
    transform 720ms var(--wy-spring) 320ms;
}
.pane-feature.is-in .feature-stage::before {
  opacity: 1;
}
.pane-feature.is-in .feature-copy > *,
.pane-feature.is-in .feature-demo {
  opacity: 1;
  transform: none;
}
.feature-step {
  display: block;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  letter-spacing: 3px;
}
.feature-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  margin-top: var(--wy-s4);
  border-radius: 24px;
  background: var(--wy-primary-weak);
  color: var(--wy-primary-strong);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.7),
    0 12px 28px color-mix(in srgb, var(--wy-jade) 18%, transparent);
}

/* ===== 三个特性图标：各自专属动画（进入视口时播放） ===== */
.icon-anim {
  display: block;
  width: 32px;
  height: 32px;
  overflow: visible;
}
/* 绕图标中心旋转（view-box 坐标系，12px 12px 即中心） */
.ic-spin {
  transform-box: view-box;
  transform-origin: 12px 12px;
}
/* 绕自身包围盒中心缩放（星星/日期格） */
.ic-scale {
  transform-box: fill-box;
  transform-origin: center;
}
/* 公共：沿路径描出（pathLength=100） */
.ic-ring,
.ic-cal-body,
.ic-cal-line {
  stroke-dasharray: 100;
}
.pane-feature.is-in .ic-ring {
  animation: ic-draw 720ms var(--wy-ease) backwards;
}
.pane-feature.is-in .ic-cal-body {
  animation: ic-draw 620ms var(--wy-ease) backwards;
}
.pane-feature.is-in .ic-cal-line {
  animation: ic-draw 420ms var(--wy-ease) 260ms backwards;
}
@keyframes ic-draw {
  from {
    stroke-dashoffset: 100;
    opacity: 0.3;
  }
  to {
    stroke-dashoffset: 0;
    opacity: 1;
  }
}

/* 01 指南针：指针摆入找北 → 之后缓慢微摆 */
.pane-feature.is-in .ic-needle {
  animation: ic-needle-in 1100ms var(--wy-spring) 120ms backwards;
}
@keyframes ic-needle-in {
  from {
    transform: rotate(-150deg);
  }
  to {
    transform: rotate(0deg);
  }
}
/* 持续动画一律不设 fill，保证与入场末帧衔接不跳变 */
.pane-feature.is-in .ic-sway {
  animation: ic-sway 4.2s var(--wy-ease) 1.4s infinite;
}
@keyframes ic-sway {
  0%,
  100% {
    transform: rotate(0deg);
  }
  32% {
    transform: rotate(6deg);
  }
  66% {
    transform: rotate(-4deg);
  }
}

/* 02 日历：挂钩淡入 → 三个"行程日"依次弹亮 → 循环"推进" */
.pane-feature.is-in .ic-cal-top {
  animation: ic-top-in 420ms var(--wy-spring) 80ms backwards;
}
@keyframes ic-top-in {
  from {
    opacity: 0;
    transform: translateY(-2px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
.ic-day {
  fill: currentColor;
  stroke: none;
}
.pane-feature.is-in .ic-day {
  animation:
    ic-day-in 460ms var(--wy-spring) backwards,
    ic-march 3.6s var(--wy-ease) 1.6s infinite;
}
.pane-feature.is-in .ic-day:nth-of-type(2) {
  animation-delay: 130ms, 2.8s;
}
.pane-feature.is-in .ic-day:nth-of-type(3) {
  animation-delay: 260ms, 4s;
}
@keyframes ic-day-in {
  from {
    opacity: 0;
    transform: scale(0.2);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes ic-march {
  0%,
  60%,
  100% {
    opacity: 1;
  }
  20% {
    opacity: 0.35;
  }
}

/* 03 双星：转出 → 大星缓慢转动、小星闪烁 + 主题色轮换 */
.pane-feature.is-in .ic-star-big {
  animation:
    ic-star-in 760ms var(--wy-spring) 80ms backwards,
    ic-twinkle 5.4s var(--wy-ease) 1.3s infinite;
}
.pane-feature.is-in .ic-star-small {
  animation:
    ic-star-in 700ms var(--wy-spring) 300ms backwards,
    ic-twinkle-sm 4.4s var(--wy-ease) 1.5s infinite,
    ic-hue 9s linear 1.5s infinite;
}
@keyframes ic-star-in {
  from {
    opacity: 0;
    transform: rotate(-90deg) scale(0.3);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes ic-twinkle {
  0%,
  100% {
    transform: rotate(0deg) scale(1);
  }
  50% {
    transform: rotate(10deg) scale(1.06);
  }
}
@keyframes ic-twinkle-sm {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  45% {
    opacity: 0.45;
    transform: scale(0.8);
  }
}
/* 小星在真实主题色之间轮换（收尾回到 currentColor，避免主题不符） */
@keyframes ic-hue {
  0%,
  100% {
    stroke: currentColor;
  }
  25% {
    stroke: var(--wy-accent-preset-teal);
  }
  50% {
    stroke: var(--wy-accent-preset-sapphire);
  }
  75% {
    stroke: var(--wy-accent-preset-amethyst);
  }
}
.feature-title {
  margin: var(--wy-s4) 0 var(--wy-s3);
  font-size: clamp(26px, 3.4vw, 40px);
}
.feature-desc {
  margin: 0;
  max-width: 34ch;
  color: var(--wy-ink-2);
  font-size: var(--wy-text-md);
  line-height: 1.7;
}

/* ===== 示例卡（装饰性演示） ===== */
.demo-card {
  width: 100%;
  max-width: 460px;
  padding: var(--wy-s5);
  border-radius: var(--wy-r-md);
  display: grid;
  gap: var(--wy-s3);
}
.demo-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--wy-s3);
}
.demo-head-title {
  color: var(--wy-ink-1);
  font-size: var(--wy-text-base);
  font-weight: 650;
}
.demo-chip {
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--wy-primary-weak);
  color: var(--wy-primary-strong);
  font-size: var(--wy-text-xs);
}
/* ① 一天的行程 */
.demo-plan {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: var(--wy-s2);
}
.demo-plan li {
  display: grid;
  grid-template-columns: 44px 8px minmax(0, 1fr);
  align-items: center;
  gap: var(--wy-s3);
  padding-top: var(--wy-s2);
  border-top: 1px solid color-mix(in srgb, var(--wy-jade) 18%, transparent);
}
.demo-plan li:first-child {
  padding-top: 0;
  border-top: none;
}
.demo-time {
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
}
.demo-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--wy-primary);
}
.demo-place {
  color: var(--wy-ink-1);
  font-size: var(--wy-text-base);
}
/* ② 月视图 */
.demo-week,
.demo-days {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.demo-week span {
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  text-align: center;
}
.demo-day {
  display: grid;
  place-items: center;
  height: 28px;
  border-radius: 9px;
  color: var(--wy-ink-2);
  font-size: var(--wy-text-xs);
}
.demo-day.is-trip {
  background: var(--wy-primary-weak);
  color: var(--wy-primary-strong);
  font-weight: 650;
}
/* ③ 主题色与背景 */
.demo-swatches {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wy-s3);
}
.demo-swatch {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.55);
}
.demo-swatch.is-active {
  box-shadow:
    0 0 0 2px var(--wy-surface),
    0 0 0 4px var(--wy-primary);
}
.demo-walls {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--wy-s2);
}
.demo-wall {
  height: 44px;
  border-radius: 14px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.55);
}

.landing-foot {
  padding: var(--wy-s5) 0 calc(var(--wy-s5) + env(safe-area-inset-bottom));
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  letter-spacing: 1px;
  text-align: center;
}

/* 无障碍：减少动态效果时，跳过整段编排，直接呈现终态 */
@media (prefers-reduced-motion: reduce) {
  .title-ch,
  .hero-sub,
  .hero-cta,
  .dot,
  .pin {
    animation-delay: 0ms !important;
  }
  .pin {
    offset-distance: 100% !important;
  }
  .route {
    stroke-dashoffset: 0 !important;
  }
  .hero-cue {
    display: none;
  }
  .feature-copy > *,
  .feature-demo {
    opacity: 1 !important;
    transform: none !important;
    transition: none !important;
  }
  .feature-stage::before {
    opacity: 1 !important;
    transition: none !important;
  }
}

/* 尺寸全部随视口自适应（min/clamp + vh），不再需要矮屏压缩档 */

/* 窄屏：左右结构改为上下堆叠（文字在上、示例卡在下） */
@media (max-width: 767px) {
  .pane-feature.is-flipped .feature-copy {
    order: 0;
  }
  .feature-stage {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--wy-s6);
    text-align: center;
  }
  .feature-desc {
    margin: 0 auto;
    max-width: 30ch;
  }
}

@media (max-width: 480px) {
  .brand-en {
    display: none;
  }
  .hero-cta {
    flex-direction: column;
  }
  .hero-cta :deep(.el-button + .el-button) {
    margin-left: 0;
  }
  .hero-cue {
    height: 28px;
  }
}
</style>
