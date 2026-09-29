<script setup lang="ts">
/** 移动端侧边抽屉（桌面端改用常驻左侧栏 DesktopSidebar） */
import { computed } from 'vue'
import SideNavContent from '@/components/SideNavContent.vue'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})
</script>

<template>
  <el-drawer
    v-model="visible"
    direction="ltr"
    size="280px"
    :with-header="false"
    class="wy-side-drawer"
  >
    <SideNavContent @navigate="visible = false" />
  </el-drawer>
</template>
