<script setup lang="ts">
/** 我的：资料 / 统计 / 安全（设置或修改密码）/ 外观设置 / 关于 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppIcon from '@/components/AppIcon.vue'
import FormSheet from '@/components/FormSheet.vue'
import { changePassword, sendEmailCode } from '@/api/auth'
import { listTrips } from '@/api/trips'
import { useCountdown } from '@/composables/useCountdown'
import { useAppearanceStore } from '@/stores/appearance'
import { useAuthStore } from '@/stores/auth'
import { BACKGROUND_PRESETS } from '@/utils/background'
import { apiErrorMessage } from '@/utils/error'
import { formatDateCN } from '@/utils/trip'

const auth = useAuthStore()
const appearance = useAppearanceStore()
const router = useRouter()

const stats = ref({ trips: 0, days: 0, places: 0 })
const loadingStats = ref(true)
const version = import.meta.env.VITE_APP_VERSION ?? 'dev'

const displayName = computed(() => auth.user?.name || auth.user?.email || '旅人')
const avatarChar = computed(() => displayName.value.slice(0, 1).toUpperCase())
const registeredAt = computed(() =>
  auth.user?.created_at ? formatDateCN(auth.user.created_at) : '',
)
const backgroundLabel = computed(() =>
  appearance.isCustomImage
    ? '自定义图片'
    : (BACKGROUND_PRESETS.find((item) => item.id === appearance.presetId)?.name ?? '极光'),
)

async function loadStats() {
  loadingStats.value = true
  try {
    const trips = await listTrips()
    stats.value = {
      trips: trips.length,
      days: trips.reduce((sum, trip) => sum + trip.day_count, 0),
      places: trips.reduce((sum, trip) => sum + trip.place_count, 0),
    }
  } catch {
    // 请求失败已由拦截器记录，这里保持 0 值
  } finally {
    loadingStats.value = false
  }
}

function logout() {
  auth.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}

/* ===== 安全：设置 / 修改密码（有密码用旧密码；免密账号用邮箱验证码，purpose=reset）===== */
const pwOpen = ref(false)
const pwOld = ref('')
const pwCode = ref('')
const pwNew = ref('')
const pwConfirm = ref('')
const pwSaving = ref(false)
const pwSending = ref(false)
const pwError = ref('')
const { seconds: pwSeconds, start: pwStartCountdown } = useCountdown()

const hasPassword = computed(() => auth.user?.has_password === true)
const passwordRowTitle = computed(() => (hasPassword.value ? '修改密码' : '设置密码'))
const passwordRowSub = computed(() =>
  hasPassword.value ? '用当前密码验证后更换' : '用邮箱验证码设置一个新密码',
)

function openPasswordSheet() {
  pwOld.value = ''
  pwCode.value = ''
  pwNew.value = ''
  pwConfirm.value = ''
  pwError.value = ''
  pwOpen.value = true
}

async function onSendPasswordCode() {
  pwError.value = ''
  const email = auth.user?.email
  if (!email) return
  pwSending.value = true
  try {
    const result = await sendEmailCode(email, 'reset')
    pwStartCountdown(result.cooldown_seconds)
    ElMessage.success(result.message)
  } catch (error: unknown) {
    pwError.value = apiErrorMessage(error, '验证码发送失败，请稍后重试')
  } finally {
    pwSending.value = false
  }
}

async function submitPassword() {
  pwError.value = ''
  const hadPassword = hasPassword.value
  if (hadPassword) {
    if (!pwOld.value) {
      pwError.value = '请输入当前密码'
      return
    }
  } else if (!/^\d{6}$/.test(pwCode.value)) {
    pwError.value = '请输入 6 位数字验证码'
    return
  }
  if (pwNew.value.length < 6) {
    pwError.value = '新密码至少 6 位'
    return
  }
  if (pwNew.value !== pwConfirm.value) {
    pwError.value = '两次输入的密码不一致'
    return
  }

  pwSaving.value = true
  try {
    await changePassword(
      hadPassword
        ? { new_password: pwNew.value, old_password: pwOld.value }
        : { new_password: pwNew.value, code: pwCode.value },
    )
    await auth.fetchMe() // 刷新 has_password：设置成功后按钮文案变为「修改密码」
    pwOpen.value = false
    ElMessage.success(hadPassword ? '密码已更新' : '密码已设置')
  } catch (error: unknown) {
    pwError.value = apiErrorMessage(error, '保存失败，请稍后重试')
  } finally {
    pwSaving.value = false
  }
}

onMounted(() => {
  if (!auth.user) auth.fetchMe()
  loadStats()
})
</script>

