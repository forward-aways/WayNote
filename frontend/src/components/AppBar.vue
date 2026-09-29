<script setup lang="ts">
/** 顶栏：左上角侧边栏按钮（或返回）+ 品牌；右上角用户信息保持原样 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppIcon from '@/components/AppIcon.vue'
import { useAuthStore } from '@/stores/auth'

withDefaults(defineProps<{ back?: boolean; menu?: boolean; showBrand?: boolean }>(), {
  back: false,
  menu: false,
  showBrand: true,
})
const emit = defineEmits<{ back: []; menu: [] }>()

const auth = useAuthStore()
const router = useRouter()

// 顶栏透明态 / 滚动态：页面顶部完全融入背景，下滑后渐显磨砂玻璃（内容从下方穿过时需要）
const scrolled = ref(false)
let ticking = false

function onScroll() {
  if (ticking) return
  ticking = true
  requestAnimationFrame(() => {
    scrolled.value = window.scrollY > 8
    ticking = false
  })
}

onMounted(() => {
  if (auth.token && !auth.user) auth.fetchMe()
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
})

const avatarChar = computed(() =>
  (auth.user?.name || auth.user?.email || '?').slice(0, 1).toUpperCase(),
)

function onCommand(command: string) {
  if (command !== 'logout') return
  auth.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<template>
  <header class="appbar">
    <span class="appbar-veil liquid-glass" :class="{ visible: scrolled }" aria-hidden="true" />
    <div class="bar-inner wy-container">
      <button
        v-if="back"
        class="icon-btn"
        type="button"
        aria-label="返回"
        @click="emit('back')"
      >
        <AppIcon name="arrow-left" :size="20" />
      </button>
      <button
        v-else-if="menu"
        class="icon-btn"
        type="button"
        aria-label="打开侧边栏"
        @click="emit('menu')"
      >
        <AppIcon name="menu" :size="20" />
      </button>

      <router-link v-if="showBrand" class="brand" to="/trips">
        <span class="brand-seal" aria-hidden="true">途</span>
        <span class="brand-name wy-display">途笺</span>
        <span class="brand-en">Waynote</span>
      </router-link>

      <div class="spacer" />
      <slot name="actions" />

      <el-dropdown v-if="auth.user" trigger="click" @command="onCommand">
        <button class="avatar" type="button" :title="auth.user.name || auth.user.email">
          {{ avatarChar }}
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>{{ auth.user.name || auth.user.email }}</el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <span class="logout-item"><AppIcon name="logout" :size="15" /> 退出登录</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<style scoped>
.appbar {
  position: sticky;
  top: 0;
  z-index: 30;
}
/* 透明态与磨砂态之间用"蒙层渐变"过渡（避免渐变背景硬切） */
.appbar-veil {
  position: absolute;
  inset: 0;
  opacity: 0;
  pointer-events: none;
  transition: opacity 220ms var(--wy-ease);
}
.appbar-veil.visible {
  opacity: 1;
}
.bar-inner {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: var(--wy-s3);
  height: 58px;
}
.brand {
  display: inline-flex;
  align-items: baseline;
  gap: var(--wy-s2);
  color: var(--wy-ink-1);
}
.brand:hover {
  text-decoration: none;
}
.brand-seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 9px;
  background: var(--wy-jade-surface);
  color: var(--wy-on-jade);
  font-size: var(--wy-text-base);
  font-weight: 700;
  line-height: 1;
  box-shadow:
    var(--wy-gem-highlight),
    0 4px 12px rgba(4, 120, 87, 0.3);
}
.brand-name {
  font-size: var(--wy-text-lg);
  letter-spacing: 1px;
}
.brand-en {
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  letter-spacing: 1.5px;
  text-transform: uppercase;
}
.spacer {
  flex: 1;
}
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: var(--wy-r-sm);
  background: rgba(255, 255, 255, 0.5);
  color: var(--wy-ink-1);
  cursor: pointer;
  transition:
    background var(--wy-dur) var(--wy-ease),
    transform var(--wy-dur) var(--wy-spring);
}
.icon-btn:hover {
  background: rgba(255, 255, 255, 0.85);
}
.icon-btn:active {
  transform: scale(0.94);
}
.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: var(--wy-jade-surface);
  color: var(--wy-on-jade);
  font-size: var(--wy-text-sm);
  font-weight: 700;
  box-shadow:
    var(--wy-gem-highlight),
    var(--wy-gem-glow);
  cursor: pointer;
  transition: transform var(--wy-dur) var(--wy-spring);
}
.avatar:hover {
  transform: translateY(-1px);
}
.logout-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
@media (max-width: 480px) {
  .brand-en {
    display: none;
  }
}
</style>
