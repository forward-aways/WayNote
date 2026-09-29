/** 行程日期/状态/展示相关的纯函数工具（无副作用，便于复用与测试） */

export type TripPhase = 'undated' | 'upcoming' | 'ongoing' | 'finished'

export interface DateRangeInput {
  start_date: string | null
  end_date: string | null
}

const DAY_MS = 86_400_000
const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

/** 后端日期为 datetime 序列化（YYYY-MM-DDTHH:mm:ss），统一取本地日期部分 */
export function toDayString(value: string | null | undefined): string | null {
  return value ? value.slice(0, 10) : null
}

export function todayString(): string {
  const now = new Date()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${m}-${d}`
}

/** 两个本地日期字符串相差的天数（to - from），按本地零点解析避免时区偏移 */
export function diffDays(from: string, to: string): number {
  const a = new Date(`${from}T00:00:00`).getTime()
  const b = new Date(`${to}T00:00:00`).getTime()
  return Math.round((b - a) / DAY_MS)
}

export function tripPhase(trip: DateRangeInput, today = todayString()): TripPhase {
  const start = toDayString(trip.start_date)
  if (!start) return 'undated'
  const end = toDayString(trip.end_date) ?? start
  if (today < start) return 'upcoming'
  if (today > end) return 'finished'
  return 'ongoing'
}

export const PHASE_LABEL: Record<TripPhase, string> = {
  undated: '未定日期',
  upcoming: '待出发',
  ongoing: '旅途中',
  finished: '已归档',
}

export const PHASE_TONE: Record<TripPhase, 'primary' | 'sun' | 'ink' | 'gem'> = {
  undated: 'ink',
  upcoming: 'sun',
  ongoing: 'gem',
  finished: 'ink',
}

export function countdownText(trip: DateRangeInput, today = todayString()): string {
  const start = toDayString(trip.start_date)
  if (!start) return '日期待定'
  const end = toDayString(trip.end_date) ?? start
  if (today < start) {
    const n = diffDays(today, start)
    return n === 1 ? '明天出发' : `还有 ${n} 天`
  }
  if (today > end) return '行程已结束'
  return `行程第 ${diffDays(start, today) + 1} 天`
}

/** 行程的起止天数（含首尾）；缺少任一端返回 null */
export function tripDayCount(trip: DateRangeInput): number | null {
  const start = toDayString(trip.start_date)
  const end = toDayString(trip.end_date)
  if (!start || !end) return null
  return diffDays(start, end) + 1
}

/** 本地日期字符串 + N 天 */
export function addDays(day: string, delta: number): string {
  const d = new Date(`${day}T00:00:00`)
  d.setDate(d.getDate() + delta)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${dd}`
}

export function weekdayCN(value: string | null | undefined): string {
  const day = toDayString(value)
  if (!day) return ''
  return `周${WEEKDAYS[new Date(`${day}T00:00:00`).getDay()]}`
}

export function formatDateCN(value: string | null | undefined): string {
  const day = toDayString(value)
  if (!day) return ''
  const [, m, d] = day.split('-')
  return `${Number(m)}月${Number(d)}日`
}

/** 日期范围展示：同月合并、跨年补年份 */
export function formatDateRange(start: string | null, end: string | null): string {
  const s = toDayString(start)
  const e = toDayString(end)
  if (!s && !e) return '日期待定'
  if (s && !e) return formatDateCN(s)
  if (!s || !e) return `至 ${formatDateCN(e)}`

  const [sy = '', sm = '', sd = ''] = s.split('-')
  const [ey = '', em = '', ed = ''] = e.split('-')
  const yearPrefix = (y: string) => (y === String(new Date().getFullYear()) ? '' : `${y}年`)
  if (s === e) return `${yearPrefix(sy)}${Number(sm)}月${Number(sd)}日`
  if (sy === ey && sm === em) {
    return `${yearPrefix(sy)}${Number(sm)}月${Number(sd)}日 – ${Number(ed)}日`
  }
  if (sy === ey) {
    return `${yearPrefix(sy)}${Number(sm)}月${Number(sd)}日 – ${Number(em)}月${Number(ed)}日`
  }
  return `${sy}年${Number(sm)}月${Number(sd)}日 – ${ey}年${Number(em)}月${Number(ed)}日`
}

export interface PlaceTimeInput {
  start_time: string | null
  end_time: string | null
}

/** 地点时间展示：14:00 – 16:00 / 14:00 / 至 16:00 */
export function timeText(place: PlaceTimeInput): string {
  const s = place.start_time ? place.start_time.slice(11, 16) : ''
  const e = place.end_time ? place.end_time.slice(11, 16) : ''
  if (s && e) return `${s} – ${e}`
  if (s) return s
  if (e) return `至 ${e}`
  return ''
}

/** 目的地 → 恒定渐变板（同一名称永远得到同一配色；色值统一来自 tokens.css） */
const PALETTE: readonly { gradient: string; soft: string }[] = [
  { gradient: 'var(--wy-grad-emerald)', soft: 'var(--wy-grad-emerald-weak)' },
  { gradient: 'var(--wy-grad-jade)', soft: 'var(--wy-grad-jade-weak)' },
  { gradient: 'var(--wy-grad-sapphire)', soft: 'var(--wy-grad-sapphire-weak)' },
  { gradient: 'var(--wy-grad-amber)', soft: 'var(--wy-grad-amber-weak)' },
  { gradient: 'var(--wy-grad-peridot)', soft: 'var(--wy-grad-peridot-weak)' },
  { gradient: 'var(--wy-grad-amethyst)', soft: 'var(--wy-grad-amethyst-weak)' },
]

const FALLBACK_COLOR = { gradient: 'var(--wy-grad-brand)', soft: 'var(--wy-primary-weak)' }

export function destinationPalette(name: string | null | undefined): {
  gradient: string
  soft: string
} {
  const key = (name ?? '').trim() || '未命名'
  let hash = 0
  for (const ch of key) {
    hash = (hash * 31 + (ch.codePointAt(0) ?? 0)) % 997
  }
  return PALETTE[hash % PALETTE.length] ?? FALLBACK_COLOR
}

/** 腾讯地图 URI（无需 key）。仅在有坐标时可用 */
export function tencentMapUrl(place: {
  name: string
  lat: number | null
  lng: number | null
}): string | null {
  if (place.lat === null || place.lng === null) return null
  const title = encodeURIComponent(place.name)
  return `https://apis.map.qq.com/uri/v1/marker?marker=coord:${place.lat},${place.lng};title:${title}&referer=waynote`
}
