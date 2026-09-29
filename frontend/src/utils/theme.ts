/**
 * 主题色派生（与设计审计脚本同源算法）：
 * 由唯一基色派生出「宝石表面 / 高光 / 深色文字 / 弱底 / 宝石面墨色」，
 * 并保证以下对比度全部 ≥4.5:1（WCAG AA）：
 *   - 深色 vs 白（白字场景的替代：深色文字用于浅底）
 *   - 深色 vs 弱底（chip 文字）
 *   - 宝石面墨色 vs 两个渐变端（按钮/胶囊上的文字与图标）
 * 因此用户自定义任意主题色时，可读性都不会失控。
 */

export interface DerivedTheme {
  jade: string
  bright: string
  deep: string
  weak: string
  onJade: string
}

interface Rgb {
  r: number
  g: number
  b: number
}

const WHITE: Rgb = { r: 255, g: 255, b: 255 }
const BLACK: Rgb = { r: 0, g: 0, b: 0 }
const INK_DARK = '#052a1b'
const INK_LIGHT = '#ffffff'

export const ACCENT_PRESETS = [
  { id: 'emerald', name: '翡翠', cssVar: 'var(--wy-accent-preset-emerald)' },
  { id: 'teal', name: '青玉', cssVar: 'var(--wy-accent-preset-teal)' },
  { id: 'sapphire', name: '蓝宝石', cssVar: 'var(--wy-accent-preset-sapphire)' },
  { id: 'amethyst', name: '紫水晶', cssVar: 'var(--wy-accent-preset-amethyst)' },
  { id: 'amber', name: '琥珀', cssVar: 'var(--wy-accent-preset-amber)' },
  { id: 'coral', name: '珊瑚', cssVar: 'var(--wy-accent-preset-coral)' },
  { id: 'sakura', name: '樱粉', cssVar: 'var(--wy-accent-preset-sakura)' },
  { id: 'graphite', name: '石墨', cssVar: 'var(--wy-accent-preset-graphite)' },
] as const

export const DEFAULT_ACCENT_ID = 'emerald'

export function parseHexColor(value: string): Rgb | null {
  const text = value.trim()
  const match = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(text)
  if (!match) return null
  const hex = match[1] ?? ''
  const full =
    hex.length === 3
      ? hex
          .split('')
          .map((ch) => ch + ch)
          .join('')
      : hex
  return {
    r: parseInt(full.slice(0, 2), 16),
    g: parseInt(full.slice(2, 4), 16),
    b: parseInt(full.slice(4, 6), 16),
  }
}

function toHex(color: Rgb): string {
  const part = (value: number) =>
    Math.max(0, Math.min(255, Math.round(value)))
      .toString(16)
      .padStart(2, '0')
  return `#${part(color.r)}${part(color.g)}${part(color.b)}`
}

function mix(base: Rgb, other: Rgb, ratioOther: number): Rgb {
  return {
    r: base.r * (1 - ratioOther) + other.r * ratioOther,
    g: base.g * (1 - ratioOther) + other.g * ratioOther,
    b: base.b * (1 - ratioOther) + other.b * ratioOther,
  }
}

function srgb(channel: number): number {
  const c = channel / 255
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
}

function luminance(color: Rgb): number {
  return 0.2126 * srgb(color.r) + 0.7152 * srgb(color.g) + 0.0722 * srgb(color.b)
}

function contrast(a: Rgb, b: Rgb): number {
  const l1 = luminance(a)
  const l2 = luminance(b)
  const hi = Math.max(l1, l2)
  const lo = Math.min(l1, l2)
  return (hi + 0.05) / (lo + 0.05)
}

function asRgb(hex: string): Rgb {
  return parseHexColor(hex) ?? { r: 34, g: 197, b: 94 }
}

const MIN_CONTRAST = 4.5
const MAX_STEPS = 20

/** 基色 → 主题（全部派生值与对比度保障在函数内完成） */
export function deriveTheme(baseHex: string): DerivedTheme {
  const base = asRgb(baseHex)
  const inkDark = asRgb(INK_DARK)
  const inkLight = asRgb(INK_LIGHT)

  let jade = mix(base, WHITE, 0.14)
  let bright = mix(base, WHITE, 0.38)
  const weak = mix(base, WHITE, 0.84)

  // 选择更接近达标的墨色分支，并迭代调整宝石面直到两个渐变端都达标
  const useWhiteInk = contrast(inkLight, jade) > contrast(inkDark, jade)
  const ink = useWhiteInk ? inkLight : inkDark
  const toward = useWhiteInk ? BLACK : WHITE
  for (let step = 0; step < MAX_STEPS; step += 1) {
    if (contrast(ink, jade) >= MIN_CONTRAST && contrast(ink, bright) >= MIN_CONTRAST) break
    jade = mix(jade, toward, 0.06)
    bright = mix(bright, toward, 0.06)
  }

  // 深色：先加深 38%，再按需继续加深直到「白字」与「弱底文字」都达标
  let deep = mix(base, BLACK, 0.38)
  for (let step = 0; step < MAX_STEPS; step += 1) {
    if (contrast(deep, WHITE) >= MIN_CONTRAST && contrast(deep, weak) >= MIN_CONTRAST) break
    deep = mix(deep, BLACK, 0.08)
  }

  return {
    jade: toHex(jade),
    bright: toHex(bright),
    deep: toHex(deep),
    weak: toHex(weak),
    onJade: toHex(ink),
  }
}

const CSS_VARS: Array<[keyof DerivedTheme, string]> = [
  ['jade', '--wy-jade'],
  ['bright', '--wy-jade-bright'],
  ['deep', '--wy-primary'],
  ['deep', '--wy-primary-strong'],
  ['weak', '--wy-primary-weak'],
  ['onJade', '--wy-on-jade'],
]

export function applyTheme(theme: DerivedTheme, baseHex: string, root: HTMLElement): void {
  root.style.setProperty('--wy-accent-base', baseHex)
  for (const [key, cssVar] of CSS_VARS) {
    root.style.setProperty(cssVar, theme[key])
  }
}

export function clearTheme(root: HTMLElement): void {
  root.style.removeProperty('--wy-accent-base')
  for (const [, cssVar] of CSS_VARS) {
    root.style.removeProperty(cssVar)
  }
}
