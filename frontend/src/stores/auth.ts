import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as authApi from '@/api/auth'
import type { User } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<User | null>(null)

  async function doLogin(email: string, password: string) {
    const data = await authApi.login(email, password)
    token.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
    await fetchMe()
  }

  /** 验证码登录（未注册邮箱自动建号，见 ADR-20261009 §6.5） */
  async function doLoginWithCode(email: string, code: string) {
    const data = await authApi.loginWithCode(email, code)
    token.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
    await fetchMe()
  }

  async function doRegister(email: string, password: string, name?: string, code?: string) {
    const data = await authApi.register({ email, password, name, code: code ?? '' })
    token.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
    await fetchMe()
  }

  /** 找回密码：重置成功后直接进入登录态 */
  async function doResetPassword(email: string, code: string, newPassword: string) {
    const data = await authApi.resetPassword({ email, code, new_password: newPassword })
    token.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
    await fetchMe()
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      user.value = await authApi.getMe()
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
  }

  return { token, user, doLogin, doLoginWithCode, doRegister, doResetPassword, fetchMe, logout }
})
