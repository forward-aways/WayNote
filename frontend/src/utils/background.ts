/** 背景系统工具：预设 / 图片 URL 校验与转义 / 本地图片压缩（纯前端，无外部依赖） */

export interface BackgroundPreset {
  id: string
  name: string
  /** 引用 tokens.css 中的令牌（本文件禁止出现字面色值，见 check-tokens 守卫） */
  cssVar: string
}

export const BACKGROUND_PRESETS: readonly BackgroundPreset[] = [
  { id: 'aurora', name: '极光', cssVar: 'var(--wy-bg-preset-aurora)' },
  { id: 'emerald', name: '翡翠', cssVar: 'var(--wy-bg-preset-emerald)' },
  { id: 'sapphire', name: '蓝宝石', cssVar: 'var(--wy-bg-preset-sapphire)' },
  { id: 'amethyst', name: '紫水晶', cssVar: 'var(--wy-bg-preset-amethyst)' },
  { id: 'amber', name: '琥珀', cssVar: 'var(--wy-bg-preset-amber)' },
  { id: 'sunrise', name: '日出', cssVar: 'var(--wy-bg-preset-sunrise)' },
]

export const DEFAULT_PRESET_ID = 'aurora'

/** 本地图片存储上限（localStorage 约 5MB，留足余量） */
export const MAX_BACKGROUND_BYTES = 1_200_000
/** 原始文件上限（超过则直接拒绝，避免无意义的压缩尝试） */
export const MAX_SOURCE_BYTES = 12_000_000
const MAX_EDGE = 1920
const JPEG_QUALITY = 0.82

export function presetCss(presetId: string): string {
  const preset = BACKGROUND_PRESETS.find((item) => item.id === presetId) ?? BACKGROUND_PRESETS[0]
  return preset?.cssVar ?? 'var(--wy-bg-preset-aurora)'
}

/** 转义为安全的 CSS url() 值，只允许 http/https/data:image */
export function toSafeUrlValue(raw: string): string | null {
  const value = raw.trim()
  if (!value) return null
  const isAllowed =
    /^https?:\/\//i.test(value) || /^data:image\/(png|jpe?g|webp|gif);base64,/i.test(value)
  if (!isAllowed) return null
  const escaped = value.replace(/\\/g, '%5C').replace(/"/g, '%22').replace(/[\r\n\s]+/g, '')
  return `url("${escaped}")`
}

/** 校验 CSS 背景值是否由本工具生成（读取 localStorage 时的防御） */
export function isSafeBackgroundValue(value: string): boolean {
  return /^url\("(https?:\/\/|data:image\/)[^"\\]{1,3000000}"\)$/.test(value)
}

export function bytesOfDataUrl(dataUrl: string): number {
  const index = dataUrl.indexOf(',')
  return index < 0 ? 0 : Math.floor((dataUrl.length - index - 1) * 0.75)
}

/** 本地图片 → 压缩 → dataURL（长边 ≤1920，JPEG） */
export async function compressImageFile(file: File): Promise<string> {
  if (!file.type.startsWith('image/')) {
    throw new Error('请选择图片文件')
  }
  if (file.size > MAX_SOURCE_BYTES) {
    throw new Error('图片过大（超过 12MB），请先压缩后再试')
  }

  const objectUrl = URL.createObjectURL(file)
  try {
    const image = await loadImage(objectUrl)
    const scale = Math.min(1, MAX_EDGE / Math.max(image.width, image.height))
    const width = Math.max(1, Math.round(image.width * scale))
    const height = Math.max(1, Math.round(image.height * scale))

    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const context = canvas.getContext('2d')
    if (!context) throw new Error('浏览器不支持图片处理')
    context.drawImage(image, 0, 0, width, height)

    const dataUrl = canvas.toDataURL('image/jpeg', JPEG_QUALITY)
    if (bytesOfDataUrl(dataUrl) > MAX_BACKGROUND_BYTES) {
      throw new Error('压缩后仍超过 1.2MB，请换一张更小的图片')
    }
    return dataUrl
  } finally {
    URL.revokeObjectURL(objectUrl)
  }
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('图片加载失败'))
    image.src = src
  })
}
