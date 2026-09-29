/**
 * 设计令牌守卫（三道检查）：
 * 1) 禁止在 src 下（tokens.css / element.css 除外）出现硬编码十六进制色值；
 * 2) 所有 var(--wy-*) 引用必须能在 tokens.css 中找到定义（防止重命名后静默失效）；
 * 3) 「宝石表面 + 边框」必须声明 background-origin: border-box
 *    （否则背景只铺 padding-box 并向外平铺，边框区显示渐变反向切片 = 深绿"假边框"）。
 * 用法：npm run check:tokens
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const srcDir = fileURLToPath(new URL('../src', import.meta.url))
// utils/theme.ts 例外：主题派生算法的墨色常量（#052a1b / #ffffff），非样式色值，
// 与 tokens.css 的 --wy-ink-1 / --wy-surface 语义一致，改动需同步审计脚本。
const ALLOW = new Set(['styles/tokens.css', 'styles/element.css', 'utils/theme.ts'])
const HEX_PATTERN = /#[0-9a-fA-F]{3,8}\b/g
const VAR_USE_PATTERN = /var\(\s*(--wy-[a-z0-9-]+)/gi
const VAR_DEF_PATTERN = /(--wy-[a-z0-9-]+)\s*:/gi

const hexViolations = []
const usedTokens = new Map() // token -> first file:line
const definedTokens = new Set()
const jadeBorderViolations = []

/* ===== 第 3 道检查用的轻量块扫描（深度感知，处理嵌套 @media） ===== */
const JADE_SURFACE = /var\(--wy-(jade-surface|grad-brand)\)/
const ORIGIN_DECL = /^background-origin\s*:\s*border-box/

/** 该声明是否"真的画了边框"（border: none / 0 不算） */
function borderDeclared(decl) {
  const match = /^border(-(top|right|bottom|left))?(-width|-color|-style)?\s*:\s*(.+)$/.exec(decl)
  if (!match) return false
  return !/^(none|0|0px)\b/.test((match[4] ?? '').trim())
}

function collectBlocks(text, rel) {
  const blocks = []
  const stack = []
  text.split(/\r?\n/).forEach((raw, index) => {
    const line = raw.trim()
    if (!line || line.startsWith('/*') || line.startsWith('*') || line.startsWith('//')) return
    if (line.endsWith('{')) {
      stack.push({ selector: line.slice(0, -1).trim(), decls: [], line: index + 1 })
      return
    }
    if (line.startsWith('}')) {
      const block = stack.pop()
      if (block) blocks.push({ ...block, rel })
      return
    }
    const current = stack[stack.length - 1]
    if (current) {
      for (const decl of line.split(';')) {
        const value = decl.trim()
        if (value) current.decls.push(value)
      }
    }
  })
  return blocks
}

function checkJadeBorder(blocks) {
  for (const block of blocks) {
    if (!block.decls.some((decl) => JADE_SURFACE.test(decl))) continue
    const hasBorder = block.decls.some(borderDeclared)
    const hasOrigin = block.decls.some((decl) => ORIGIN_DECL.test(decl))
    if (hasBorder && !hasOrigin) {
      jadeBorderViolations.push(`${block.rel}:${block.line}  ${block.selector}`)
    }
  }
}

function walk(dir) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) {
      walk(full)
      continue
    }
    if (!/\.(vue|ts|css)$/.test(entry)) continue
    const rel = relative(srcDir, full).split(sep).join('/')
    const text = readFileSync(full, 'utf8')

    if (rel === 'styles/tokens.css') {
      for (const match of text.matchAll(VAR_DEF_PATTERN)) {
        definedTokens.add(match[1])
      }
    }

    if (rel.endsWith('.vue') || rel.endsWith('.css')) {
      checkJadeBorder(collectBlocks(text, rel))
    }

    text.split(/\r?\n/).forEach((line, index) => {
      if (!ALLOW.has(rel)) {
        const hexes = line.match(HEX_PATTERN)
        if (hexes) hexViolations.push(`${rel}:${index + 1}  ${hexes.join(', ')}`)
      }
      for (const match of line.matchAll(VAR_USE_PATTERN)) {
        if (!usedTokens.has(match[1])) usedTokens.set(match[1], `${rel}:${index + 1}`)
      }
    })
  }
}

walk(srcDir)

const missingTokens = [...usedTokens.entries()].filter(([token]) => !definedTokens.has(token))
let failed = false

if (hexViolations.length > 0) {
  failed = true
  console.error('发现硬编码颜色，请改用 src/styles/tokens.css 中的 --wy-* 变量：')
  for (const item of hexViolations) console.error('  ' + item)
}

if (missingTokens.length > 0) {
  failed = true
  console.error('发现未定义的令牌引用（重命名后遗漏？）：')
  for (const [token, where] of missingTokens) console.error(`  ${token}  <- ${where}`)
}

if (jadeBorderViolations.length > 0) {
  failed = true
  console.error('发现「宝石表面 + 边框」但未声明 background-origin: border-box（边框区会平铺出深绿"假边框"）：')
  for (const item of jadeBorderViolations) console.error('  ' + item)
}

if (failed) process.exit(1)

console.log(`tokens check passed（${definedTokens.size} 个令牌，引用全部有定义）`)
