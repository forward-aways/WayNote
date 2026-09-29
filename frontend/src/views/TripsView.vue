<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AppIcon from '@/components/AppIcon.vue'
import EmptyState from '@/components/EmptyState.vue'
import FormSheet from '@/components/FormSheet.vue'
import TripCard from '@/components/TripCard.vue'
import { createTrip, deleteTrip, listTrips, updateTrip } from '@/api/trips'
import type { TripListItem } from '@/api/trips'
import { tripPhase } from '@/utils/trip'
import { rememberTripHint } from '@/utils/tripHint'
import { apiErrorMessage } from '@/utils/error'

type FilterKey = 'all' | 'upcoming' | 'ongoing' | 'finished'

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'upcoming', label: '待出发' },
  { key: 'ongoing', label: '旅途中' },
  { key: 'finished', label: '已结束' },
]

const router = useRouter()
const trips = ref<TripListItem[]>([])
const loading = ref(true)
const activeFilter = ref<FilterKey>('all')

const sheetVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = ref({
  title: '',
  destination: '',
  start_date: '',
  end_date: '',
  description: '',
})

/** 无日期行程归入「待出发」，保证任一筛选都不丢数据 */
function phaseOf(trip: TripListItem): FilterKey {
  const phase = tripPhase(trip)
  return phase === 'undated' ? 'upcoming' : phase
}

const counts = computed(() => {
  const result: Record<FilterKey, number> = { all: trips.value.length, upcoming: 0, ongoing: 0, finished: 0 }
  for (const trip of trips.value) result[phaseOf(trip)] += 1
  return result
})

const filtered = computed(() =>
  activeFilter.value === 'all'
    ? trips.value
    : trips.value.filter((trip) => phaseOf(trip) === activeFilter.value),
)

const summaryText = computed(() => {
  if (trips.value.length === 0) return ''
  const upcoming = counts.value.upcoming
  return upcoming > 0
    ? `共 ${trips.value.length} 段行程 · ${upcoming} 段待出发`
    : `共 ${trips.value.length} 段行程`
})

