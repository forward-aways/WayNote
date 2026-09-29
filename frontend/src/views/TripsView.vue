<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { listTrips, createTrip, deleteTrip } from '@/api/trips'
import type { Trip } from '@/api/trips'

const auth = useAuthStore()
const router = useRouter()

const trips = ref<Trip[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)

const form = ref({
  title: '',
  destination: '',
  start_date: '',
  end_date: '',
  description: '',
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

function openDialog() {
  form.value = {
    title: '',
    destination: '',
    start_date: '',
    end_date: '',
    description: '',
  }
  dialogVisible.value = true
}

async function submit() {
  if (!form.value.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  submitting.value = true
  try {
    const payload: any = { title: form.value.title.trim() }
    if (form.value.destination) payload.destination = form.value.destination
    if (form.value.start_date) payload.start_date = form.value.start_date
    if (form.value.end_date) payload.end_date = form.value.end_date
    if (form.value.description) payload.description = form.value.description

    await createTrip(payload)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    await loadTrips()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

async function onDelete(trip: Trip) {
  try {
    await ElMessageBox.confirm(`确定删除「${trip.title}」吗？`, '提示', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deleteTrip(trip.id)
    ElMessage.success('已删除')
    await loadTrips()
  } catch {
    ElMessage.error('删除失败')
  }
}

function openTrip(trip: Trip) {
  router.push(`/trips/${trip.id}`)
}

function logout() {
  auth.logout()
  router.push('/login')
}

onMounted(() => {
  auth.fetchMe()
  loadTrips()
})
</script>

<template>
  <div class="page">
    <header class="topbar">
      <div class="brand">途笺 Waynote</div>
      <div class="user">
        <span>{{ auth.user?.name || auth.user?.email }}</span>
        <el-button link @click="logout">退出</el-button>
      </div>
    </header>

    <main class="content">
      <div class="toolbar">
        <h2>我的行程</h2>
        <el-button type="primary" @click="openDialog">新建行程</el-button>
      </div>

      <div v-loading="loading">
        <el-empty v-if="!loading && trips.length === 0" description="还没有行程，点右上角新建一个吧" />

        <div v-else class="trip-grid">
          <el-card
            v-for="trip in trips"
            :key="trip.id"
            class="trip-card"
            shadow="hover"
            @click="openTrip(trip)"
          >
            <div class="trip-title">{{ trip.title }}</div>
            <div class="trip-dest" v-if="trip.destination">📍 {{ trip.destination }}</div>
            <div class="trip-date" v-if="trip.start_date">
              {{ trip.start_date.slice(0, 10) }}
              <span v-if="trip.end_date"> ~ {{ trip.end_date.slice(0, 10) }}</span>
            </div>
            <div class="trip-desc" v-if="trip.description">{{ trip.description }}</div>
            <div class="trip-actions">
              <el-button size="small" link type="danger" @click.stop="onDelete(trip)">
                删除
              </el-button>
            </div>
          </el-card>
        </div>
      </div>
    </main>

    <el-dialog v-model="dialogVisible" title="新建行程" width="480px">
      <el-form label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="例如：京都三日游" />
        </el-form-item>
        <el-form-item label="目的地">
          <el-input v-model="form.destination" placeholder="例如：京都" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="form.start_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="form.end_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="简单描述一下这次旅行"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">创建</el-button>
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
.user {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #666;
  font-size: 14px;
}
.content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.toolbar h2 {
  margin: 0;
}
.trip-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.trip-card {
  cursor: pointer;
  transition: transform 0.15s;
}
.trip-card:hover {
  transform: translateY(-2px);
}
.trip-title {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 8px;
}
.trip-dest {
  color: #409eff;
  font-size: 13px;
  margin-bottom: 4px;
}
.trip-date {
  color: #999;
  font-size: 12px;
  margin-bottom: 6px;
}
.trip-desc {
  color: #666;
  font-size: 13px;
  margin-top: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.trip-actions {
  margin-top: 10px;
  text-align: right;
}
</style>
