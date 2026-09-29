<script setup lang="ts">
import { computed } from 'vue'
import { useIsMobile } from '@/composables/useIsMobile'

/**
 * 响应式表单容器：桌面为居中对话框，移动端为底部抽屉。
 * 页面只负责内容与底部按钮，交互形态由本组件统一承担。
 */
const props = withDefaults(
  defineProps<{ modelValue: boolean; title: string; width?: string }>(),
  { width: '480px' },
)

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const isMobile = useIsMobile()
const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})
</script>

<template>
  <el-dialog
    v-if="!isMobile"
    v-model="visible"
    :title="title"
    :width="width"
    append-to-body
    destroy-on-close
  >
    <slot />
    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </el-dialog>

  <el-drawer
    v-else
    v-model="visible"
    :title="title"
    direction="btt"
    size="auto"
    class="wy-sheet-drawer"
    append-to-body
    destroy-on-close
  >
    <slot />
    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </el-drawer>
</template>
