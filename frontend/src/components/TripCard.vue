<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import TagChip from '@/components/TagChip.vue'
import type { TripListItem } from '@/api/trips'
import {
  PHASE_LABEL,
  PHASE_TONE,
  countdownText,
  destinationPalette,
  formatDateRange,
  tripPhase,
} from '@/utils/trip'

const props = defineProps<{ trip: TripListItem }>()
const emit = defineEmits<{ open: []; edit: []; remove: [] }>()

const phase = computed(() => tripPhase(props.trip))
const palette = computed(() => destinationPalette(props.trip.destination || props.trip.title))
const dateText = computed(() => formatDateRange(props.trip.start_date, props.trip.end_date))
const countdown = computed(() => countdownText(props.trip))
const statsText = computed(() => {
  const { day_count, place_count } = props.trip
  if (day_count === 0 && place_count === 0) return '尚未安排日程'
  return [`已安排 ${day_count} 天`, `${place_count} 个地点`].join(' · ')
})

function onCommand(command: string) {
  if (command === 'edit') emit('edit')
  if (command === 'remove') emit('remove')
}
</script>

<template>
  <article
    class="trip-card wy-rise"
    role="button"
    tabindex="0"
    :aria-label="`打开行程：${trip.title}`"
    @click="emit('open')"
    @keydown.enter.prevent="emit('open')"
  >
    <div class="card-body">
      <header class="card-head">
        <h3 class="card-title wy-clamp-2" :title="trip.title">{{ trip.title }}</h3>
        <TagChip
          :text="PHASE_LABEL[phase]"
          :tone="PHASE_TONE[phase]"
        />
      </header>

      <p v-if="trip.destination" class="card-line">
        <span class="dest-dot" :style="{ background: palette.gradient }" aria-hidden="true" />
        <span class="wy-clamp-1">{{ trip.destination }}</span>
      </p>
      <p class="card-line">
        <AppIcon name="calendar" :size="14" />
        <span>{{ dateText }}</span>
        <span class="countdown wy-num">{{ countdown }}</span>
      </p>

      <p v-if="trip.description" class="card-desc wy-clamp-2">{{ trip.description }}</p>
    </div>

    <footer class="card-foot">
      <span class="card-stats">{{ statsText }}</span>
      <el-dropdown trigger="click" @command="onCommand">
        <button
          class="more-btn"
          type="button"
          aria-label="更多操作"
          @click.stop
          @keydown.stop
        >
          <AppIcon name="more" :size="18" />
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="edit">
              <span class="menu-item"><AppIcon name="edit" :size="15" /> 编辑行程</span>
            </el-dropdown-item>
            <el-dropdown-item command="remove" divided>
              <span class="menu-item danger"><AppIcon name="trash" :size="15" /> 删除行程</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </footer>
  </article>
</template>

<style scoped>
.trip-card {
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: var(--wy-r-md);
  /* 淡雅翡翠玻璃卡：主题色轻染 + 镜面高光 + 边缘反光（不再用顶部色条） */
  background:
    var(--wy-sheen-soft),
    color-mix(in srgb, var(--wy-accent-base) 8%, rgba(255, 255, 255, 0.86));
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.5),
    var(--wy-shadow-2);
  cursor: pointer;
  transition:
    transform var(--wy-dur) var(--wy-spring),
    box-shadow var(--wy-dur) var(--wy-ease);
}
.trip-card:hover {
  transform: translateY(-5px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.5),
    var(--wy-float-shadow);
}
.trip-card:active {
  transform: translateY(0) scale(0.985);
}
.dest-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: var(--wy-gem-highlight);
}
.card-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--wy-s2);
  padding: var(--wy-s4) var(--wy-s4) var(--wy-s3);
}
.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--wy-s3);
}
.card-title {
  margin: 0;
  font-size: var(--wy-text-md);
  line-height: 1.4;
}
.card-line {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
}
.card-line svg {
  flex-shrink: 0;
}
.countdown {
  margin-left: auto;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--wy-sun-weak);
  color: var(--wy-sun-strong);
  font-size: var(--wy-text-xs);
  font-weight: 600;
  white-space: nowrap;
}
.card-desc {
  margin: 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-sm);
}
.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--wy-s2) var(--wy-s4);
  background: rgba(255, 255, 255, 0.45);
}
.card-stats {
  color: var(--wy-ink-2);
  font-size: var(--wy-text-xs);
  letter-spacing: 0.3px;
}
.more-btn {
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
  opacity: 0;
  transition:
    opacity var(--wy-dur) var(--wy-ease),
    background var(--wy-dur) var(--wy-ease);
}
.trip-card:hover .more-btn,
.more-btn:focus-visible {
  opacity: 1;
}
.more-btn:hover {
  background: var(--wy-surface);
  color: var(--wy-ink-1);
}
.menu-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.menu-item.danger {
  color: var(--el-color-danger);
}
@media (hover: none) {
  .more-btn {
    opacity: 1;
  }
}
</style>
