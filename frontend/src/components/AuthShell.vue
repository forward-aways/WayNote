<script setup lang="ts">
/** 登录/注册页共用外壳：左侧品牌画面 + 右侧纸面表单 */
defineProps<{ artTitle: string; artSub: string }>()
</script>

<template>
  <div class="auth">
    <section class="auth-art">
      <div class="art-inner">
        <div class="art-seal wy-display" aria-hidden="true">途笺</div>
        <h1 class="art-title wy-display">{{ artTitle }}</h1>
        <p class="art-sub">{{ artSub }}</p>
        <svg class="art-route" viewBox="0 0 240 96" fill="none" aria-hidden="true">
          <path
            d="M8 78C46 22 108 8 166 24"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-dasharray="5 7"
            stroke-linecap="round"
          />
          <circle cx="8" cy="78" r="4" fill="currentColor" />
          <circle
            class="art-pin"
            cx="166"
            cy="24"
            r="11"
            stroke="currentColor"
            stroke-width="1.6"
            fill="none"
          />
          <circle class="art-pin" cx="166" cy="24" r="4" fill="currentColor" />
        </svg>
      </div>
    </section>

    <section class="auth-panel">
      <div class="panel-card">
        <p class="panel-brand">
          <span class="panel-seal wy-display" aria-hidden="true">途</span>
          途笺 Waynote
        </p>
        <slot />
      </div>
    </section>
  </div>
</template>

<style scoped>
.auth {
  display: grid;
  grid-template-columns: 1fr;
  min-height: 100vh;
}
.auth-art {
  display: none;
}
.auth-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--wy-s6) var(--wy-s4);
}
.panel-card {
  width: 100%;
  max-width: 400px;
}
.panel-brand {
  display: flex;
  align-items: center;
  gap: var(--wy-s2);
  margin-bottom: var(--wy-s6);
  color: var(--wy-ink-2);
  font-size: var(--wy-text-sm);
  letter-spacing: 1px;
}
.panel-seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 1.5px solid var(--wy-cinnabar);
  border-radius: 6px;
  color: var(--wy-cinnabar);
  font-size: var(--wy-text-base);
}

@media (min-width: 900px) {
  .auth {
    grid-template-columns: 1.05fr 1fr;
  }
  .auth-art {
    display: flex;
    align-items: center;
    justify-content: center;
    border-right: 1px solid var(--wy-line);
    background: var(--wy-paper-sunken);
  }
  .art-inner {
    max-width: 360px;
    padding: var(--wy-s8);
  }
  .art-seal {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 72px;
    height: 72px;
    border: 2px solid var(--wy-cinnabar);
    border-radius: var(--wy-r-md);
    color: var(--wy-cinnabar);
    font-size: 30px;
    letter-spacing: 2px;
    transform: rotate(-3deg);
  }
  .art-title {
    margin: var(--wy-s6) 0 var(--wy-s3);
    font-size: var(--wy-text-2xl);
    line-height: 1.5;
    letter-spacing: 2px;
  }
  .art-sub {
    color: var(--wy-ink-3);
    font-size: var(--wy-text-sm);
    letter-spacing: 3px;
  }
  .art-route {
    width: 100%;
    max-width: 240px;
    margin-top: var(--wy-s8);
    color: var(--wy-line-strong);
  }
  .art-pin {
    color: var(--wy-cinnabar);
  }
}
</style>
