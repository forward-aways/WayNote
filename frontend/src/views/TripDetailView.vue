<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppBar from '@/components/AppBar.vue'
import AppIcon from '@/components/AppIcon.vue'
import EmptyState from '@/components/EmptyState.vue'
import FormSheet from '@/components/FormSheet.vue'
import SealTag from '@/components/SealTag.vue'
import { deleteTrip, getTrip, updateTrip } from '@/api/trips'
import type { Trip } from '@/api/trips'
import { createDay, deleteDay, listDays, updateDay } from '@/api/days'
import type { TripDay } from '@/api/days'
import { createPlace, deletePlace, listPlaces, updatePlace } from '@/api/places'
import type { Place } from '@/api/places'
import {
  PHASE_LABEL,
  PHASE_TONE,
  addDays,
  countdownText,
  diffDays,
  formatDateCN,
  formatDateRange,
  tencentMapUrl,
  timeText,
  toDayString,
  tripDayCount,
  tripPhase,
  weekdayCN,
} from '@/utils/trip'
import { apiErrorMessage, apiErrorStatus } from '@/utils/error'

const route = useRoute()
const router = useRouter()
const tripId = computed(() => Number(route.params.id))

const trip = ref<Trip | null>(null)
const days = ref<TripDay[]>([])
const places = ref<Place[]>([])
const loading = ref(true)
const generating = ref(false)

const phase = computed(() => (trip.value ? tripPhase(trip.value) : 'undated'))
const dateText = computed(() =>
  trip.value ? formatDateRange(trip.value.start_date, trip.value.end_date) : '',
)
const countdown = computed(() => (trip.value ? countdownText(trip.value) : ''))
const spanDays = computed(() => (trip.value ? tripDayCount(trip.value) : null))
const unassigned = computed(() => places.value.filter((place) => place.day_id === null))
const statsText = computed(() => `已安排 ${days.value.length} 天 · ${places.value.length} 个地点`)

const placesOfDay = (dayId: number) => places.value.filter((place) => place.day_id === dayId)

const canGenerateDays = computed(
  () => days.value.length === 0 && !!toDayString(trip.value?.start_date) && !!toDayString(trip.value?.end_date),
)

/* ===== 行程表单 ===== */
const tripSheetVisible = ref(false)
const tripSaving = ref(false)
const tripForm = ref({
  title: '',
  destination: '',
  start_date: '',
  end_date: '',
  description: '',
})

function openTripSheet() {
  if (!trip.value) return
  tripForm.value = {
    title: trip.value.title,
    destination: trip.value.destination ?? '',
    start_date: toDayString(trip.value.start_date) ?? '',
    end_date: toDayString(trip.value.end_date) ?? '',
    description: trip.value.description ?? '',
  }
  tripSheetVisible.value = true
}

async function saveTrip() {
  const title = tripForm.value.title.trim()
  if (!title) {
    ElMessage.warning('请填写行程标题')
    return
  }
  if (tripForm.value.start_date && tripForm.value.end_date && tripForm.value.end_date < tripForm.value.start_date) {
    ElMessage.warning('结束日期不能早于开始日期')
    return
  }
  tripSaving.value = true
  try {
    await updateTrip(tripId.value, {
      title,
      destination: tripForm.value.destination.trim() || null,
      start_date: tripForm.value.start_date || null,
      end_date: tripForm.value.end_date || null,
      description: tripForm.value.description.trim() || null,
    })
    ElMessage.success('行程已更新')
    tripSheetVisible.value = false
    await loadAll()
  } catch (error: unknown) {
    ElMessage.error(apiErrorMessage(error, '保存失败'))
  } finally {
    tripSaving.value = false
  }
}

