import { http } from './http'

export interface User {
  id: number
  email: string
  name: string | null
  created_at: string
  /** 是否已设置密码：验证码登录自动建号的账号为 false（前端据此显示「设置密码」） */
  has_password: boolean
}

/** 验证码用途（与后端 purpose 一一对应，不可混用：见 ADR-20261009 不变量 I4） */
export type EmailCodePurpose = 'login' | 'register' | 'reset'

export interface EmailCodeResult {
  ok: boolean
  cooldown_seconds: number
  ttl_minutes: number
  message: string
}

export async function register(data: {
  email: string
  password: string
  name?: string
  code: string
}) {
  const res = await http.post('/auth/register', data)
  return res.data
}

export async function login(email: string, password: string) {
  const res = await http.post('/auth/login', { email, password })
  return res.data
}

/** 请求邮箱验证码（统一话术：不区分邮箱是否存在） */
export async function sendEmailCode(email: string, purpose: EmailCodePurpose) {
  const res = await http.post<EmailCodeResult>('/auth/email-code', { email, purpose })
  return res.data
}

/** 验证码免密登录（未注册邮箱会自动建号） */
export async function loginWithCode(email: string, code: string) {
  const res = await http.post('/auth/login/email-code', { email, code })
  return res.data
}

/** 找回密码：验证码校验通过后设置新密码（返回令牌，即登录态） */
export async function resetPassword(data: { email: string; code: string; new_password: string }) {
  const res = await http.post('/auth/password/reset', data)
  return res.data
}

/** 已登录改密：有密码用 old_password；免密账号用邮箱验证码（purpose=reset） */
export async function changePassword(data: {
  new_password: string
  old_password?: string
  code?: string
}) {
  const res = await http.post('/auth/password/change', data)
  return res.data
}

export async function getMe(): Promise<User> {
  const res = await http.get('/auth/me')
  return res.data
}