<template>
  <main class="wy-container content wy-bottom-safe">
    <header class="head">
      <h1 class="page-title wy-display">我的</h1>
    </header>

    <section class="profile glass-panel">
      <span class="avatar" aria-hidden="true">{{ avatarChar }}</span>
      <div class="profile-main">
        <p class="profile-name">{{ displayName }}</p>
        <p class="profile-sub">{{ auth.user?.email || '—' }}</p>
        <p v-if="registeredAt" class="profile-sub">注册于 {{ registeredAt }}</p>
      </div>
    </section>

    <section class="stats glass-panel">
      <!-- 加载中：翡翠骨架占位（不用白色加载遮罩） -->
      <div v-if="loadingStats" class="sk-stats" aria-hidden="true">
        <div v-for="n in 3" :key="n" class="wy-skeleton sk-stat" />
      </div>

      <template v-else>
        <div class="stat">
          <span class="stat-num wy-num">{{ stats.trips }}</span>
          <span class="stat-label">段行程</span>
        </div>
        <div class="stat">
          <span class="stat-num wy-num">{{ stats.days }}</span>
          <span class="stat-label">天日程</span>
        </div>
        <div class="stat">
          <span class="stat-num wy-num">{{ stats.places }}</span>
          <span class="stat-label">个地点</span>
        </div>
      </template>
    </section>

    <section class="rows glass-panel">
      <button type="button" class="row" @click="appearance.sheetOpen = true">
        <span class="row-icon"><AppIcon name="image" :size="17" /></span>
        <span class="row-main">
          <span class="row-title">外观设置</span>
          <span class="row-sub">当前背景：{{ backgroundLabel }}</span>
        </span>
        <AppIcon name="chevron-right" :size="16" />
      </button>
      <div class="row-divider" />
      <div class="row static">
        <span class="row-icon"><AppIcon name="sparkles" :size="17" /></span>
        <span class="row-main">
          <span class="row-title">极光光斑</span>
          <span class="row-sub">缓慢漂移的背景光晕</span>
        </span>
        <el-switch
          :model-value="appearance.aurora"
          @update:model-value="(value: unknown) => appearance.setAurora(Boolean(value))"
        />
      </div>
    </section>

    <section class="rows glass-panel">
      <button type="button" class="row" @click="openPasswordSheet">
        <span class="row-icon"><AppIcon name="user" :size="17" /></span>
        <span class="row-main">
          <span class="row-title">{{ passwordRowTitle }}</span>
          <span class="row-sub">{{ passwordRowSub }}</span>
        </span>
        <AppIcon name="chevron-right" :size="16" />
      </button>
    </section>

    <section class="rows glass-panel">
      <div class="row static">
        <span class="row-icon"><AppIcon name="note" :size="17" /></span>
        <span class="row-main">
          <span class="row-title">版本</span>
          <span class="row-sub">Waynote {{ version }}</span>
        </span>
      </div>
      <div class="row-divider" />
      <a
        class="row"
        href="https://github.com/forward-aways/WayNote"
        target="_blank"
        rel="noopener"
      >
        <span class="row-icon"><AppIcon name="compass" :size="17" /></span>
        <span class="row-main">
          <span class="row-title">开源仓库</span>
          <span class="row-sub">github.com/forward-aways/WayNote</span>
        </span>
        <AppIcon name="chevron-right" :size="16" />
      </a>
    </section>

    <button class="logout" type="button" @click="logout">
      <AppIcon name="logout" :size="16" />
      退出登录
    </button>

    <!-- 设置 / 修改密码：桌面弹窗、移动端抽屉（FormSheet 统一承担两种形态） -->
    <FormSheet v-model="pwOpen" :title="passwordRowTitle">
      <el-form label-position="top" @submit.prevent="submitPassword">
        <el-form-item v-if="hasPassword" label="当前密码">
          <el-input
            v-model="pwOld"
            size="large"
            type="password"
            show-password
            autocomplete="current-password"
            name="current-password"
            placeholder="请输入当前密码"
          />
        </el-form-item>
        <el-form-item v-else label="邮箱验证码">
          <div class="code-row">
            <el-input
              v-model="pwCode"
              size="large"
              inputmode="numeric"
              maxlength="6"
              autocomplete="one-time-code"
              name="code"
              placeholder="6 位数字"
            />
            <el-button
              size="large"
              :disabled="pwSeconds > 0"
              :loading="pwSending"
              @click="onSendPasswordCode"
            >
              {{ pwSeconds > 0 ? `重新获取 ${pwSeconds}s` : '获取验证码' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="pwNew"
            size="large"
            type="password"
            show-password
            autocomplete="new-password"
            name="new-password"
            placeholder="至少 6 位"
          />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input
            v-model="pwConfirm"
            size="large"
            type="password"
            show-password
            autocomplete="new-password"
            name="confirm-password"
            placeholder="再输一次"
          />
        </el-form-item>
        <p v-if="pwError" class="form-error" role="alert">{{ pwError }}</p>
      </el-form>
      <template #footer>
        <el-button size="large" @click="pwOpen = false">取消</el-button>
        <el-button size="large" type="primary" :loading="pwSaving" @click="submitPassword">
          保存
        </el-button>
      </template>
    </FormSheet>
  </main>
</template>

<style scoped>
.content {
  padding-top: var(--wy-s5);
  padding-bottom: var(--wy-s12);
  display: flex;
  flex-direction: column;
  gap: var(--wy-s4);
}
.head {
  margin-bottom: var(--wy-s1);
}
.page-title {
  margin: 0;
  font-size: var(--wy-text-xl);
  letter-spacing: 1px;
}
.profile {
  display: flex;
  align-items: center;
  gap: var(--wy-s4);
  padding: var(--wy-s5);
  border-radius: var(--wy-r-md);
}
.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 20px;
  background: var(--wy-jade-surface);
  color: var(--wy-on-jade);
  font-size: var(--wy-text-lg);
  font-weight: 700;
  box-shadow:
    var(--wy-gem-highlight),
    var(--wy-gem-glow);
  flex-shrink: 0;
}
.profile-main {
  min-width: 0;
}
.profile-name {
  margin: 0;
  color: var(--wy-ink-1);
  font-size: var(--wy-text-md);
  font-weight: 700;
}
.profile-sub {
  margin: 2px 0 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
  overflow-wrap: anywhere;
}
.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  padding: var(--wy-s4);
  border-radius: var(--wy-r-md);
}
.sk-stats {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--wy-s4);
}
.sk-stat {
  height: 52px;
}
.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.stat-num {
  color: var(--wy-primary-strong);
  font-size: var(--wy-text-xl);
  font-weight: 700;
}
.stat-label {
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
}
.rows {
  padding: var(--wy-s1) var(--wy-s2);
  border-radius: var(--wy-r-md);
}
.row {
  display: flex;
  align-items: center;
  gap: var(--wy-s3);
  width: 100%;
  padding: var(--wy-s3);
  border: none;
  border-radius: var(--wy-r-sm);
  background: transparent;
  color: var(--wy-ink-1);
  text-align: left;
  cursor: pointer;
  transition:
    background var(--wy-dur) var(--wy-ease),
    transform var(--wy-dur) var(--wy-spring);
}
.row.static {
  cursor: default;
}
a.row:hover {
  text-decoration: none;
  background: rgba(255, 255, 255, 0.6);
  transform: translateY(-2px);
}
button.row:hover {
  background: rgba(255, 255, 255, 0.6);
  transform: translateY(-2px);
}
a.row:active,
button.row:active {
  transform: translateY(0) scale(0.99);
}
.row-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: var(--wy-primary-weak);
  color: var(--wy-primary-strong);
  flex-shrink: 0;
}
.row-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.row-title {
  font-weight: 600;
}
.row-sub {
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
}
.row-divider {
  height: 1px;
  margin: 0 var(--wy-s3);
  background: var(--wy-line);
}
.logout {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 13px;
  border: 1px solid color-mix(in srgb, var(--el-color-danger) 35%, transparent);
  border-radius: var(--wy-r-md);
  background: color-mix(in srgb, var(--el-color-danger) 8%, rgba(255, 255, 255, 0.6));
  color: var(--el-color-danger);
  font-size: var(--wy-text-base);
  font-weight: 600;
  cursor: pointer;
  transition: transform var(--wy-dur) var(--wy-spring);
}
.logout:active {
  transform: scale(0.98);
}
.code-row {
  display: flex;
  gap: var(--wy-s2);
  width: 100%;
}
.code-row :deep(.el-input) {
  flex: 1;
}
.code-row :deep(.el-button) {
  flex-shrink: 0;
  padding: 0 var(--wy-s4);
}
.form-error {
  margin-bottom: var(--wy-s4);
  padding: var(--wy-s2) var(--wy-s3);
  border: 1px solid color-mix(in srgb, var(--el-color-danger) 30%, transparent);
  border-radius: var(--wy-r-sm);
  background: color-mix(in srgb, var(--el-color-danger) 8%, transparent);
  color: var(--el-color-danger);
  font-size: var(--wy-text-sm);
}
</style>