async function removeTrip() {
  if (!trip.value) return
  try {
    await ElMessageBox.confirm(`删除「${trip.value.title}」后，其日程与地点将一并删除且无法恢复。`, '删除行程', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteTrip(tripId.value)
    ElMessage.success('行程已删除')
    router.push('/trips')
  } catch {
    ElMessage.error('删除失败')
  }
}

/* ===== 数据加载 ===== */
async function loadAll() {
  loading.value = true
  try {
    const [t, d, p] = await Promise.all([
      getTrip(tripId.value),
      listDays(tripId.value),
      listPlaces(tripId.value),
    ])
    trip.value = t
    days.value = d
    places.value = p
  } catch (error: unknown) {
    if (apiErrorStatus(error) === 404) {
      ElMessage.error('行程不存在或无权访问')
      router.push('/trips')
      return
    }
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

/* ===== 日程（天） ===== */
const daySheetVisible = ref(false)
const daySaving = ref(false)
const editingDayId = ref<number | null>(null)
const dayForm = ref({ date: '', title: '' })

function openDaySheet(day?: TripDay) {
  if (day) {
    editingDayId.value = day.id
    dayForm.value = { date: toDayString(day.date) ?? '', title: day.title ?? '' }
  } else {
    editingDayId.value = null
    const last = days.value[days.value.length - 1]
    const fallback = toDayString(last?.date) ?? toDayString(trip.value?.start_date) ?? ''
    dayForm.value = { date: fallback ? addDays(fallback, last ? 1 : 0) : '', title: '' }
  }
  daySheetVisible.value = true
}

async function saveDay() {
  if (!dayForm.value.date) {
    ElMessage.warning('请选择日期')
    return
  }
  daySaving.value = true
  try {
    if (editingDayId.value === null) {
      await createDay(tripId.value, {
        date: dayForm.value.date,
        ...(dayForm.value.title.trim() ? { title: dayForm.value.title.trim() } : {}),
      })
      ElMessage.success('已添加一天')
    } else {
      await updateDay(tripId.value, editingDayId.value, {
        date: dayForm.value.date,
        title: dayForm.value.title.trim() || null,
      })
      ElMessage.success('日程已更新')
    }
    daySheetVisible.value = false
    await loadAll()
  } catch (error: unknown) {
    ElMessage.error(apiErrorMessage(error, '保存失败'))
  } finally {
    daySaving.value = false
  }
}

async function removeDay(day: TripDay) {
  try {
    await ElMessageBox.confirm(
      `删除 Day ${day.day_index}（${formatDateCN(day.date)}）？该天地点会保留并移入「待定地点」。`,
      '删除日程',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteDay(tripId.value, day.id)
    ElMessage.success('日程已删除')
    await loadAll()
  } catch {
    ElMessage.error('删除失败')
  }
}

/** 按行程起止日期顺序生成每一天（顺序请求，避免 day_index 竞态） */
async function generateDays() {
  if (!trip.value) return
  const start = toDayString(trip.value.start_date)
  const end = toDayString(trip.value.end_date)
  if (!start || !end) return
  generating.value = true
  try {
    const existing = new Set(days.value.map((day) => toDayString(day.date)))
    const total = diffDays(start, end) + 1
    for (let i = 0; i < total; i++) {
      const date = addDays(start, i)
      if (existing.has(date)) continue
      await createDay(tripId.value, { date })
    }
    ElMessage.success(`已生成 ${total} 天日程`)
    await loadAll()
  } catch (error: unknown) {
    ElMessage.error(apiErrorMessage(error, '生成失败'))
    await loadAll()
  } finally {
    generating.value = false
  }
}

/* ===== 地点 ===== */
const placeSheetVisible = ref(false)
const placeSaving = ref(false)
const editingPlaceId = ref<number | null>(null)
const placeForm = ref({
  name: '',
  day_id: null as number | null,
  address: '',
  category: '',
  start_time: '',
  end_time: '',
  notes: '',
  lat: undefined as number | undefined,
  lng: undefined as number | undefined,
})

/** el-select 的 clear 会给出非数字值，统一归一化为 null（待定） */
function setDayId(value: unknown) {
  placeForm.value.day_id = typeof value === 'number' ? value : null
}

function openPlaceSheet(dayId?: number | null, place?: Place) {
  if (place) {
    editingPlaceId.value = place.id
    placeForm.value = {
      name: place.name,
      day_id: place.day_id,
      address: place.address ?? '',
      category: place.category ?? '',
      start_time: place.start_time ? place.start_time.slice(0, 19) : '',
      end_time: place.end_time ? place.end_time.slice(0, 19) : '',
      notes: place.notes ?? '',
      lat: place.lat ?? undefined,
      lng: place.lng ?? undefined,
    }
  } else {
    editingPlaceId.value = null
    placeForm.value = {
      name: '',
      day_id: dayId ?? null,
      address: '',
      category: '',
      start_time: '',
      end_time: '',
      notes: '',
      lat: undefined,
      lng: undefined,
    }
  }
  placeSheetVisible.value = true
}

async function savePlace() {
  const name = placeForm.value.name.trim()
  if (!name) {
    ElMessage.warning('请填写地点名称')
    return
  }
  if (
    placeForm.value.start_time &&
    placeForm.value.end_time &&
    placeForm.value.end_time < placeForm.value.start_time
  ) {
    ElMessage.warning('结束时间不能早于开始时间')
    return
  }

  const payload = {
    name,
    day_id: placeForm.value.day_id,
    address: placeForm.value.address.trim() || null,
    category: placeForm.value.category.trim() || null,
    start_time: placeForm.value.start_time || null,
    end_time: placeForm.value.end_time || null,
    notes: placeForm.value.notes.trim() || null,
    lat: placeForm.value.lat ?? null,
    lng: placeForm.value.lng ?? null,
  }

  placeSaving.value = true
  try {
    if (editingPlaceId.value === null) {
      await createPlace(tripId.value, payload)
      ElMessage.success('地点已添加')
    } else {
      await updatePlace(tripId.value, editingPlaceId.value, payload)
      ElMessage.success('地点已更新')
    }
    placeSheetVisible.value = false
    await loadAll()
  } catch (error: unknown) {
    ElMessage.error(apiErrorMessage(error, '保存失败'))
  } finally {
    placeSaving.value = false
  }
}

async function removePlace(place: Place) {
  try {
    await ElMessageBox.confirm(`删除地点「${place.name}」？`, '删除地点', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deletePlace(tripId.value, place.id)
    ElMessage.success('地点已删除')
    await loadAll()
  } catch {
    ElMessage.error('删除失败')
  }
}

/** 重排：交换位置后按 10/20/30… 顺序编号，仅提交发生变化的行 */
async function movePlace(list: Place[], index: number, delta: number) {
  const target = index + delta
  if (target < 0 || target >= list.length) return
  const next = [...list]
  const [item] = next.splice(index, 1)
  if (!item) return
  next.splice(target, 0, item)
  try {
    for (let i = 0; i < next.length; i++) {
      const current = next[i]
      if (!current) continue
      const order = (i + 1) * 10
      if (current.sort_order !== order) {
        await updatePlace(tripId.value, current.id, { sort_order: order })
      }
    }
    await loadAll()
  } catch {
    ElMessage.error('调整顺序失败')
  }
}

/** 模板安全的地图链接（无坐标时返回 undefined，配合 v-if 使用） */
function mapHref(place: Place): string | undefined {
  return tencentMapUrl(place) ?? undefined
}

async function assignTo(command: string | number | object, place: Place) {
  const raw = String(command)
  const dayId = raw === 'clear' ? null : Number(raw)
  try {
    await updatePlace(tripId.value, place.id, { day_id: dayId })
    if (dayId === null) {
      ElMessage.success('已移入待定地点')
    } else {
      const day = days.value.find((item) => item.id === dayId)
      ElMessage.success(`已安排到 Day ${day?.day_index ?? ''}`)
    }
    await loadAll()
  } catch {
    ElMessage.error('安排失败')
  }
}

async function copyAddress(place: Place) {
  if (!place.address) return
  try {
    await navigator.clipboard.writeText(place.address)
    ElMessage.success('地址已复制')
  } catch {
    ElMessage.warning('当前浏览器不支持自动复制')
  }
}

onMounted(loadAll)
</script>

<template>
  <div class="page" v-loading="loading">
    <AppBar back @back="router.push('/trips')" />

    <main v-if="trip" class="wy-container content">
      <!-- 行程头部 -->
      <section class="hero wy-card">
        <div class="hero-top">
          <SealTag :text="PHASE_LABEL[phase]" :tone="PHASE_TONE[phase]" :filled="phase === 'ongoing'" size="md" />
          <div class="hero-actions">
            <el-button text @click="openTripSheet">
              <AppIcon name="edit" :size="15" />
              编辑行程
            </el-button>
            <el-dropdown trigger="click" @command="removeTrip">
              <button class="icon-btn" type="button" aria-label="更多操作">
                <AppIcon name="more" :size="18" />
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="remove">
                    <span class="danger-item"><AppIcon name="trash" :size="15" /> 删除行程</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <h1 class="hero-title wy-display">{{ trip.title }}</h1>
        <p class="hero-meta">
          <span v-if="trip.destination"><AppIcon name="pin" :size="14" /> {{ trip.destination }}</span>
          <span><AppIcon name="calendar" :size="14" /> {{ dateText }}</span>
          <span v-if="spanDays" class="wy-num">{{ spanDays }} 天</span>
          <span class="hero-countdown">{{ countdown }}</span>
        </p>
        <p v-if="trip.description" class="hero-desc">{{ trip.description }}</p>
        <p class="hero-stats">{{ statsText }}</p>
      </section>

      <!-- 生成日程引导 -->
      <section v-if="canGenerateDays" class="generate-tip wy-card">
        <p class="generate-text">
          行程共有
          <span class="wy-num">{{ tripDayCount(trip) }}</span>
          天，还是一片空白
        </p>
        <el-button type="primary" :loading="generating" @click="generateDays">
          <AppIcon name="calendar" :size="15" />
          按行程日期生成 {{ tripDayCount(trip) }} 天
        </el-button>
      </section>

      <!-- 时间轴 -->
      <div v-if="days.length" class="timeline">
        <section v-for="day in days" :key="day.id" class="day-block">
          <div class="day-node" aria-hidden="true" />
          <div class="day-card wy-card">
            <header class="day-head">
              <div class="day-title-wrap">
                <span class="day-badge wy-num">{{ day.day_index }}</span>
                <div>
                  <p class="day-date">
                    <span class="wy-num">{{ formatDateCN(day.date) }}</span>
                    <span class="day-week">{{ weekdayCN(day.date) }}</span>
                  </p>
                  <p v-if="day.title" class="day-name wy-display">{{ day.title }}</p>
                </div>
              </div>
              <div class="day-actions">
                <button class="text-btn" type="button" @click="openPlaceSheet(day.id)">
                  <AppIcon name="plus" :size="15" />
                  地点
                </button>
                <button class="icon-btn" type="button" aria-label="编辑这一天" @click="openDaySheet(day)">
                  <AppIcon name="edit" :size="16" />
                </button>
                <button class="icon-btn danger" type="button" aria-label="删除这一天" @click="removeDay(day)">
                  <AppIcon name="trash" :size="16" />
                </button>
              </div>
            </header>

            <div class="place-list">
              <p v-if="placesOfDay(day.id).length === 0" class="place-empty">这一天还没有地点</p>

              <article
                v-for="(place, index) in placesOfDay(day.id)"
                :key="place.id"
                class="place-row"
              >
                <div class="place-main">
                  <div class="place-title-line">
                    <span v-if="timeText(place)" class="time-chip wy-num">{{ timeText(place) }}</span>
                    <span class="place-name">{{ place.name }}</span>
                    <SealTag v-if="place.category" :text="place.category" tone="indigo" />
                  </div>
                  <p v-if="place.address" class="place-sub">
                    <AppIcon name="pin" :size="13" />
                    <span class="place-addr">{{ place.address }}</span>
                    <button class="link-btn" type="button" @click="copyAddress(place)">复制</button>
                    <a
                      v-if="mapHref(place)"
                      class="link-btn"
                      :href="mapHref(place)"
                      target="_blank"
                      rel="noopener"
                    >
                      地图
                    </a>
                  </p>
                  <p v-if="place.notes" class="place-notes">{{ place.notes }}</p>
                </div>
                <div class="place-actions">
                  <button
                    class="icon-btn"
                    type="button"
                    title="上移"
                    :disabled="index === 0"
                    @click="movePlace(placesOfDay(day.id), index, -1)"
                  >
                    <AppIcon name="chevron-up" :size="15" />
                  </button>
                  <button
                    class="icon-btn"
                    type="button"
                    title="下移"
                    :disabled="index === placesOfDay(day.id).length - 1"
                    @click="movePlace(placesOfDay(day.id), index, 1)"
                  >
                    <AppIcon name="chevron-down" :size="15" />
                  </button>
                  <button class="icon-btn" type="button" title="编辑" @click="openPlaceSheet(place.day_id, place)">
                    <AppIcon name="edit" :size="15" />
                  </button>
                  <button class="icon-btn danger" type="button" title="删除" @click="removePlace(place)">
                    <AppIcon name="trash" :size="15" />
                  </button>
                </div>
              </article>
            </div>
          </div>
        </section>
      </div>

      <EmptyState
        v-else-if="!canGenerateDays"
        title="还没有安排日程"
        description="添加一天，或先给行程设置起止日期后一键生成"
      >
        <el-button type="primary" @click="openDaySheet()">
          <AppIcon name="plus" :size="16" />
          添加一天
        </el-button>
      </EmptyState>

      <!-- 待定地点 -->
      <section v-if="unassigned.length" class="pending wy-card">
        <header class="pending-head">
          <div>
            <h2 class="pending-title wy-display">待定地点</h2>
            <p class="pending-sub">还没安排到具体某一天</p>
          </div>
        </header>

        <article v-for="(place, index) in unassigned" :key="place.id" class="place-row">
          <div class="place-main">
            <div class="place-title-line">
              <span class="place-name">{{ place.name }}</span>
              <SealTag v-if="place.category" :text="place.category" tone="indigo" />
            </div>
            <p v-if="place.address" class="place-sub">
              <AppIcon name="pin" :size="13" />
              <span class="place-addr">{{ place.address }}</span>
              <button class="link-btn" type="button" @click="copyAddress(place)">复制</button>
              <a
                v-if="mapHref(place)"
                class="link-btn"
                :href="mapHref(place)"
                target="_blank"
                rel="noopener"
              >
                地图
              </a>
            </p>
            <p v-if="place.notes" class="place-notes">{{ place.notes }}</p>
          </div>
          <div class="place-actions">
            <el-dropdown trigger="click" @command="(command: string | number | object) => assignTo(command, place)">
              <button class="text-btn" type="button">安排到某天</button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-for="day in days" :key="day.id" :command="day.id">
                    Day {{ day.day_index }} · {{ formatDateCN(day.date) }}
                  </el-dropdown-item>
                  <el-dropdown-item v-if="days.length === 0" disabled>暂无日程</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <button
              class="icon-btn"
              type="button"
              title="上移"
              :disabled="index === 0"
              @click="movePlace(unassigned, index, -1)"
            >
              <AppIcon name="chevron-up" :size="15" />
            </button>
            <button
              class="icon-btn"
              type="button"
              title="下移"
              :disabled="index === unassigned.length - 1"
              @click="movePlace(unassigned, index, 1)"
            >
              <AppIcon name="chevron-down" :size="15" />
            </button>
            <button class="icon-btn" type="button" title="编辑" @click="openPlaceSheet(null, place)">
              <AppIcon name="edit" :size="15" />
            </button>
            <button class="icon-btn danger" type="button" title="删除" @click="removePlace(place)">
              <AppIcon name="trash" :size="15" />
            </button>
          </div>
        </article>
      </section>
    </main>

    <button
      v-if="trip"
      class="fab"
      type="button"
      aria-label="添加地点"
      @click="openPlaceSheet(days[0]?.id ?? null)"
    >
      <AppIcon name="plus" :size="24" />
    </button>

    <!-- 行程表单 -->
    <FormSheet v-model="tripSheetVisible" title="编辑行程">
      <el-form label-position="top" @submit.prevent="saveTrip">
        <el-form-item label="标题" required>
          <el-input v-model="tripForm.title" maxlength="100" />
        </el-form-item>
        <el-form-item label="目的地">
          <el-input v-model="tripForm.destination" maxlength="100" placeholder="例如：京都" />
        </el-form-item>
        <div class="form-row">
          <el-form-item label="开始日期">
            <el-date-picker v-model="tripForm.start_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-date-picker v-model="tripForm.end_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
          </el-form-item>
        </div>
        <el-form-item label="描述">
          <el-input v-model="tripForm.description" type="textarea" :rows="3" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="sheet-footer">
          <el-button @click="tripSheetVisible = false">取消</el-button>
          <el-button type="primary" :loading="tripSaving" @click="saveTrip">保存</el-button>
        </div>
      </template>
    </FormSheet>

    <!-- 日程表单 -->
    <FormSheet v-model="daySheetVisible" :title="editingDayId === null ? '添加一天' : '编辑日程'">
      <el-form label-position="top" @submit.prevent="saveDay">
        <el-form-item label="日期" required>
          <el-date-picker v-model="dayForm.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item label="标题（可选）">
          <el-input v-model="dayForm.title" maxlength="100" placeholder="例如：抵达京都 / 岚山一日" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="sheet-footer">
          <el-button @click="daySheetVisible = false">取消</el-button>
          <el-button type="primary" :loading="daySaving" @click="saveDay">
            {{ editingDayId === null ? '添加' : '保存' }}
          </el-button>
        </div>
      </template>
    </FormSheet>

    <!-- 地点表单 -->
    <FormSheet v-model="placeSheetVisible" :title="editingPlaceId === null ? '添加地点' : '编辑地点'">
      <el-form label-position="top" @submit.prevent="savePlace">
        <el-form-item label="名称" required>
          <el-input v-model="placeForm.name" maxlength="100" placeholder="例如：清水寺" />
        </el-form-item>
        <el-form-item label="所属日程">
          <el-select
            :model-value="placeForm.day_id ?? undefined"
            clearable
            placeholder="待定（不安排到具体某天）"
            @update:model-value="setDayId"
          >
            <el-option
              v-for="day in days"
              :key="day.id"
              :label="`Day ${day.day_index} · ${formatDateCN(day.date)}`"
              :value="day.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="placeForm.address" maxlength="255" placeholder="可选" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="placeForm.category" maxlength="50" placeholder="寺庙 / 餐厅 / 酒店…" />
        </el-form-item>
        <div class="form-row">
          <el-form-item label="开始时间">
            <el-date-picker
              v-model="placeForm.start_time"
              type="datetime"
              value-format="YYYY-MM-DDTHH:mm:ss"
              placeholder="可选"
            />
          </el-form-item>
          <el-form-item label="结束时间">
            <el-date-picker
              v-model="placeForm.end_time"
              type="datetime"
              value-format="YYYY-MM-DDTHH:mm:ss"
              placeholder="可选"
            />
          </el-form-item>
        </div>
        <div class="form-row">
          <el-form-item label="纬度（可选）">
            <el-input-number v-model="placeForm.lat" :precision="6" :controls="false" placeholder="35.011600" />
          </el-form-item>
          <el-form-item label="经度（可选）">
            <el-input-number v-model="placeForm.lng" :precision="6" :controls="false" placeholder="135.768100" />
          </el-form-item>
        </div>
        <el-form-item label="备注">
          <el-input v-model="placeForm.notes" type="textarea" :rows="2" maxlength="1000" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="sheet-footer">
          <el-button @click="placeSheetVisible = false">取消</el-button>
          <el-button type="primary" :loading="placeSaving" @click="savePlace">
            {{ editingPlaceId === null ? '添加' : '保存' }}
          </el-button>
        </div>
      </template>
    </FormSheet>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
}
.content {
  padding-top: var(--wy-s6);
  padding-bottom: calc(var(--wy-s12) + 64px);
}

/* 头部 */
.hero {
  padding: var(--wy-s6);
  margin-bottom: var(--wy-s6);
}
.hero-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--wy-s3);
  margin-bottom: var(--wy-s3);
}
.hero-actions {
  display: flex;
  align-items: center;
  gap: var(--wy-s1);
}
.hero-title {
  margin: 0 0 var(--wy-s3);
  font-size: var(--wy-text-xl);
  letter-spacing: 2px;
}
.hero-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--wy-s2) var(--wy-s4);
  margin: 0;
  color: var(--wy-ink-2);
  font-size: var(--wy-text-sm);
}
.hero-meta span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.hero-countdown {
  color: var(--wy-cinnabar);
}
.hero-desc {
  margin: var(--wy-s3) 0 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
}
.hero-stats {
  margin: var(--wy-s3) 0 0;
  padding-top: var(--wy-s3);
  border-top: 1px dashed var(--wy-line-strong);
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  letter-spacing: 0.5px;
}

