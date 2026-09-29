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

export interface TripCreate {
  title: string
  destination?: string
  start_date?: string
  end_date?: string
  description?: string
}

export async function listTrips(): Promise<Trip[]> {
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

export async function deleteTrip(id: number): Promise<void> {
  await http.delete(`/trips/${id}`)
}