async function loadTrips() {
  loading.value = true
  try {
    trips.value = await listTrips()
  } catch {
    ElMessage.error('加载行程失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.value = { title: '', destination: '', start_date: '', end_date: '', description: '' }
}

function openCreate() {
  resetForm()
  editingId.value = null
  sheetVisible.value = true
}

function openEdit(trip: TripListItem) {
  editingId.value = trip.id
  form.value = {
    title: trip.title,
    destination: trip.destination ?? '',
    start_date: trip.start_date?.slice(0, 10) ?? '',
    end_date: trip.end_date?.slice(0, 10) ?? '',
    description: trip.description ?? '',
  }
  sheetVisible.value = true
}

/** 点卡片进详情：先把列表数据接力过去（详情页首帧即可渲染，消除白闪） */
function openDetail(trip: TripListItem) {
  rememberTripHint(trip)
  router.push(`/trips/${trip.id}`)
}

async function submit() {
  const title = form.value.title.trim()
  if (!title) {
    ElMessage.warning('请填写行程标题')
    return
  }
  if (form.value.start_date && form.value.end_date && form.value.end_date < form.value.start_date) {
    ElMessage.warning('结束日期不能早于开始日期')
    return
  }

  saving.value = true
  try {
    if (editingId.value === null) {
      await createTrip({
        title,
        ...(form.value.destination.trim() ? { destination: form.value.destination.trim() } : {}),
        ...(form.value.start_date ? { start_date: form.value.start_date } : {}),
        ...(form.value.end_date ? { end_date: form.value.end_date } : {}),
        ...(form.value.description.trim() ? { description: form.value.description.trim() } : {}),
      })
      ElMessage.success('行程已创建')
    } else {
      await updateTrip(editingId.value, {
        title,
        destination: form.value.destination.trim() || null,
        start_date: form.value.start_date || null,
        end_date: form.value.end_date || null,
        description: form.value.description.trim() || null,
      })
      ElMessage.success('行程已更新')
    }
    sheetVisible.value = false
    await loadTrips()
  } catch (error: unknown) {
    ElMessage.error(apiErrorMessage(error, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function onDelete(trip: TripListItem) {
  try {
    await ElMessageBox.confirm(`删除「${trip.title}」后，其日程与地点将一并删除且无法恢复。`, '删除行程', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteTrip(trip.id)
    ElMessage.success('行程已删除')
    await loadTrips()
  } catch {
    ElMessage.error('删除失败')
  }
}

onMounted(loadTrips)
</script>

<template>
  <div class="page">
    <main class="wy-container content wy-bottom-safe">
      <header class="page-head">
        <div>
          <h1 class="page-title wy-display">我的行程</h1>
          <p v-if="summaryText" class="page-sub">{{ summaryText }}</p>
        </div>
        <el-button class="create-btn" type="primary" @click="openCreate">
          <AppIcon name="plus" :size="16" />
          新建行程
        </el-button>
      </header>

      <nav v-if="trips.length > 0" class="filters" aria-label="行程筛选">
        <button
          v-for="item in FILTERS"
          :key="item.key"
          class="chip"
          :class="{ active: activeFilter === item.key }"
          type="button"
          :aria-pressed="activeFilter === item.key"
          @click="activeFilter = item.key"
        >
          {{ item.label }}
          <span class="chip-count wy-num">{{ counts[item.key] }}</span>
        </button>
      </nav>

      <div v-if="loading" class="trip-grid" aria-busy="true">
        <div v-for="n in 3" :key="n" class="skeleton-card">
          <div class="sk-stripe" />
          <div class="sk-line w60" />
          <div class="sk-line w40" />
          <div class="sk-line w80" />
        </div>
      </div>

      <EmptyState
        v-else-if="trips.length === 0"
        title="还没有行程，去写下第一段旅途吧"
        description="记录想去的地方，出发时一目了然"
      >
        <el-button type="primary" @click="openCreate">
          <AppIcon name="plus" :size="16" />
          新建行程
        </el-button>
      </EmptyState>

      <p v-else-if="filtered.length === 0" class="filter-empty">该筛选下暂无行程</p>

      <div v-else class="trip-grid">
        <TripCard
          v-for="(trip, index) in filtered"
          :key="trip.id"
          :trip="trip"
          :style="{ animationDelay: `${index * 40}ms` }"
          @open="openDetail(trip)"
          @edit="openEdit(trip)"
          @remove="onDelete(trip)"
        />
      </div>
    </main>

    <button class="fab" type="button" aria-label="新建行程" @click="openCreate">
      <AppIcon name="plus" :size="24" />
    </button>

    <FormSheet v-model="sheetVisible" :title="editingId === null ? '新建行程' : '编辑行程'">
      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="例如：京都三日游" maxlength="100" />
        </el-form-item>
        <el-form-item label="目的地">
          <el-input v-model="form.destination" placeholder="例如：京都" maxlength="100" />
        </el-form-item>
        <div class="form-row">
          <el-form-item label="开始日期">
            <el-date-picker
              v-model="form.start_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择日期"
            />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-date-picker
              v-model="form.end_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择日期"
            />
          </el-form-item>
        </div>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            maxlength="500"
            placeholder="简单描述一下这次旅行"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="sheet-footer">
          <el-button @click="sheetVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="submit">
            {{ editingId === null ? '创建' : '保存' }}
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
  padding-bottom: var(--wy-s12);
}
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--wy-s4);
  margin-bottom: var(--wy-s4);
}
.page-title {
  margin: 0;
  font-size: var(--wy-text-xl);
  letter-spacing: 2px;
}
.page-sub {
  margin-top: var(--wy-s1);
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wy-s2);
  margin-bottom: var(--wy-s4);
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--wy-glass-stroke);
  border-radius: var(--wy-r-full);
  background: rgba(255, 255, 255, 0.6);
  color: var(--wy-ink-2);
  font-size: var(--wy-text-sm);
  cursor: pointer;
  transition: all var(--wy-dur) var(--wy-ease);
}
.chip:hover {
  border-color: var(--wy-line-strong);
}
.chip.active {
  border-color: transparent;
  background: var(--wy-jade-surface);
  /* 必写：带边框的元素若只铺 padding-box，边框区会平铺出深绿切片（假边框） */
  background-origin: border-box;
  color: var(--wy-on-jade);
  box-shadow: var(--wy-gem-glow-sm);
}
.chip-count {
  font-size: var(--wy-text-xs);
  opacity: 0.75;
}
.trip-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--wy-s4);
}
.filter-empty {
  padding: var(--wy-s8) 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
  text-align: center;
}
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--wy-s3);
}
.form-row :deep(.el-date-editor) {
  width: 100%;
}
.sheet-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--wy-s2);
}
.create-btn {
  flex-shrink: 0;
}
.fab {
  display: none;
}
/* 骨架卡 */
.skeleton-card {
  display: flex;
  flex-direction: column;
  gap: var(--wy-s3);
  padding: var(--wy-s4);
  border: 1px solid var(--wy-glass-stroke);
  border-radius: var(--wy-r-md);
  background: var(--wy-glass-panel-bg);
  box-shadow: var(--wy-shadow-2);
}
.sk-stripe {
  height: 8px;
  border-radius: 999px;
  background: var(--wy-bg-soft);
}
.sk-line {
  height: 12px;
  border-radius: 999px;
  background: linear-gradient(
    90deg,
    var(--wy-bg-soft) 25%,
    var(--wy-line) 37%,
    var(--wy-bg-soft) 63%
  );
  background-size: 400% 100%;
  animation: sk 1.4s ease infinite;
}
.w60 {
  width: 60%;
}
.w40 {
  width: 40%;
}
.w80 {
  width: 80%;
}
@keyframes sk {
  0% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0 50%;
  }
}
@media (max-width: 767px) {
  .page-head {
    align-items: center;
  }
  .create-btn {
    display: none;
  }
  .trip-grid {
    grid-template-columns: 1fr;
  }
  .fab {
    position: fixed;
    right: var(--wy-s4);
    bottom: calc(96px + env(safe-area-inset-bottom));
    z-index: 30;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 58px;
    height: 58px;
    border-radius: 50%;
    /* 透明淡绿光玻璃 FAB（与激活胶囊同款） */
    background: color-mix(in srgb, var(--wy-accent-base) 20%, rgba(255, 255, 255, 0.34));
    border: 1px solid rgba(255, 255, 255, 0.55);
    color: var(--wy-ink-1);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.55),
      0 10px 24px rgba(6, 60, 46, 0.16);
    -webkit-backdrop-filter: blur(12px) saturate(160%);
    backdrop-filter: blur(12px) saturate(160%);
    cursor: pointer;
    transition: transform var(--wy-dur) var(--wy-spring);
  }
  .fab:hover {
    transform: translateY(-2px) scale(1.04);
  }
  .fab:active {
    transform: scale(0.94);
  }
  .form-row {
    grid-template-columns: 1fr;
    gap: 0;
  }
}
</style>
