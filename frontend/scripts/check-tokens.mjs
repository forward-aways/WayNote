/**
 * 设计令牌守卫（两道检查）：
 * 1) 禁止在 src 下（tokens.css / element.css 除外）出现硬编码十六进制色值；
 * 2) 所有 var(--wy-*) 引用必须能在 tokens.css 中找到定义（防止重命名后静默失效）。
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

if (failed) process.exit(1)

console.log(`tokens check passed（${definedTokens.size} 个令牌，引用全部有定义）`)
