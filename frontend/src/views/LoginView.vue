<script setup lang="ts">
/** 登录：密码 / 验证码双通道（验证码通道见 .deepcode/ADR-20261009-Waynote-email-code-auth.md） */
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import AuthPanel from '@/components/AuthPanel.vue'
import { sendEmailCode } from '@/api/auth'
import { useCountdown } from '@/composables/useCountdown'
import { useAuthStore } from '@/stores/auth'
import { apiErrorMessage } from '@/utils/error'

const auth = useAuthStore()
const { seconds, start: startCountdown } = useCountdown()

const mode = ref<'password' | 'code'>('password')

const email = ref('')
const password = ref('')
const code = ref('')
const loading = ref(false)
const sending = ref(false)
const errorMsg = ref('')

async function onSendCode() {
  errorMsg.value = ''
  if (!email.value) {
    errorMsg.value = '请先填写邮箱'
    return
  }
  sending.value = true
  try {
    const result = await sendEmailCode(email.value, 'login')
    startCountdown(result.cooldown_seconds)
    ElMessage.success(result.message)
  } catch (error: unknown) {
    errorMsg.value = apiErrorMessage(error, '验证码发送失败，请稍后重试')
  } finally {
    sending.value = false
  }
}

async function onSubmitPassword() {
  errorMsg.value = ''
  if (!email.value || !password.value) {
    errorMsg.value = '请填写邮箱和密码'
    return
  }
  loading.value = true
  try {
    await auth.doLogin(email.value, password.value)
    // 整页跳转：给浏览器密码管理器最强的“登录成功”信号，并彻底重置内存状态
    // （见 .deepcode/ADR-20260929-Waynote-password-manager-friendly-login.md）
    window.location.assign('/trips')
  } catch (error: unknown) {
    errorMsg.value = apiErrorMessage(error, '登录失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function onSubmitCode() {
  errorMsg.value = ''
  if (!email.value) {
    errorMsg.value = '请填写邮箱'
    return
  }
  if (!/^\d{6}$/.test(code.value)) {
    errorMsg.value = '请输入 6 位数字验证码'
    return
  }
  loading.value = true
  try {
    await auth.doLoginWithCode(email.value, code.value)
    window.location.assign('/trips')
  } catch (error: unknown) {
    errorMsg.value = apiErrorMessage(error, '登录失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthPanel title="欢迎回来" subtitle="登录后继续你的行程">
    <div class="mode-switch">
      <button
        type="button"
        class="mode-btn"
        :class="{ 'is-active': mode === 'password' }"
        @click="mode = 'password'"
      >
        密码登录
      </button>
      <button
        type="button"
        class="mode-btn"
        :class="{ 'is-active': mode === 'code' }"
        @click="mode = 'code'"
      >
        验证码登录
      </button>
    </div>

    <el-form v-if="mode === 'password'" label-position="top" @submit.prevent="onSubmitPassword">
      <el-form-item label="邮箱">
        <el-input
          v-model="email"
          size="large"
          type="email"
          autocomplete="username"
          name="username"
          placeholder="you@example.com"
        />
      </el-form-item>
      <el-form-item label="密码">
        <el-input
          v-model="password"
          size="large"
          type="password"
          show-password
          autocomplete="current-password"
          name="password"
          placeholder="请输入密码"
        />
      </el-form-item>

      <p class="forgot-row"><router-link to="/forgot">忘记密码？</router-link></p>

      <p v-if="errorMsg" class="form-error" role="alert">{{ errorMsg }}</p>

      <el-button class="form-submit" type="primary" size="large" native-type="submit" :loading="loading">
        登 录
      </el-button>
    </el-form>

    <el-form v-else label-position="top" @submit.prevent="onSubmitCode">
      <el-form-item label="邮箱">
        <el-input
          v-model="email"
          size="large"
          type="email"
          autocomplete="username"
          name="username"
          placeholder="you@example.com"
        />
      </el-form-item>
      <el-form-item label="验证码">
        <div class="code-row">
          <el-input
            v-model="code"
            size="large"
            inputmode="numeric"
            maxlength="6"
            autocomplete="one-time-code"
            name="code"
            placeholder="6 位数字"
          />
          <el-button
            size="large"
            :disabled="seconds > 0"
            :loading="sending"
            @click="onSendCode"
          >
            {{ seconds > 0 ? `重新获取 ${seconds}s` : '获取验证码' }}
          </el-button>
        </div>
      </el-form-item>

      <p v-if="errorMsg" class="form-error" role="alert">{{ errorMsg }}</p>

      <el-button class="form-submit" type="primary" size="large" native-type="submit" :loading="loading">
        登 录
      </el-button>

      <p class="mode-hint">没注册过的邮箱会自动创建账号（之后可在「我的」里设置密码）</p>
    </el-form>

    <p class="form-foot">
      还没有账号？<router-link to="/register">去注册</router-link>
    </p>
  </AuthPanel>
</template>

<style scoped>
.mode-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  margin-bottom: var(--wy-s5);
  padding: 4px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--wy-accent-base) 8%, rgba(255, 255, 255, 0.6));
}
.mode-btn {
  padding: 9px 0;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: var(--wy-ink-2);
  font-size: var(--wy-text-sm);
  font-weight: 600;
  cursor: pointer;
  transition:
    background var(--wy-dur) var(--wy-ease),
    color var(--wy-dur) var(--wy-ease);
}
.mode-btn.is-active {
  /* 宝石面 + 墨色文字：与全站主按钮同一套对比度保障 */
  background: var(--wy-jade-surface);
  background-origin: border-box;
  color: var(--wy-on-jade);
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
.forgot-row {
  margin: calc(var(--wy-s1) * -1) 0 var(--wy-s3);
  text-align: right;
  font-size: var(--wy-text-sm);
}
.mode-hint {
  margin: var(--wy-s3) 0 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  line-height: 1.6;
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
.form-submit {
  width: 100%;
  margin-top: var(--wy-s2);
  letter-spacing: 6px;
}
.form-foot {
  margin: var(--wy-s6) 0 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
  text-align: center;
}
</style>
