<script setup lang="ts">
/** 日历：月视图 + 行程标记（点击有行程的日期查看当日安排） */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AppIcon from '@/components/AppIcon.vue'
import FormSheet from '@/components/FormSheet.vue'
import TagChip from '@/components/TagChip.vue'
import { listTrips } from '@/api/trips'
import type { TripListItem } from '@/api/trips'
import { listDays } from '@/api/days'
import type { TripDay } from '@/api/days'
import { destinationPalette, formatDateCN, toDayString, todayString, weekdayCN } from '@/utils/trip'

interface DayEntry {
  trip: TripListItem
  day: TripDay
}

const WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']
const MAX_DOTS = 3

const router = useRouter()
const loading = ref(true)
const trips = ref<TripListItem[]>([])
const entries = ref<DayEntry[]>([])
const cursor = ref(startOfMonth(new Date()))
const selected = ref<string | null>(null)
const sheetOpen = ref(false)

function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

function ymd(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

const monthLabel = computed(() => `${cursor.value.getFullYear()} 年 ${cursor.value.getMonth() + 1} 月`)

const daysMap = computed(() => {
  const map = new Map<string, DayEntry[]>()
  for (const entry of entries.value) {
    const key = toDayString(entry.day.date)
    if (!key) continue
    const list = map.get(key) ?? []
    list.push(entry)
    map.set(key, list)
  }
  return map
})

const grid = computed(() => {
  const year = cursor.value.getFullYear()
  const month = cursor.value.getMonth()
  const offset = (new Date(year, month, 1).getDay() + 6) % 7 // 周一为一周起点
  const start = new Date(year, month, 1 - offset)
  const today = todayString()

  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start.getFullYear(), start.getMonth(), start.getDate() + index)
    const key = ymd(date)
    return {
      key,
      day: date.getDate(),
      inMonth: date.getMonth() === month,
      isToday: key === today,
      entries: daysMap.value.get(key) ?? [],
    }
  })
})

const undatedTrips = computed(() => trips.value.filter((trip) => !toDayString(trip.start_date)))
const selectedEntries = computed(() =>
  selected.value ? (daysMap.value.get(selected.value) ?? []) : [],
)
const selectedLabel = computed(() =>
  selected.value
    ? `${formatDateCN(selected.value)} ${weekdayCN(selected.value)}`
    : '',
)

async function load() {
  loading.value = true
  try {
    trips.value = await listTrips()
    const all = await Promise.all(
      trips.value.map(async (trip) => (await listDays(trip.id)).map((day) => ({ trip, day }))),
    )
    entries.value = all.flat()
  } catch {
    ElMessage.error('加载日历失败')
  } finally {
    loading.value = false
  }
}

function shiftMonth(delta: number) {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + delta, 1)
}

function backToToday() {
  cursor.value = startOfMonth(new Date())
}

function openDay(date: string, hasEntries: boolean) {
  selected.value = date
  if (hasEntries) sheetOpen.value = true
}

function goTrip(id: number) {
  sheetOpen.value = false
  router.push(`/trips/${id}`)
}

onMounted(load)
</script>

<template>
  <main class="wy-container content wy-bottom-safe">
    <header class="cal-head">
      <div>
        <h1 class="page-title wy-display">日历</h1>
        <p class="page-sub">按月查看行程安排</p>
      </div>
      <div class="cal-nav">
        <button class="icon-btn" type="button" aria-label="上个月" @click="shiftMonth(-1)">
          <AppIcon name="chevron-left" :size="18" />
        </button>
        <span class="month-label wy-num">{{ monthLabel }}</span>
        <button class="icon-btn" type="button" aria-label="下个月" @click="shiftMonth(1)">
          <AppIcon name="chevron-right" :size="18" />
        </button>
        <button class="today-btn" type="button" @click="backToToday">回到今天</button>
      </div>
    </header>

    <section class="grid-card glass-panel" v-loading="loading">
      <div class="weekdays">
        <span v-for="label in WEEKDAYS" :key="label">{{ label }}</span>
      </div>
      <div class="grid">
        <button
          v-for="cell in grid"
          :key="cell.key"
          type="button"
          class="cell"
          :class="{
            outside: !cell.inMonth,
            today: cell.isToday,
            selected: selected === cell.key,
            busy: cell.entries.length > 0,
          }"
          @click="openDay(cell.key, cell.entries.length > 0)"
        >
          <span class="cell-day wy-num">{{ cell.day }}</span>
          <span v-if="cell.entries.length" class="dots">
            <span
              v-for="entry in cell.entries.slice(0, MAX_DOTS)"
              :key="entry.day.id"
              class="dot"
              :style="{ background: destinationPalette(entry.trip.destination || entry.trip.title).gradient }"
            />
            <span v-if="cell.entries.length > MAX_DOTS" class="dot-more wy-num">
              +{{ cell.entries.length - MAX_DOTS }}
            </span>
          </span>
        </button>
      </div>
    </section>

    <section v-if="undatedTrips.length" class="undated glass-panel">
      <h2 class="section-title">未定日期</h2>
      <div class="undated-list">
        <button
          v-for="trip in undatedTrips"
          :key="trip.id"
          type="button"
          class="undated-item"
          @click="goTrip(trip.id)"
        >
          <span class="undated-stripe" :style="{ background: destinationPalette(trip.destination || trip.title).gradient }" />
          <span class="undated-name">{{ trip.title }}</span>
          <TagChip text="待定日期" tone="ink" />
        </button>
      </div>
    </section>

    <FormSheet v-model="sheetOpen" :title="selectedLabel">
      <div class="entry-list">
        <button
          v-for="entry in selectedEntries"
          :key="entry.day.id"
          type="button"
          class="entry"
          @click="goTrip(entry.trip.id)"
        >
          <span class="entry-stripe" :style="{ background: destinationPalette(entry.trip.destination || entry.trip.title).gradient }" />
          <span class="entry-main">
            <span class="entry-title">
              {{ entry.trip.title }}
              <TagChip :text="`Day ${entry.day.day_index}`" tone="primary" />
            </span>
            <span class="entry-sub">{{ entry.day.title || '（未命名日程）' }}</span>
          </span>
          <AppIcon name="chevron-right" :size="16" />
        </button>
      </div>
    </FormSheet>
  </main>
