import axios from 'axios'
import type { AxiosError } from 'axios'
import { toApiError } from './error'
import { createLogger } from '@/utils/logger'

const log = createLogger('api')

export const http = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** 401 跳转防抖：并发请求只跳一次，且在登录页不重复跳 */
let redirecting = false

function describe(error: unknown): string {
  const config = (error as AxiosError)?.config
  if (!config) return 'request'
  return `${(config.method ?? 'get').toUpperCase()} ${config.url ?? ''}`.trim()
}

http.interceptors.response.use(
  (res) => res,
  (error: unknown) => {
    // 唯一漏斗：归一化 → 分级留痕 → 401 处理；提示文案由调用方经 apiErrorMessage 输出
    const apiError = toApiError(error)
    const where = describe(error)

    if (apiError.isCanceled) {
      log.debug(`${where} 请求已取消`)
    } else if (apiError.isNetwork || apiError.isTimeout) {
      log.error(`${where} ${apiError.detail}`)
    } else if (apiError.status !== null && apiError.status >= 500) {
      log.error(`${where} ${apiError.status} 编号=${apiError.requestId ?? '-'}`, apiError.detail)
    } else {
      log.warn(`${where} ${apiError.status ?? '-'} ${apiError.detail}`)
    }

    if (apiError.status === 401) {
      localStorage.removeItem('access_token')
      if (!redirecting && !window.location.pathname.startsWith('/login')) {
        redirecting = true
        window.location.href = '/login'
      }
    }

    return Promise.reject(apiError)
  },
)
