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
  /** 完成状态（ADR-20261012）：天/整程进度由它派生 */
  done: boolean
  /** 完成时间（仅服务端写入；done=false 时恒为 null） */
  done_at: string | null
  /** 照片 media key（相对标识；展示走 utils/media.ts；见 ADR-20261012 图片篇） */
  photo: string | null
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

export interface PlaceUpdate extends Partial<PlaceCreate> {
  /** 完成状态：省略=不改；显式 null 会被服务端拒绝（422） */
  done?: boolean
  /** 照片 media key：省略=不改；null=清除（服务端校验归属） */
  photo?: string | null
}

export async function updatePlace(
  tripId: number,
  placeId: number,
  data: PlaceUpdate,
): Promise<Place> {
  const res = await http.patch(`/trips/${tripId}/places/${placeId}`, data)
  return res.data
}

export async function deletePlace(tripId: number, placeId: number): Promise<void> {
  await http.delete(`/trips/${tripId}/places/${placeId}`)
}
