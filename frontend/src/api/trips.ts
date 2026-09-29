import { http } from './http'

export interface Trip {
  id: number
  title: string
  destination: string | null
  start_date: string | null
  end_date: string | null
  cover: string | null
  description: string | null
  status: string
  created_at: string
}

/** 列表接口附带只读计数 */
export interface TripListItem extends Trip {
  day_count: number
  place_count: number
}

export interface TripCreate {
  title: string
  destination?: string
  start_date?: string
  end_date?: string
  description?: string
}

export async function listTrips(): Promise<TripListItem[]> {
  const res = await http.get('/trips')
  return res.data
}

export async function createTrip(data: TripCreate): Promise<Trip> {
  const res = await http.post('/trips', data)
  return res.data
}

export async function getTrip(id: number): Promise<Trip> {
  const res = await http.get(`/trips/${id}`)
  return res.data
}

export interface TripUpdate {
  title?: string
  destination?: string | null
  start_date?: string | null
  end_date?: string | null
  description?: string | null
  status?: string
}

export async function updateTrip(id: number, data: TripUpdate): Promise<Trip> {
  const res = await http.patch(`/trips/${id}`, data)
  return res.data
}

export async function deleteTrip(id: number): Promise<void> {
  await http.delete(`/trips/${id}`)
}
