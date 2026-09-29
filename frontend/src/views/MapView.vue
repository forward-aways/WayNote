<script setup lang="ts">
/** 地图（v1）：坐标地点清单 + 一键跳转腾讯地图；真地图 SDK 待备案与 Key 后接入 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import AppIcon from '@/components/AppIcon.vue'
import EmptyState from '@/components/EmptyState.vue'
import TagChip from '@/components/TagChip.vue'
import { listTrips } from '@/api/trips'
import type { TripListItem } from '@/api/trips'
import { listPlaces } from '@/api/places'
import type { Place } from '@/api/places'
import { destinationPalette, tencentMapUrl, timeText } from '@/utils/trip'

interface Group {
  trip: TripListItem
  places: Place[]
}

const loading = ref(true)
const groups = ref<Group[]>([])
const totalGeo = computed(() => groups.value.reduce((sum, group) => sum + group.places.length, 0))

async function load() {
  loading.value = true
  try {
    const trips = await listTrips()
    const all = await Promise.all(
      trips.map(async (trip) => {
        const places = await listPlaces(trip.id)
        const geo = places.filter((place) => place.lat !== null && place.lng !== null)
        return { trip, places: geo }
      }),
    )
    groups.value = all.filter((group) => group.places.length > 0)
  } catch {
    ElMessage.error('加载地点失败')
  } finally {
    loading.value = false
  }
}

function openMap(place: Place) {
  const url = tencentMapUrl(place)
  if (url) window.open(url, '_blank', 'noopener')
}

async function copyCoordinate(place: Place) {
  try {
    await navigator.clipboard.writeText(`${place.lat},${place.lng}`)
    ElMessage.success('坐标已复制')
  } catch {
    ElMessage.warning('当前浏览器不支持自动复制')
  }
}

onMounted(load)
</script>

<template>
  <main class="wy-container content wy-bottom-safe">
    <header class="head">
      <h1 class="page-title wy-display">地图</h1>
      <p class="page-sub">带坐标的地点可以一键跳到腾讯地图</p>
    </header>

    <section class="notice glass-panel">
      <span class="notice-icon"><AppIcon name="map" :size="18" /></span>
      <div>
        <p class="notice-title">完整地图视图即将上线</p>
        <p class="notice-desc">
          站内地图 SDK 需要备案域名与地图 Key（备案审核中）。当前先提供坐标清单与跳转，功能不受影响。
        </p>
      </div>
    </section>

    <div v-loading="loading">
      <EmptyState
        v-if="!loading && groups.length === 0"
        title="还没有带坐标的地点"
        description="在行程里给地点补上经纬度，就会出现在这里"
      />

      <template v-else>
        <p class="count">共 {{ totalGeo }} 个坐标地点</p>
        <section v-for="group in groups" :key="group.trip.id" class="group glass-panel">
          <header class="group-head">
            <span
              class="group-stripe"
              :style="{ background: destinationPalette(group.trip.destination || group.trip.title).gradient }"
            />
            <span class="group-title">{{ group.trip.title }}</span>
            <TagChip v-if="group.trip.destination" :text="group.trip.destination" tone="gem" />
          </header>

          <article v-for="place in group.places" :key="place.id" class="place">
            <div class="place-main">
              <p class="place-name">
                {{ place.name }}
                <TagChip v-if="place.category" :text="place.category" tone="primary" />
              </p>
              <p v-if="place.address" class="place-sub">
                <AppIcon name="pin" :size="13" /> {{ place.address }}
              </p>
              <p v-if="timeText(place)" class="place-sub">
                <AppIcon name="clock" :size="13" /> {{ timeText(place) }}
              </p>
            </div>
            <div class="place-actions">
              <button class="text-btn" type="button" @click="openMap(place)">
                <AppIcon name="navigation" :size="14" /> 地图
              </button>
              <button class="text-btn" type="button" @click="copyCoordinate(place)">
                <AppIcon name="copy" :size="14" /> 坐标
              </button>
            </div>
          </article>
        </section>
      </template>
    </div>
  </main>
</template>

<style scoped>
.content {
  padding-top: var(--wy-s5);
  padding-bottom: var(--wy-s12);
}
.head {
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
.notice {
  display: flex;
  align-items: flex-start;
  gap: var(--wy-s3);
  padding: var(--wy-s4);
  margin-bottom: var(--wy-s4);
  border-radius: var(--wy-r-md);
}
.notice-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: var(--wy-primary-weak);
  color: var(--wy-primary-strong);
  flex-shrink: 0;
}
.notice-title {
  margin: 0;
  color: var(--wy-ink-1);
  font-weight: 600;
}
.notice-desc {
  margin: 2px 0 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
}
.count {
  margin: 0 0 var(--wy-s3);
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
}
.group {
  padding: var(--wy-s4);
  border-radius: var(--wy-r-md);
  margin-bottom: var(--wy-s4);
}
.group-head {
  display: flex;
  align-items: center;
  gap: var(--wy-s3);
  margin-bottom: var(--wy-s3);
}
.group-stripe {
  width: 6px;
  height: 22px;
  border-radius: var(--wy-r-full);
}
.group-title {
  color: var(--wy-ink-1);
  font-weight: 700;
}
.place {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--wy-s3);
  padding: var(--wy-s3);
  border-radius: var(--wy-r-sm);
  transition: background var(--wy-dur) var(--wy-ease);
}
.place:hover {
  background: rgba(255, 255, 255, 0.6);
}
.place-main {
  min-width: 0;
  flex: 1;
}
.place-name {
  display: flex;
  align-items: center;
  gap: var(--wy-s2);
  margin: 0;
  color: var(--wy-ink-1);
  font-weight: 600;
}
.place-sub {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 4px 0 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
}
.place-actions {
  display: flex;
  gap: var(--wy-s2);
  flex-shrink: 0;
}
.text-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border: 1px solid var(--wy-glass-stroke);
  border-radius: var(--wy-r-full);
  background: rgba(255, 255, 255, 0.6);
  color: var(--wy-ink-2);
  font-size: var(--wy-text-xs);
  cursor: pointer;
  transition: all var(--wy-dur) var(--wy-ease);
}
.text-btn:hover {
  border-color: var(--wy-primary);
  color: var(--wy-primary-strong);
}
@media (max-width: 767px) {
  .place {
    flex-direction: column;
  }
}
</style>
