<script setup lang="ts">
import { ref } from 'vue'
import AuthPanel from '@/components/AuthPanel.vue'
import { useAuthStore } from '@/stores/auth'
import { apiErrorMessage } from '@/utils/error'

const auth = useAuthStore()

const email = ref('')
const name = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function onSubmit() {
  errorMsg.value = ''
  if (!email.value || !password.value) {
    errorMsg.value = '请填写邮箱和密码'
    return
  }
  if (password.value.length < 6) {
    errorMsg.value = '密码至少 6 位'
    return
  }
  loading.value = true
  try {
    await auth.doRegister(email.value, password.value, name.value || undefined)
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
      <el-form-item label="邮箱">
        <el-input
          v-model="email"
          size="large"
          type="email"
          autocomplete="email"
          name="email"
          placeholder="you@example.com"
        />
      </el-form-item>
      <el-form-item label="昵称（可选）">
        <el-input
          v-model="name"
          size="large"
          autocomplete="nickname"
          name="nickname"
          placeholder="旅途中怎么称呼你"
        />
      </el-form-item>
      <el-form-item label="密码">
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

      <el-button
        class="form-submit"
        type="primary"
        size="large"
        native-type="submit"
        :loading="loading"
      >
        注 册
      </el-button>
    </el-form>

    <p class="form-foot">已有账号？<router-link to="/login">去登录</router-link></p>
  </AuthPanel>
</template>

<style scoped>
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
