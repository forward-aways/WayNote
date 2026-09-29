/** 后端错误信息提取：ApiError 优先；5xx 自动附带请求编号，便于与后端日志对照 */
import { isApiError } from '@/api/error'

interface LegacyApiErrorShape {
  response?: {
    status?: number
    data?: { detail?: unknown }
  }
}

export function apiErrorMessage(error: unknown, fallback: string): string {
  if (isApiError(error)) {
    const message = error.detail || fallback
    if (error.status !== null && error.status >= 500 && error.requestId) {
      return `${message}（编号 ${error.requestId.slice(-8)}）`
    }
    return message
  }
  const detail = (error as LegacyApiErrorShape)?.response?.data?.detail
  return typeof detail === 'string' && detail ? detail : fallback
}

export function apiErrorStatus(error: unknown): number | undefined {
  if (isApiError(error)) return error.status ?? undefined
  return (error as LegacyApiErrorShape)?.response?.status
}
