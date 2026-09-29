/**
 * 前端错误上报：未捕获异常写入后端统一日志（带指纹去重与会话上限，避免刷日志）。
 * 使用 fetch + keepalive，绕过 axios 拦截器，避免上报失败引发二次提示/循环。
 */
import { createLogger } from '@/utils/logger'

const log = createLogger('report')

const DEDUPE_MS = 60_000
const MAX_PER_SESSION = 20
const MAX_SEEN_KEYS = 200

const seen = new Map<string, number>()
let sentCount = 0

function truncate(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max)}…` : value
}

function normalize(error: unknown): { message: string; stack?: string } {
  if (error instanceof Error) {
    return { message: truncate(error.message || 'unknown error', 500), stack: error.stack }
  }
  if (typeof error === 'string') return { message: truncate(error, 500) }
  try {
    return { message: truncate(JSON.stringify(error) ?? 'unknown error', 500) }
  } catch {
    return { message: 'unserializable error' }
  }
}

export function reportError(
  kind: 'vue' | 'unhandledrejection' | 'window',
  error: unknown,
  extra?: { requestId?: string },
): void {
  try {
    const { message, stack } = normalize(error)
    const key = `${kind}|${message}|${window.location.pathname}`
    const now = Date.now()

    if ((seen.get(key) ?? 0) > now - DEDUPE_MS) return
    if (sentCount >= MAX_PER_SESSION) return
    if (seen.size > MAX_SEEN_KEYS) seen.clear()

    seen.set(key, now)
    sentCount += 1

    const token = localStorage.getItem('access_token')
    const payload = {
      kind,
      message,
      stack: stack ? truncate(stack, 2000) : undefined,
      url: window.location.href.slice(0, 500),
      app_version: import.meta.env.VITE_APP_VERSION ?? 'dev',
      request_id: extra?.requestId,
    }

    void fetch('/api/v1/client-logs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {
      log.debug('错误上报失败（已忽略）')
    })
  } catch {
    // 上报自身的任何异常都必须被吞掉
  }
}
