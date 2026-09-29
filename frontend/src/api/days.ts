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
  data: { date: string; title?: string }
): Promise<TripDay> {
  const res = await http.post(`/trips/${tripId}/days`, data)
  return res.data
}

export async function deleteDay(tripId: number, dayId: number): Promise<void> {
  await http.delete(`/trips/${tripId}/days/${dayId}`)
}
