/** 外观设置（背景 / 主题色 / 光斑）：持久化到 localStorage，并同步到 CSS 变量 */
import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import {
  DEFAULT_PRESET_ID,
  isSafeBackgroundValue,
  presetCss,
  toSafeUrlValue,
  compressImageFile,
} from '@/utils/background'
import {
  ACCENT_PRESETS,
  DEFAULT_ACCENT_ID,
  applyTheme,
  clearTheme,
  deriveTheme,
  parseHexColor,
} from '@/utils/theme'

export type BackgroundMode = 'preset' | 'image'

const STORAGE_KEY = 'wy.appearance'

interface PersistedAppearance {
  mode: BackgroundMode
  presetId: string
  imageValue: string
  aurora: boolean
  accentId: string
  accentCustom: string
}

/** 读取 tokens.css 中的预设色值（保持色值单一来源，前端不硬编码；无 DOM 时返回空由调用方回退默认） */
function cssVarHex(cssVar: string): string {
  if (typeof document === 'undefined') return ''
  const name = /var\(\s*(--[\w-]+)\s*\)/.exec(cssVar)?.[1]
  if (!name) return ''
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

export const useAppearanceStore = defineStore('appearance', () => {
  const mode = ref<BackgroundMode>('preset')
  const presetId = ref<string>(DEFAULT_PRESET_ID)
  const imageValue = ref<string>('')
  const aurora = ref(true)
  const accentId = ref<string>(DEFAULT_ACCENT_ID)
  const accentCustom = ref<string>('')
  const sheetOpen = ref(false)

  const background = computed(() =>
    mode.value === 'image' && imageValue.value ? imageValue.value : presetCss(presetId.value),
  )

  const accentBase = computed(() =>
    accentCustom.value ||
    cssVarHex(
      ACCENT_PRESETS.find((item) => item.id === accentId.value)?.cssVar ??
        'var(--wy-accent-preset-emerald)',
    ),
  )

  const isCustomAccent = computed(() => !!accentCustom.value)

  function apply() {
    document.documentElement.style.setProperty('--wy-user-bg', background.value)
    if (!accentCustom.value && accentId.value === DEFAULT_ACCENT_ID) {
      clearTheme(document.documentElement) // 使用 tokens.css 中已审计的默认值
      return
    }
    if (!parseHexColor(accentBase.value)) {
      clearTheme(document.documentElement)
      return
    }
    applyTheme(deriveTheme(accentBase.value), accentBase.value, document.documentElement)
  }

  function persist() {
    const payload: PersistedAppearance = {
      mode: mode.value,
      presetId: presetId.value,
      imageValue: imageValue.value,
      aurora: aurora.value,
      accentId: accentId.value,
      accentCustom: accentCustom.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  }

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const saved = JSON.parse(raw) as Partial<PersistedAppearance>
        if (saved.mode === 'image' || saved.mode === 'preset') mode.value = saved.mode
        if (typeof saved.presetId === 'string') presetId.value = saved.presetId
        if (typeof saved.imageValue === 'string' && isSafeBackgroundValue(saved.imageValue)) {
          imageValue.value = saved.imageValue
        } else if (saved.mode === 'image') {
          mode.value = 'preset'
        }
        if (typeof saved.aurora === 'boolean') aurora.value = saved.aurora
        if (typeof saved.accentId === 'string') accentId.value = saved.accentId
        if (typeof saved.accentCustom === 'string' && parseHexColor(saved.accentCustom)) {
          accentCustom.value = saved.accentCustom
        }
      }
    } catch {
      // 数据损坏：回退默认
    }
    apply()
  }

  function setPreset(id: string) {
    presetId.value = id
    mode.value = 'preset'
    persist()
  }

  function setImageUrl(raw: string) {
    const value = toSafeUrlValue(raw)
    if (!value) throw new Error('仅支持 http(s) 图片链接或 data:image')
    imageValue.value = value
    mode.value = 'image'
    persist()
  }

  async function setImageFile(file: File) {
    const dataUrl = await compressImageFile(file)
    imageValue.value = `url("${dataUrl}")`
    mode.value = 'image'
    persist()
  }

  function clearImage() {
    imageValue.value = ''
    mode.value = 'preset'
    persist()
  }

  function setAurora(on: boolean) {
    aurora.value = on
    persist()
  }

  /** 主题色：预设 */
  function setAccentPreset(id: string) {
    if (!ACCENT_PRESETS.some((item) => item.id === id)) return
    accentId.value = id
    accentCustom.value = ''
    apply()
    persist()
  }

  /** 主题色：自定义（自动派生深浅色并保证对比度） */
  function setCustomAccent(hex: string) {
    if (!parseHexColor(hex)) throw new Error('颜色格式无效')
    accentCustom.value = hex.toLowerCase()
    apply()
    persist()
  }

  function resetAccent() {
    accentId.value = DEFAULT_ACCENT_ID
    accentCustom.value = ''
    apply()
    persist()
  }

  function resetAll() {
    mode.value = 'preset'
    presetId.value = DEFAULT_PRESET_ID
    imageValue.value = ''
    aurora.value = true
    accentId.value = DEFAULT_ACCENT_ID
    accentCustom.value = ''
    apply()
    persist()
  }

  const isCustomImage = computed(() => mode.value === 'image' && !!imageValue.value)

  watch(background, apply)

  return {
    mode,
    presetId,
    imageValue,
    aurora,
    accentId,
    accentCustom,
    sheetOpen,
    background,
    accentBase,
    isCustomAccent,
    isCustomImage,
    load,
    apply,
    setPreset,
    setImageUrl,
    setImageFile,
    clearImage,
    setAurora,
    setAccentPreset,
    setCustomAccent,
    resetAccent,
    resetAll,
  }
})
