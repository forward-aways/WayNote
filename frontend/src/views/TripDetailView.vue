<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTrip } from '@/api/trips'
import type { Trip } from '@/api/trips'
import { listDays, createDay, deleteDay } from '@/api/days'
import type { TripDay } from '@/api/days'
import { listPlaces, createPlace, deletePlace } from '@/api/places'
import type { Place } from '@/api/places'

const route = useRoute()
const router = useRouter()
const tripId = computed(() => Number(route.params.id))

const trip = ref<Trip | null>(null)
const days = ref<TripDay[]>([])
const places = ref<Place[]>([])
const loading = ref(false)

const dayDialogVisible = ref(false)
const dayForm = ref({ date: '', title: '' })
const daySubmitting = ref(false)

const placeDialogVisible = ref(false)
const placeForm = ref({
  name: '',
  day_id: null as number | null,
  address: '',
  category: '',
  start_time: '',
  end_time: '',
  notes: '',
})
const placeSubmitting = ref(false)

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
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function placesOfDay(dayId: number) {
  return places.value.filter((p) => p.day_id === dayId)
}

function placesWithoutDay() {
  return places.value.filter((p) => p.day_id === null)
}

function openDayDialog() {
  dayForm.value = { date: '', title: '' }
  dayDialogVisible.value = true
}

