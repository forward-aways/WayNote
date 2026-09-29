/** 统一日志出口：开发全量、生产仅 warn/error；彩色前缀与设计令牌同源（不硬编码色值） */
type Level = 'debug' | 'info' | 'warn' | 'error'

const isDev = import.meta.env.DEV
const ORDER: Record<Level, number> = { debug: 0, info: 1, warn: 2, error: 3 }
const MIN_LEVEL: Level = isDev ? 'debug' : 'warn'

/** 颜色从 tokens.css 的 CSS 变量读取（延迟到首次输出，确保样式已注入），回退到语义色名 */
function tokenColor(name: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

let cachedStyles: Record<Level, string> | null = null

function getStyles(): Record<Level, string> {
  if (!cachedStyles) {
    cachedStyles = {
      debug: `color:${tokenColor('--wy-ink-3', 'gray')}`,
      info: `color:${tokenColor('--wy-jade', 'steelblue')}`,
      warn: `color:${tokenColor('--wy-sun-strong', 'orange')};font-weight:600`,
      error: `color:${tokenColor('--wy-danger', 'crimson')};font-weight:600`,
    }
  }
  return cachedStyles
}

export interface AppLogger {
  debug: (message: string, ...args: unknown[]) => void
  info: (message: string, ...args: unknown[]) => void
  warn: (message: string, ...args: unknown[]) => void
  error: (message: string, ...args: unknown[]) => void
}

export function createLogger(scope: string): AppLogger {
  const emit = (level: Level, message: string, ...args: unknown[]) => {
    if (ORDER[level] < ORDER[MIN_LEVEL]) return
    const prefix = `%c[waynote·${scope}]%c ${message}`
    const style = getStyles()[level]
    const reset = 'color:inherit'
    if (level === 'error') console.error(prefix, style, reset, ...args)
    else if (level === 'warn') console.warn(prefix, style, reset, ...args)
    else console.log(prefix, style, reset, ...args)
  }

  return {
    debug: (message, ...args) => emit('debug', message, ...args),
    info: (message, ...args) => emit('info', message, ...args),
    warn: (message, ...args) => emit('warn', message, ...args),
    error: (message, ...args) => emit('error', message, ...args),
  }
}

export const logger = createLogger('app')