</template>

<style scoped>
.content {
  padding-top: var(--wy-s5);
  padding-bottom: var(--wy-s12);
}
.cal-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--wy-s3);
  margin-bottom: var(--wy-s4);
}
.page-title {
  margin: 0;
  font-size: var(--wy-text-xl);
  letter-spacing: 1px;
}
.page-sub {
  margin: var(--wy-s1) 0 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
}
.cal-nav {
  display: flex;
  align-items: center;
  gap: var(--wy-s2);
}
.month-label {
  min-width: 108px;
  color: var(--wy-ink-1);
  font-size: var(--wy-text-base);
  font-weight: 600;
  text-align: center;
}
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--wy-glass-stroke);
  border-radius: var(--wy-r-full);
  background: rgba(255, 255, 255, 0.6);
  color: var(--wy-ink-1);
  cursor: pointer;
  transition: transform var(--wy-dur) var(--wy-spring);
}
.icon-btn:active {
  transform: scale(0.94);
}
.today-btn {
  padding: 7px 14px;
  border: 1px solid var(--wy-glass-stroke);
  border-radius: var(--wy-r-full);
  background: rgba(255, 255, 255, 0.6);
  color: var(--wy-ink-2);
  font-size: var(--wy-text-sm);
  cursor: pointer;
}
.grid-card {
  padding: var(--wy-s4);
  border-radius: var(--wy-r-md);
}
.weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  margin-bottom: var(--wy-s2);
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  text-align: center;
}
.grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.cell {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: 54px;
  border: 1px solid transparent;
  border-radius: var(--wy-r-sm);
  background: transparent;
  color: var(--wy-ink-2);
  cursor: pointer;
  transition:
    background var(--wy-dur) var(--wy-ease),
    border-color var(--wy-dur) var(--wy-ease);
}
.cell:hover {
  background: rgba(255, 255, 255, 0.6);
}
.cell.outside {
  color: var(--wy-ink-3);
  opacity: 0.55;
}
.cell.today {
  border-color: var(--wy-primary);
}
.cell.selected {
  border-color: var(--wy-jade);
  background: rgba(255, 255, 255, 0.75);
}
.cell.busy .cell-day {
  font-weight: 700;
  color: var(--wy-ink-1);
}
.cell-day {
  font-size: var(--wy-text-sm);
}
.dots {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  box-shadow: var(--wy-gem-highlight);
}
.dot-more {
  color: var(--wy-ink-3);
  font-size: 10px;
}
.section-title {
  margin: 0 0 var(--wy-s3);
  font-size: var(--wy-text-md);
}
.undated {
  margin-top: var(--wy-s4);
  padding: var(--wy-s4);
  border-radius: var(--wy-r-md);
}
.undated-list {
  display: flex;
  flex-direction: column;
  gap: var(--wy-s2);
}
.undated-item,
.entry {
  display: flex;
  align-items: center;
  gap: var(--wy-s3);
  width: 100%;
  padding: var(--wy-s3);
  border: none;
  border-radius: var(--wy-r-sm);
  background: rgba(255, 255, 255, 0.55);
  color: var(--wy-ink-1);
  text-align: left;
  cursor: pointer;
  transition: background var(--wy-dur) var(--wy-ease);
}
.undated-item:hover,
.entry:hover {
  background: rgba(255, 255, 255, 0.85);
}
.undated-stripe,
.entry-stripe {
  width: 6px;
  height: 28px;
  border-radius: var(--wy-r-full);
}
.undated-name {
  flex: 1;
  font-weight: 600;
}
.entry-list {
  display: flex;
  flex-direction: column;
  gap: var(--wy-s2);
}
.entry-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
}
.entry-title {
  display: inline-flex;
  align-items: center;
  gap: var(--wy-s2);
  font-weight: 600;
}
.entry-sub {
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
}
</style>