async function submitDay() {
  if (!dayForm.value.date) {
    ElMessage.warning('请选择日期')
    return
  }
  daySubmitting.value = true
  try {
    await createDay(tripId.value, {
      date: dayForm.value.date,
      title: dayForm.value.title || undefined,
    })
    ElMessage.success('已添加')
    dayDialogVisible.value = false
    await loadAll()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally {
    daySubmitting.value = false
  }
}

async function onDeleteDay(day: TripDay) {
  try {
    await ElMessageBox.confirm(`删除第 ${day.day_index} 天？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteDay(tripId.value, day.id)
    ElMessage.success('已删除')
    await loadAll()
  } catch {
    ElMessage.error('删除失败')
  }
}

function openPlaceDialog(dayId: number | null = null) {
  placeForm.value = {
    name: '',
    day_id: dayId,
    address: '',
    category: '',
    start_time: '',
    end_time: '',
    notes: '',
  }
  placeDialogVisible.value = true
}

async function submitPlace() {
  if (!placeForm.value.name.trim()) {
    ElMessage.warning('请填写地点名称')
    return
  }
  placeSubmitting.value = true
  try {
    const payload: any = { name: placeForm.value.name.trim() }
    if (placeForm.value.day_id !== null) payload.day_id = placeForm.value.day_id
    if (placeForm.value.address) payload.address = placeForm.value.address
    if (placeForm.value.category) payload.category = placeForm.value.category
    if (placeForm.value.start_time) payload.start_time = placeForm.value.start_time
    if (placeForm.value.end_time) payload.end_time = placeForm.value.end_time
    if (placeForm.value.notes) payload.notes = placeForm.value.notes

    await createPlace(tripId.value, payload)
    ElMessage.success('已添加')
    placeDialogVisible.value = false
    await loadAll()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally {
    placeSubmitting.value = false
  }
}

async function onDeletePlace(place: Place) {
  try {
    await deletePlace(tripId.value, place.id)
    ElMessage.success('已删除')
    await loadAll()
  } catch {
    ElMessage.error('删除失败')
  }
}

function goBack() {
  router.push('/trips')
}

onMounted(loadAll)
</script>

<template>
  <div class="page" v-loading="loading">
    <header class="topbar">
      <el-button link @click="goBack">← 返回</el-button>
      <div class="brand">途笺 Waynote</div>
      <div style="width: 60px"></div>
    </header>

    <main class="content" v-if="trip">
      <div class="trip-header">
        <div>
          <h1>{{ trip.title }}</h1>
          <div class="meta">
            <span v-if="trip.destination">📍 {{ trip.destination }}</span>
            <span v-if="trip.start_date">
              🗓 {{ trip.start_date.slice(0, 10) }}
              <template v-if="trip.end_date"> ~ {{ trip.end_date.slice(0, 10) }}</template>
            </span>
          </div>
          <p class="desc" v-if="trip.description">{{ trip.description }}</p>
        </div>
        <el-button type="primary" @click="openDayDialog">添加一天</el-button>
      </div>

      <el-empty v-if="days.length === 0" description="还没有安排，点右上角添加一天" />

      <div v-else class="days">
        <div v-for="day in days" :key="day.id" class="day-block">
          <div class="day-header">
            <div class="day-title">
              <span class="badge">Day {{ day.day_index }}</span>
              <span class="date">{{ day.date }}</span>
              <span class="day-name" v-if="day.title">{{ day.title }}</span>
            </div>
            <div>
              <el-button size="small" link type="primary" @click="openPlaceDialog(day.id)">
                + 地点
              </el-button>
              <el-button size="small" link type="danger" @click="onDeleteDay(day)">
                删除
              </el-button>
            </div>
          </div>

          <div class="place-list">
            <el-empty
              v-if="placesOfDay(day.id).length === 0"
              description="暂无地点"
              :image-size="60"
            />
            <div v-for="place in placesOfDay(day.id)" :key="place.id" class="place-item">
              <div class="place-main">
                <div class="place-name">
                  {{ place.name }}
                  <el-tag v-if="place.category" size="small" type="info">
                    {{ place.category }}
                  </el-tag>
                </div>
                <div class="place-sub" v-if="place.address">📌 {{ place.address }}</div>
                <div class="place-sub" v-if="place.start_time">
                  🕐 {{ place.start_time.slice(11, 16) }}
                  <template v-if="place.end_time"> ~ {{ place.end_time.slice(11, 16) }}</template>
                </div>
                <div class="place-sub" v-if="place.notes">{{ place.notes }}</div>
              </div>
              <el-button link type="danger" size="small" @click="onDeletePlace(place)">
                删除
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="placesWithoutDay().length > 0" class="unassigned">
        <h3>未分配地点</h3>
        <div v-for="place in placesWithoutDay()" :key="place.id" class="place-item">
          <div class="place-main">
            <div class="place-name">{{ place.name }}</div>
            <div class="place-sub" v-if="place.address">📌 {{ place.address }}</div>
          </div>
          <el-button link type="danger" size="small" @click="onDeletePlace(place)">
            删除
          </el-button>
        </div>
      </div>
    </main>

    <el-dialog v-model="dayDialogVisible" title="添加一天" width="420px">
      <el-form label-width="70px">
        <el-form-item label="日期" required>
          <el-date-picker
            v-model="dayForm.date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="dayForm.title" placeholder="例如：抵达京都" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dayDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="daySubmitting" @click="submitDay">添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="placeDialogVisible" title="添加地点" width="480px">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="placeForm.name" placeholder="例如：清水寺" />
        </el-form-item>
        <el-form-item label="所属天">
          <el-select v-model="placeForm.day_id" placeholder="可选" clearable style="width: 100%">
            <el-option
              v-for="day in days"
              :key="day.id"
              :label="`Day ${day.day_index} · ${day.date}`"
              :value="day.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="placeForm.address" placeholder="可选" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="placeForm.category" placeholder="例如：寺庙、餐厅、酒店" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker
            v-model="placeForm.start_time"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="可选"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="placeForm.end_time"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="可选"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="placeForm.notes" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="placeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="placeSubmitting" @click="submitPlace">
          添加
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: #f5f7fa;
}
.topbar {
  height: 56px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.brand {
  font-weight: 700;
  font-size: 18px;
  letter-spacing: 2px;
}
.content {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}
.trip-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.trip-header h1 {
  margin: 0 0 8px;
  font-size: 26px;
}
.meta {
  color: #888;
  font-size: 13px;
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
}
.desc {
  color: #666;
  font-size: 14px;
  margin: 8px 0 0;
}
.days {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.day-block {
  background: #fff;
  border-radius: 10px;
  padding: 16px 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.day-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 12px;
}
.day-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.badge {
  background: #409eff;
  color: #fff;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}
.date {
  color: #333;
  font-weight: 600;
}
.day-name {
  color: #888;
  font-size: 13px;
}
.place-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.place-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 10px 12px;
  background: #fafbfc;
  border-radius: 8px;
}
.place-main {
  flex: 1;
}
.place-name {
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.place-sub {
  color: #888;
  font-size: 12px;
  margin-top: 4px;
}
.unassigned {
  margin-top: 24px;
  background: #fff;
  border-radius: 10px;
  padding: 16px 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.unassigned h3 {
  margin: 0 0 12px;
  font-size: 15px;
  color: #666;
}
</style>
