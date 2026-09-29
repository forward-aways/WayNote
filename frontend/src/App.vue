<script setup lang="ts">
/** 应用外壳：背景舞台 + （桌面）常驻左侧栏 + 顶栏 + （移动）底部胶囊导航 + 外观设置 */
import { computed, onMounted, ref } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import AppBar from '@/components/AppBar.vue'
import AppearanceSheet from '@/components/AppearanceSheet.vue'
import BackgroundStage from '@/components/BackgroundStage.vue'
import BottomNav from '@/components/BottomNav.vue'
import DesktopSidebar from '@/components/DesktopSidebar.vue'
import SideNav from '@/components/SideNav.vue'
import { useIsMobile } from '@/composables/useIsMobile'
import { useAppearanceStore } from '@/stores/appearance'

const route = useRoute()
const router = useRouter()
const appearance = useAppearanceStore()

const isMobile = useIsMobile()
const sideOpen = ref(false)
const isAuthed = computed(() => route.meta.auth === true)
const isDetail = computed(() => route.name === 'trip-detail')

onMounted(() => appearance.load())

function onBack() {
  if (window.history.length > 1) router.back()
  else router.push('/trips')
}
</script>

<template>
  <BackgroundStage />

  <div class="shell" :class="{ 'shell-authed': isAuthed }">
    <DesktopSidebar v-if="isAuthed" />

    <div class="shell-main">
      <AppBar
        v-if="isAuthed"
        :menu="isMobile && !isDetail"
        :back="isDetail"
        :show-brand="isMobile"
        @menu="sideOpen = true"
        @back="onBack"
      />
      <router-view v-slot="{ Component }">
        <transition name="wy-page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
  </div>

  <SideNav v-if="isAuthed && isMobile" v-model="sideOpen" />
  <BottomNav v-if="isAuthed" />
  <AppearanceSheet />
</template>

<style scoped>
.shell {
  min-height: 100vh;
}
.shell-main {
  min-width: 0;
}
@media (min-width: 768px) {
  .shell-authed {
    display: flex;
    align-items: stretch;
  }
  .shell-main {
    flex: 1;
  }
}
</style>
