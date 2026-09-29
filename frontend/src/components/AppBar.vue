<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppIcon from '@/components/AppIcon.vue'
import { useAuthStore } from '@/stores/auth'

withDefaults(defineProps<{ back?: boolean }>(), { back: false })
const emit = defineEmits<{ back: [] }>()

const auth = useAuthStore()
const router = useRouter()

// 刷新后恢复用户信息（AppBar 在所有登录后页面复用，集中处理）
onMounted(() => {
  if (auth.token && !auth.user) auth.fetchMe()
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
    <div class="bar-inner wy-container">
      <button v-if="back" class="icon-btn" type="button" aria-label="返回" @click="emit('back')">
        <AppIcon name="arrow-left" :size="20" />
      </button>
      <router-link class="brand" to="/trips">
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
  z-index: 20;
  border-bottom: 1px solid var(--wy-line);
  background: color-mix(in srgb, var(--wy-paper-bg) 86%, transparent);
  backdrop-filter: blur(8px);
}
.bar-inner {
  display: flex;
  align-items: center;
  gap: var(--wy-s3);
  height: 56px;
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
  width: 26px;
  height: 26px;
  border: 1.5px solid var(--wy-cinnabar);
  border-radius: 6px;
  color: var(--wy-cinnabar);
  font-family: var(--wy-font-display);
  font-size: var(--wy-text-md);
  line-height: 1;
  transform: translateY(3px);
}
.brand-name {
  font-size: var(--wy-text-lg);
  letter-spacing: 2px;
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
  width: 34px;
  height: 34px;
  border: 1px solid transparent;
  border-radius: var(--wy-r-sm);
  background: transparent;
  color: var(--wy-ink-2);
  cursor: pointer;
  transition: all var(--wy-dur) var(--wy-ease);
}
.icon-btn:hover {
  border-color: var(--wy-line);
  background: var(--wy-paper-card);
}
.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--wy-line-strong);
  border-radius: 50%;
  background: var(--wy-paper-card);
  color: var(--wy-cinnabar);
  font-size: var(--wy-text-sm);
  font-weight: 600;
  cursor: pointer;
  transition: box-shadow var(--wy-dur) var(--wy-ease);
}
.avatar:hover {
  box-shadow: var(--wy-shadow-1);
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
