import { http } from './http'

export interface Place {
  id: number
  trip_id: number
  day_id: number | null
  name: string
  address: string | null
  lat: number | null
  lng: number | null
  category: string | null
  start_time: string | null
  end_time: string | null
  notes: string | null
  sort_order: number
}

export interface PlaceCreate {
  name: string
  day_id?: number | null
  address?: string | null
  lat?: number | null
  lng?: number | null
  category?: string | null
  start_time?: string | null
  end_time?: string | null
  notes?: string | null
  sort_order?: number
}

export async function listPlaces(tripId: number, dayId?: number): Promise<Place[]> {
  const params = dayId !== undefined ? { day_id: dayId } : {}
  const res = await http.get(`/trips/${tripId}/places`, { params })
  return res.data
}

export async function createPlace(tripId: number, data: PlaceCreate): Promise<Place> {
  const res = await http.post(`/trips/${tripId}/places`, data)
  return res.data
}

export async function updatePlace(
  tripId: number,
  placeId: number,
  data: Partial<PlaceCreate>,
): Promise<Place> {
  const res = await http.patch(`/trips/${tripId}/places/${placeId}`, data)
  return res.data
}

export async function deletePlace(tripId: number, placeId: number): Promise<void> {
  await http.delete(`/trips/${tripId}/places/${placeId}`)
}
