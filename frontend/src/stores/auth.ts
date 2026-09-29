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

  async function doRegister(email: string, password: string, name?: string) {
    const data = await authApi.register({ email, password, name })
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

  return { token, user, doLogin, doRegister, fetchMe, logout }
})
