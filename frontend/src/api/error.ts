/** 前端统一错误模型：所有请求失败最终都归一到 ApiError（分类/追踪/文案的唯一来源） */
import type { AxiosError } from 'axios'

interface ErrorBody {
  detail?: unknown
  request_id?: unknown
  code?: unknown
}

export class ApiError extends Error {
  readonly status: number | null
  readonly detail: string
  readonly requestId: string | null
  readonly isNetwork: boolean
  readonly isTimeout: boolean
  readonly isCanceled: boolean

  constructor(init: {
    detail: string
    status: number | null
    requestId: string | null
    isNetwork: boolean
    isTimeout: boolean
    isCanceled: boolean
  }) {
    super(init.detail)
    this.name = 'ApiError'
    this.detail = init.detail
    this.status = init.status
    this.requestId = init.requestId
    this.isNetwork = init.isNetwork
    this.isTimeout = init.isTimeout
    this.isCanceled = init.isCanceled
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError
}

export function toApiError(error: unknown): ApiError {
  const axiosError = error as AxiosError<ErrorBody>
  const response = axiosError?.response
  const data = response?.data
  const rawHeaders = (response?.headers ?? {}) as Record<string, unknown>

  const backendDetail = typeof data?.detail === 'string' && data.detail ? data.detail : ''
  const requestId =
    (typeof data?.request_id === 'string' ? data.request_id : null) ??
    (typeof rawHeaders['x-request-id'] === 'string' ? (rawHeaders['x-request-id'] as string) : null)

  const status = typeof response?.status === 'number' ? response.status : null
  const isCanceled = axiosError?.code === 'ERR_CANCELED'
  const isTimeout = axiosError?.code === 'ECONNABORTED' || axiosError?.code === 'ETIMEDOUT'
  const isNetwork = !response && !isCanceled

  const fallback = isNetwork
    ? isTimeout
      ? '请求超时，请稍后重试'
      : '网络异常，请检查网络连接'
    : status
      ? `请求失败（${status}）`
      : '请求失败'

  return new ApiError({
    detail: backendDetail || fallback,
    status,
    requestId,
    isNetwork,
    isTimeout,
    isCanceled,
  })
}