/* 生成日程提示 */
.generate-tip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--wy-s3);
  padding: var(--wy-s4) var(--wy-s6);
  margin-bottom: var(--wy-s6);
  border-style: dashed;
  background: var(--wy-paper-card);
}
.generate-text {
  margin: 0;
  color: var(--wy-ink-2);
  font-size: var(--wy-text-sm);
}

/* 时间轴 */
.timeline {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--wy-s5);
  margin-bottom: var(--wy-s6);
}
.timeline::before {
  content: '';
  position: absolute;
  left: 11px;
  top: 12px;
  bottom: 12px;
  border-left: 2px dashed var(--wy-line-strong);
}
.day-block {
  position: relative;
  padding-left: 40px;
}
.day-node {
  position: absolute;
  left: 4px;
  top: 16px;
  width: 16px;
  height: 16px;
  border: 2px solid var(--wy-cinnabar);
  border-radius: 50%;
  background: var(--wy-paper-bg);
}
.day-card {
  padding: var(--wy-s4) var(--wy-s5);
}
.day-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--wy-s3);
  padding-bottom: var(--wy-s3);
  border-bottom: 1px dashed var(--wy-line-strong);
  margin-bottom: var(--wy-s3);
}
.day-title-wrap {
  display: flex;
  align-items: center;
  gap: var(--wy-s3);
}
.day-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 34px;
  height: 34px;
  padding: 0 6px;
  border: 1.5px solid var(--wy-cinnabar);
  border-radius: var(--wy-r-sm);
  color: var(--wy-cinnabar);
  font-size: var(--wy-text-md);
  transform: rotate(-2deg);
}
.day-date {
  margin: 0;
  color: var(--wy-ink-1);
  font-size: var(--wy-text-base);
  font-weight: 600;
}
.day-week {
  margin-left: 6px;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
  font-weight: 400;
}
.day-name {
  margin: 2px 0 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
  letter-spacing: 1px;
}
.day-actions {
  display: flex;
  align-items: center;
  gap: var(--wy-s1);
  flex-shrink: 0;
}

