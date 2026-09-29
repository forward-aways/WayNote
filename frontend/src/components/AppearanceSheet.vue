<script setup lang="ts">
/** 外观设置：主题色（按钮/胶囊配色）/ 背景预设 / 图片链接 / 本地上传 / 光斑开关 */
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import AppIcon from '@/components/AppIcon.vue'
import FormSheet from '@/components/FormSheet.vue'
import { useAppearanceStore } from '@/stores/appearance'
import { BACKGROUND_PRESETS } from '@/utils/background'
import { ACCENT_PRESETS } from '@/utils/theme'

const appearance = useAppearanceStore()

const urlInput = ref('')
const uploading = ref(false)
const fileRef = ref<HTMLInputElement | null>(null)

function safeRun(action: () => void, fallback: string) {
  try {
    action()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : fallback)
  }
}

function choosePreset(id: string) {
  safeRun(() => appearance.setPreset(id), '保存失败')
}

function chooseAccent(id: string) {
  safeRun(() => appearance.setAccentPreset(id), '主题色保存失败')
}

function onCustomColor(event: Event) {
  const value = (event.target as HTMLInputElement).value
  safeRun(() => appearance.setCustomAccent(value), '主题色无效')
}

function isPresetActive(id: string) {
  return appearance.accentId === id && !appearance.isCustomAccent
}

function applyUrl() {
  safeRun(() => {
    appearance.setImageUrl(urlInput.value)
    ElMessage.success('背景已应用')
  }, '链接无效')
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  uploading.value = true
  try {
    await appearance.setImageFile(file)
    ElMessage.success('背景已应用')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '图片处理失败')
  } finally {
    uploading.value = false
  }
}

function onAurora(value: unknown) {
  safeRun(() => appearance.setAurora(Boolean(value)), '设置未能保存')
}
</script>

<template>
  <FormSheet v-model="appearance.sheetOpen" title="外观设置" width="520px">
    <p class="group-label">主题色（按钮 / 胶囊 / 高亮）</p>
    <div class="accent-grid">
      <button
        v-for="preset in ACCENT_PRESETS"
        :key="preset.id"
        type="button"
        class="accent"
        :class="{ active: isPresetActive(preset.id) }"
        :style="{ background: preset.cssVar }"
        :title="preset.name"
        @click="chooseAccent(preset.id)"
      >
        <AppIcon v-if="isPresetActive(preset.id)" name="check" :size="15" />
      </button>

      <label
        class="accent custom"
        :class="{ active: appearance.isCustomAccent }"
        :style="{ background: appearance.accentBase }"
        title="自定义颜色"
      >
        <input type="color" :value="appearance.accentBase" @input="onCustomColor" />
        <AppIcon v-if="appearance.isCustomAccent" name="check" :size="15" />
      </label>
    </div>
    <p class="hint">
      <AppIcon name="sparkles" :size="13" />
      自定义颜色会自动派生深浅色，保证任何配色下的文字对比度都达标
      <button v-if="appearance.isCustomAccent || appearance.accentId !== 'emerald'" class="reset" type="button" @click="appearance.resetAccent()">
        恢复默认
      </button>
    </p>

    <p class="group-label">背景预设</p>
    <div class="preset-grid">
      <button
        v-for="preset in BACKGROUND_PRESETS"
        :key="preset.id"
        type="button"
        class="preset"
        :class="{ active: appearance.mode === 'preset' && appearance.presetId === preset.id }"
        :style="{ background: preset.cssVar }"
        @click="choosePreset(preset.id)"
      >
        <span class="preset-name">{{ preset.name }}</span>
        <AppIcon
          v-if="appearance.mode === 'preset' && appearance.presetId === preset.id"
          name="check"
          :size="14"
        />
      </button>
    </div>

    <p class="group-label">图片链接</p>
    <div class="row">
      <el-input v-model="urlInput" placeholder="https://example.com/travel.jpg" clearable />
      <el-button :disabled="!urlInput.trim()" @click="applyUrl">应用</el-button>
    </div>

    <p class="group-label">本地上传（自动压缩，压缩后需 ≤1.2MB）</p>
    <div class="row">
      <input ref="fileRef" type="file" accept="image/*" class="file-input" @change="onFileChange" />
      <el-button :loading="uploading" @click="fileRef?.click()">
        <AppIcon name="image" :size="15" />
        选择图片
      </el-button>
      <el-button v-if="appearance.isCustomImage" text type="danger" @click="appearance.clearImage()">
        移除自定义背景
      </el-button>
    </div>

    <div class="switch-row">
      <span class="switch-label"><AppIcon name="sparkles" :size="15" /> 极光光斑动画</span>
      <el-switch :model-value="appearance.aurora" @update:model-value="onAurora" />
    </div>
  </FormSheet>
</template>

<style scoped>
.group-label {
  margin: var(--wy-s3) 0 var(--wy-s2);
  color: var(--wy-ink-2);
  font-size: var(--wy-text-sm);
  font-weight: 600;
}
.group-label:first-child {
  margin-top: 0;
}
.accent-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--wy-s2);
}
.accent {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 2px solid transparent;
  border-radius: var(--wy-r-full);
  color: var(--wy-ink-1);
  cursor: pointer;
  transition:
    transform var(--wy-dur) var(--wy-spring),
    border-color var(--wy-dur) var(--wy-ease);
}
.accent:hover {
  transform: translateY(-2px) scale(1.04);
}
.accent:active {
  transform: translateY(0) scale(0.97);
}
.accent.active {
  border-color: var(--wy-ink-1);
}
.accent.custom {
  position: relative;
  overflow: hidden;
  border-style: dashed;
}
.accent.custom input[type='color'] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}
.preset-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--wy-s2);
}
.preset {
  position: relative;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  height: 64px;
  padding: var(--wy-s2);
  border: 2px solid transparent;
  border-radius: var(--wy-r-sm);
  color: var(--wy-ink-1);
  cursor: pointer;
  transition:
    transform var(--wy-dur) var(--wy-spring),
    border-color var(--wy-dur) var(--wy-ease);
}
.preset:hover {
  transform: translateY(-2px);
}
.preset:active {
  transform: translateY(0) scale(0.98);
}
.preset.active {
  border-color: var(--wy-primary);
  box-shadow: var(--wy-gem-glow);
}
.preset-name {
  padding: 2px 8px;
  border-radius: var(--wy-r-full);
  background: rgba(255, 255, 255, 0.72);
  font-size: var(--wy-text-xs);
  font-weight: 600;
}
.hint {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin: var(--wy-s2) 0 0;
  color: var(--wy-ink-3);
  font-size: var(--wy-text-xs);
}
.reset {
  padding: 0;
  border: none;
  background: none;
  color: var(--wy-primary-strong);
  font-size: var(--wy-text-xs);
  text-decoration: underline;
  cursor: pointer;
}
.row {
  display: flex;
  align-items: center;
  gap: var(--wy-s2);
}
.file-input {
  display: none;
}
.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--wy-s5);
  padding-top: var(--wy-s4);
  border-top: 1px solid var(--wy-line);
}
.switch-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--wy-ink-2);
  font-size: var(--wy-text-sm);
}
</style>
