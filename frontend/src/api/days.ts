import { http } from './http'

export interface TripDay {
  id: number
  trip_id: number
  date: string
  day_index: number
  title: string | null
}

export async function listDays(tripId: number): Promise<TripDay[]> {
  const res = await http.get(`/trips/${tripId}/days`)
  return res.data
}

export async function createDay(
  tripId: number,
  data: { date: string; title?: string },
): Promise<TripDay> {
  const res = await http.post(`/trips/${tripId}/days`, data)
  return res.data
}

export async function updateDay(
  tripId: number,
  dayId: number,
  data: { date?: string; title?: string | null },
): Promise<TripDay> {
  const res = await http.patch(`/trips/${tripId}/days/${dayId}`, data)
  return res.data
}

export async function deleteDay(tripId: number, dayId: number): Promise<void> {
  await http.delete(`/trips/${tripId}/days/${dayId}`)
}

export interface DayDoneResult {
  day_id: number
  done: boolean
  /** 实际发生状态迁移的地点行数（重复调用为 0，幂等） */
  changed: number
}

/** 批量完成/取消完成一天（单请求原子；ADR-20261012 §5.3） */
export async function setDayDone(
  tripId: number,
  dayId: number,
  done: boolean,
): Promise<DayDoneResult> {
  const res = await http.patch(`/trips/${tripId}/days/${dayId}/done`, { done })
  return res.data
}
