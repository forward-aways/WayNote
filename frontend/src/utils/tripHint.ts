import type { TripListItem } from '@/api/trips'

/**
 * 列表 → 详情的一次性数据接力（模块级，不入持久化 store）。
 *
 * 目的：从概览点卡片进详情时，首帧就能渲染标题/日期/计数，
 * 避免"空白 + 加载遮罩"造成的白闪割裂感。
 * 详情页仍会后台刷新，数据始终以接口为准；仅命中同一 id 时生效。
 */
let hint: TripListItem | null = null

export function rememberTripHint(trip: TripListItem) {
  hint = trip
}

export function recallTripHint(id: number): TripListItem | null {
  return hint && hint.id === id ? hint : null
}