/* 地点行 */
.place-list {
  display: flex;
  flex-direction: column;
  gap: var(--wy-s2);
}
.place-empty {
  margin: 0;
  padding: var(--wy-s3) 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
}
.place-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--wy-s3);
  padding: var(--wy-s3);
  border-radius: var(--wy-r-sm);
  transition: background var(--wy-dur) var(--wy-ease);
}
.place-row:hover {
  background: var(--wy-paper-sunken);
}
.place-main {
  min-width: 0;
  flex: 1;
}
.place-title-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--wy-s2);
}
.place-name {
  color: var(--wy-ink-1);
  font-size: var(--wy-text-base);
  font-weight: 600;
}
.time-chip {
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--wy-indigo-weak);
  color: var(--wy-indigo);
  font-size: var(--wy-text-xs);
}
.place-sub {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin: 4px 0 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
}
.place-addr {
  overflow-wrap: anywhere;
}
.place-notes {
  margin: 6px 0 0;
  padding: 6px 10px;
  border-left: 2px solid var(--wy-line-strong);
  color: var(--wy-ink-2);
  font-size: var(--wy-text-xs);
  white-space: pre-wrap;
}
.place-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}

/* 通用小按钮 */
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: var(--wy-r-sm);
  background: transparent;
  color: var(--wy-ink-3);
  cursor: pointer;
  transition: all var(--wy-dur) var(--wy-ease);
}
.icon-btn:hover:not(:disabled) {
  background: var(--wy-paper-sunken);
  color: var(--wy-ink-1);
}
.icon-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.icon-btn.danger:hover:not(:disabled) {
  background: color-mix(in srgb, var(--el-color-danger) 10%, transparent);
  color: var(--el-color-danger);
}
.text-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border: 1px solid var(--wy-line);
  border-radius: var(--wy-r-sm);
  background: transparent;
  color: var(--wy-ink-2);
  font-size: var(--wy-text-xs);
  cursor: pointer;
  transition: all var(--wy-dur) var(--wy-ease);
}
.text-btn:hover {
  border-color: var(--wy-cinnabar);
  color: var(--wy-cinnabar);
}
.link-btn {
  padding: 0;
  border: none;
  background: none;
  color: var(--wy-indigo);
  font-size: var(--wy-text-xs);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.danger-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--el-color-danger);
}

