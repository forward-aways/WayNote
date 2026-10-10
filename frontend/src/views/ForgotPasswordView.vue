<script setup lang="ts">
/** 找回密码：邮箱验证码 → 设置新密码（设计见 .deepcode/ADR-20261009-Waynote-email-code-auth.md） */
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import AuthPanel from '@/components/AuthPanel.vue'
import { sendEmailCode } from '@/api/auth'
import { useCountdown } from '@/composables/useCountdown'
import { useAuthStore } from '@/stores/auth'
import { apiErrorMessage } from '@/utils/error'

const auth = useAuthStore()
const { seconds, start: startCountdown } = useCountdown()

const step = ref<1 | 2>(1)
const email = ref('')
const code = ref('')
const password = ref('')
const confirm = ref('')
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
    const result = await sendEmailCode(email.value, 'reset')
    startCountdown(result.cooldown_seconds)
    step.value = 2
    ElMessage.success(result.message)
  } catch (error: unknown) {
    errorMsg.value = apiErrorMessage(error, '验证码发送失败，请稍后重试')
  } finally {
    sending.value = false
  }
}

async function onSubmit() {
  errorMsg.value = ''
  if (!/^\d{6}$/.test(code.value)) {
    errorMsg.value = '请输入 6 位数字验证码'
    return
  }
  if (password.value.length < 6) {
    errorMsg.value = '新密码至少 6 位'
    return
  }
  if (password.value !== confirm.value) {
    errorMsg.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    await auth.doResetPassword(email.value, code.value, password.value)
    ElMessage.success('密码已重置，正在进入…')
    window.location.assign('/trips')
  } catch (error: unknown) {
    errorMsg.value = apiErrorMessage(error, '重置失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthPanel title="找回密码" subtitle="用邮箱验证码重设一个新密码">
    <div class="steps">
      <span class="step" :class="{ 'is-active': step === 1 }">1 验证邮箱</span>
      <span class="step-line" aria-hidden="true" />
      <span class="step" :class="{ 'is-active': step === 2 }">2 设置新密码</span>
    </div>

    <el-form label-position="top" @submit.prevent="step === 1 ? onSendCode() : onSubmit()">
      <el-form-item label="邮箱">
        <el-input
          v-model="email"
          size="large"
          type="email"
          autocomplete="username"
          name="username"
          :disabled="step === 2"
          placeholder="you@example.com"
        />
      </el-form-item>

      <template v-if="step === 2">
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
            <el-button size="large" :disabled="seconds > 0" :loading="sending" @click="onSendCode">
              {{ seconds > 0 ? `重新获取 ${seconds}s` : '重新获取' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="password"
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
            v-model="confirm"
            size="large"
            type="password"
            show-password
            autocomplete="new-password"
            name="confirm-password"
            placeholder="再输一次"
          />
        </el-form-item>
      </template>

      <p v-if="errorMsg" class="form-error" role="alert">{{ errorMsg }}</p>

      <el-button
        v-if="step === 1"
        class="form-submit"
        type="primary"
        size="large"
        native-type="submit"
        :loading="sending"
      >
        发送验证码
      </el-button>
      <el-button
        v-else
        class="form-submit"
        type="primary"
        size="large"
        native-type="submit"
        :loading="loading"
      >
        重置密码
      </el-button>
    </el-form>

    <p class="form-foot"><router-link to="/login">返回登录</router-link></p>
  </AuthPanel>
</template>

<style scoped>
.steps {
  display: flex;
  align-items: center;
  gap: var(--wy-s2);
  margin-bottom: var(--wy-s5);
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  letter-spacing: 1px;
}
.step {
  transition: color var(--wy-dur) var(--wy-ease);
}
.step.is-active {
  color: var(--wy-primary-strong);
  font-weight: 700;
}
.step-line {
  flex: 1;
  height: 1px;
  background: var(--wy-line);
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
.form-submit {
  width: 100%;
  margin-top: var(--wy-s2);
  letter-spacing: 4px;
}
.form-foot {
  margin: var(--wy-s6) 0 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
  text-align: center;
}
</style>
