<script setup lang="ts">
import { ref } from 'vue'
import AuthShell from '@/components/AuthShell.vue'
import { useAuthStore } from '@/stores/auth'
import { apiErrorMessage } from '@/utils/error'

const auth = useAuthStore()

const email = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function onSubmit() {
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
</script>

<template>
  <AuthShell art-title="把旅途，写成一纸手账" art-sub="行程 · 地点 · 备忘 · 记录">
    <h2 class="form-heading wy-display">欢迎回来</h2>

    <el-form label-position="top" @submit.prevent="onSubmit">
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

      <p v-if="errorMsg" class="form-error" role="alert">{{ errorMsg }}</p>

      <el-button
        class="form-submit"
        type="primary"
        size="large"
        native-type="submit"
        :loading="loading"
      >
        登 录
      </el-button>
    </el-form>

    <p class="form-foot">
      还没有账号？<router-link to="/register">去注册</router-link>
    </p>
  </AuthShell>
</template>

<style scoped>
.form-heading {
  margin-bottom: var(--wy-s6);
  font-size: var(--wy-text-xl);
  letter-spacing: 2px;
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
  margin-top: var(--wy-s6);
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
  text-align: center;
}
</style>
