/** 后端错误信息的类型安全提取（避免在视图中使用 any） */

interface ApiErrorShape {
  response?: {
    status?: number
    data?: { detail?: unknown }
  }
}

export function apiErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as ApiErrorShape)?.response?.data?.detail
  return typeof detail === 'string' && detail ? detail : fallback
}

export function apiErrorStatus(error: unknown): number | undefined {
  return (error as ApiErrorShape)?.response?.status
}
