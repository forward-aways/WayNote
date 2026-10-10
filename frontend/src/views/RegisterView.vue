<script setup lang="ts">
/** 注册：需要邮箱验证码（证明邮箱归属，见 .deepcode/ADR-20261009-Waynote-email-code-auth.md） */
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import AuthPanel from '@/components/AuthPanel.vue'
import { sendEmailCode } from '@/api/auth'
import { useCountdown } from '@/composables/useCountdown'
import { useAuthStore } from '@/stores/auth'
import { apiErrorMessage } from '@/utils/error'

const auth = useAuthStore()
const { seconds, start: startCountdown } = useCountdown()

const email = ref('')
const code = ref('')
const name = ref('')
const password = ref('')
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
    const result = await sendEmailCode(email.value, 'register')
    startCountdown(result.cooldown_seconds)
    ElMessage.success(result.message)
  } catch (error: unknown) {
    errorMsg.value = apiErrorMessage(error, '验证码发送失败，请稍后重试')
  } finally {
    sending.value = false
  }
}

async function onSubmit() {
  errorMsg.value = ''
  if (!email.value || !password.value) {
    errorMsg.value = '请填写邮箱和密码'
    return
  }
  if (!/^\d{6}$/.test(code.value)) {
    errorMsg.value = '请输入 6 位数字验证码'
    return
  }
  if (password.value.length < 6) {
    errorMsg.value = '密码至少 6 位'
    return
  }
  loading.value = true
  try {
    await auth.doRegister(email.value, password.value, name.value || undefined, code.value)
    // 整页跳转：给浏览器密码管理器最强的“注册/登录成功”信号（同 LoginView）
    window.location.assign('/trips')
  } catch (error: unknown) {
    errorMsg.value = apiErrorMessage(error, '注册失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthPanel title="创建账号" subtitle="下一段旅途，从这里开始">
    <el-form label-position="top" @submit.prevent="onSubmit">
      <el-form-item label="邮箱" required>
        <el-input
          v-model="email"
          size="large"
          type="email"
          autocomplete="username"
          name="username"
          placeholder="you@example.com"
        />
      </el-form-item>
      <el-form-item label="邮箱验证码" required>
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
            class="wy-btn-soft"
            size="large"
            :disabled="seconds > 0"
            :loading="sending"
            @click="onSendCode"
          >
            {{ seconds > 0 ? `重新获取 ${seconds}s` : '获取验证码' }}
          </el-button>
        </div>
      </el-form-item>
      <p class="code-hint">先点「获取验证码」，把收到的 6 位数字填进来（10 分钟内有效）</p>
      <el-form-item label="昵称（可选）">
        <el-input
          v-model="name"
          size="large"
          maxlength="50"
          autocomplete="nickname"
          name="nickname"
          placeholder="旅途中怎么称呼你"
        />
      </el-form-item>
      <el-form-item label="密码" required>
        <el-input
          v-model="password"
          size="large"
          type="password"
          show-password
          autocomplete="new-password"
          name="password"
          placeholder="至少 6 位"
        />
      </el-form-item>

      <p v-if="errorMsg" class="form-error" role="alert">{{ errorMsg }}</p>

      <el-button class="form-submit" type="primary" size="large" native-type="submit" :loading="loading">
        注 册
      </el-button>
    </el-form>

    <p class="mode-hint">
      不想设密码？可以直接用「<router-link to="/login?mode=code">验证码登录</router-link>」——没注册过的邮箱会自动建号，之后在「我的」里设置密码即可。
    </p>

    <p class="form-foot">已有账号？<router-link to="/login">去登录</router-link></p>
  </AuthPanel>
</template>

<style scoped>
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
.code-hint {
  margin: calc(var(--wy-s2) * -1) 0 var(--wy-s4);
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  line-height: 1.6;
}
.mode-hint {
  margin: var(--wy-s4) 0 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  line-height: 1.7;
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
