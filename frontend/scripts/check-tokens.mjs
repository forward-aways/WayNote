/**
 * 设计令牌守卫：禁止在 src 下（tokens.css / element.css 除外）出现硬编码十六进制色值，
 * 统一走 --wy-* 变量，防止样式体系腐化。用法：npm run check:tokens
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const srcDir = fileURLToPath(new URL('../src', import.meta.url))
const ALLOW = new Set(['styles/tokens.css', 'styles/element.css'])
const HEX_PATTERN = /#[0-9a-fA-F]{3,8}\b/g
const violations = []

function walk(dir) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) {
      walk(full)
      continue
    }
    if (!/\.(vue|ts|css)$/.test(entry)) continue
    const rel = relative(srcDir, full).split(sep).join('/')
    if (ALLOW.has(rel)) continue
    readFileSync(full, 'utf8')
      .split(/\r?\n/)
      .forEach((line, index) => {
        const matches = line.match(HEX_PATTERN)
        if (matches) violations.push(`${rel}:${index + 1}  ${matches.join(', ')}`)
      })
  }
}

walk(srcDir)

if (violations.length > 0) {
  console.error('发现硬编码颜色，请改用 src/styles/tokens.css 中的 --wy-* 变量：')
  for (const item of violations) console.error('  ' + item)
  process.exit(1)
}

console.log('tokens check passed')
