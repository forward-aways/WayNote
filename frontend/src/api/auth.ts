import { http } from './http'

export interface User {
  id: number
  email: string
  name: string | null
  created_at: string
}

export async function register(data: { email: string; password: string; name?: string }) {
  const res = await http.post('/auth/register', data)
  return res.data
}

export async function login(email: string, password: string) {
  const res = await http.post('/auth/login', { email, password })
  return res.data
}

export async function getMe(): Promise<User> {
  const res = await http.get('/auth/me')
  return res.data
}