/* 待定地点 */
.pending {
  padding: var(--wy-s4) var(--wy-s5);
  border-style: dashed;
  margin-bottom: var(--wy-s6);
}
.pending-head {
  margin-bottom: var(--wy-s2);
}
.pending-title {
  margin: 0;
  font-size: var(--wy-text-md);
  letter-spacing: 1px;
}
.pending-sub {
  margin: 2px 0 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
}

/* 表单 */
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--wy-s3);
}
.form-row :deep(.el-date-editor),
.form-row :deep(.el-input-number) {
  width: 100%;
}
.sheet-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--wy-s2);
}

/* FAB */
.fab {
  position: fixed;
  right: var(--wy-s4);
  bottom: calc(var(--wy-s6) + env(safe-area-inset-bottom));
  z-index: 30;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border: none;
  border-radius: 50%;
  background: var(--wy-cinnabar);
  color: var(--wy-paper-card);
  box-shadow: var(--wy-shadow-2);
  cursor: pointer;
  transition: transform var(--wy-dur) var(--wy-ease);
}
.fab:active {
  transform: scale(0.94);
}
@media (min-width: 768px) {
  .fab {
    display: none;
  }
}
@media (max-width: 767px) {
  .hero {
    padding: var(--wy-s4);
  }
  .day-head {
    flex-direction: column;
  }
  .place-row {
    flex-direction: column;
  }
  .place-actions {
    align-self: flex-end;
  }
  .form-row {
    grid-template-columns: 1fr;
    gap: 0;
  }
  .generate-tip {
    padding: var(--wy-s4);
  }
}
</style>
