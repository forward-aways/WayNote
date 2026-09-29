<script setup lang="ts">
/** 落地页：灵动起始动画（路径描边 + 落点）+ 特性玻璃卡 + CTA */
import AppIcon from '@/components/AppIcon.vue'

const FEATURES = [
  { icon: 'compass', title: '行程规划', desc: '按天安排地点，时间与备注一目了然' },
  { icon: 'calendar', title: '日历与地图', desc: '月视图纵览行程，坐标地点一键跳转' },
  { icon: 'sparkles', title: '随心外观', desc: '自定义背景与光斑，界面属于你自己' },
] as const
</script>

<template>
  <div class="landing">
    <header class="landing-top wy-container">
      <span class="brand">
        <span class="tile" aria-hidden="true">途</span>
        <span class="brand-name wy-display">途笺</span>
        <span class="brand-en">Waynote</span>
      </span>
    </header>

    <main class="hero wy-container">
      <div class="hero-art" aria-hidden="true">
        <svg viewBox="0 0 320 140" fill="none">
          <path class="route" d="M14 118C74 34 176 12 268 40" stroke-linecap="round" />
          <circle class="dot" cx="14" cy="118" r="6" />
          <g class="pin">
            <path d="M268 18a15 15 0 0 1 15 15c0 11-15 26-15 26s-15-15-15-26a15 15 0 0 1 15-15Z" />
            <circle cx="268" cy="33" r="5" />
          </g>
        </svg>
      </div>

      <h1 class="hero-title wy-display">把想去的地方，<br />变成下一段旅途</h1>
      <p class="hero-sub">规划行程 · 安排地点 · 记录沿途</p>

      <div class="hero-cta">
        <el-button type="primary" size="large" @click="$router.push('/register')">
          开始规划
        </el-button>
        <el-button size="large" @click="$router.push('/login')">我已有账号</el-button>
      </div>

      <div class="features">
        <article
          v-for="(feature, index) in FEATURES"
          :key="feature.title"
          class="feature glass-panel wy-rise"
          :style="{ animationDelay: `${240 + index * 90}ms` }"
        >
          <span class="feature-icon"><AppIcon :name="feature.icon" :size="20" /></span>
          <h2 class="feature-title">{{ feature.title }}</h2>
          <p class="feature-desc">{{ feature.desc }}</p>
        </article>
      </div>
    </main>

    <footer class="landing-foot">途笺 Waynote · 让每次出发更从容</footer>
  </div>
</template>

<style scoped>
.landing {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.landing-top {
  padding-top: var(--wy-s6);
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: var(--wy-s2);
}
.tile {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: var(--wy-jade-surface);
  color: var(--wy-on-jade);
  font-weight: 700;
  box-shadow:
    var(--wy-gem-highlight),
    var(--wy-gem-glow);
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
  flex: 1;
  padding-top: var(--wy-s8);
  padding-bottom: var(--wy-s8);
  text-align: center;
}
.hero-art svg {
  width: min(320px, 78vw);
  height: auto;
}
.route {
  stroke: var(--wy-jade);
  stroke-width: 3;
  stroke-dasharray: 360;
  --route-draw-length: 360;
  animation: wy-draw 1.5s var(--wy-ease) both;
}
.dot {
  fill: var(--wy-primary);
  animation: wy-rise 400ms var(--wy-spring) 900ms both;
}
.pin {
  animation: wy-rise 460ms var(--wy-spring) 1s both;
}
.pin path {
  fill: var(--wy-primary);
}
.pin circle {
  fill: var(--wy-surface);
}
.hero-title {
  margin: var(--wy-s6) 0 var(--wy-s3);
  font-size: clamp(26px, 6vw, 40px);
  line-height: 1.35;
}
.hero-sub {
  margin: 0;
  color: var(--wy-ink-2);
  font-size: var(--wy-text-sm);
  letter-spacing: 3px;
}
.hero-cta {
  display: flex;
  justify-content: center;
  gap: var(--wy-s3);
  margin-top: var(--wy-s6);
}
.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--wy-s4);
  margin-top: var(--wy-s12);
  text-align: left;
}
.feature {
  padding: var(--wy-s5);
  border-radius: var(--wy-r-md);
  transition: transform var(--wy-dur) var(--wy-spring);
}
.feature:hover {
  transform: translateY(-4px);
}
.feature-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: var(--wy-primary-weak);
  color: var(--wy-primary-strong);
}
.feature-title {
  margin: var(--wy-s3) 0 var(--wy-s1);
  font-size: var(--wy-text-md);
}
.feature-desc {
  margin: 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
}
.landing-foot {
  padding: var(--wy-s6) 0 calc(var(--wy-s6) + env(safe-area-inset-bottom));
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  letter-spacing: 1px;
  text-align: center;
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
}
</style>
