// 拉取 HarmonyOS Sans SC 拆分版 webfont 到 public/fonts/harmonyos-sans-sc/
//
// 为什么自托管：该字体只有 CDN 分发，而国内实测 CDN 分片速度约 50KB/s（首屏换字体要 4~10s）；
// 放到本站 nginx 后同样体量约 1s。字体文件不入库（见 .gitignore），本脚本是唯一获取入口。
//
// 用法：node scripts/fetch-fonts.mjs        （已存在的分片会跳过）
// 许可：HarmonyOS Sans 由华为发布，允许免费商用；包内 LICENSE 一并下载，勿删。

import { mkdir, readFile, writeFile, access } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const PKG = 'harmonyos-sans-sc-webfont-splitted@1.1.0'
const CDN = `https://cdn.jsdelivr.net/npm/${PKG}/dist/`
// 四个面 = 代码实际用到的字重（400/500/600/700）：
// - 500：Element Plus 按钮/标签默认（--el-font-weight-primary）
// - 600：app 里十几处小标题/标签
// 缺 Medium/Semibold 时 500 会落到 Regular(400)、600 会落到 Bold(700)
// ——"写的字重 ≠ 渲染字重"，观感不一致（2026-10-13 补齐）
const WEIGHTS = ['Regular', 'Medium', 'Semibold', 'Bold']
const OUT_DIR = join(fileURLToPath(new URL('..', import.meta.url)), 'public', 'fonts', 'harmonyos-sans-sc')
const CONCURRENCY = 6

async function exists(path) {
  try {
    await access(path)
    return true
  } catch {
    return false
  }
}

async function download(url, dest, { skipExisting = true } = {}) {
  if (skipExisting && (await exists(dest))) return 'skip'
  const res = await fetch(url)
  if (!res.ok) throw new Error(`下载失败 ${res.status} ${url}`)
  const buffer = Buffer.from(await res.arrayBuffer())
  await mkdir(dirname(dest), { recursive: true })
  await writeFile(dest, buffer)
  return `ok ${(buffer.length / 1024).toFixed(0)}KB`
}

async function runPool(tasks, limit) {
  const queue = [...tasks]
  const workers = Array.from({ length: limit }, async () => {
    while (queue.length) {
      const task = queue.shift()
      if (task) await task()
    }
  })
  await Promise.all(workers)
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true })
  const chunks = []

  for (const weight of WEIGHTS) {
    const cssName = `${weight}.css`
    const cssPath = join(OUT_DIR, cssName)
    console.log(`· ${cssName}`)
    await download(CDN + cssName, cssPath, { skipExisting: false })
    const css = await readFile(cssPath, 'utf8')
    const refs = [...css.matchAll(/url\(([^)]+)\)/g)]
      .map((m) => m[1].replace(/["']/g, '').replace(/^\.\//, ''))
      .filter((name) => name.endsWith('.woff2'))
    console.log(`  引用 ${refs.length} 个分片`)
    for (const ref of refs) {
      chunks.push(() => download(CDN + ref, join(OUT_DIR, ref)))
    }
  }

  // LICENSE（许可要求随字体保留）
  chunks.push(() => download(`https://cdn.jsdelivr.net/npm/${PKG}/LICENSE`, join(OUT_DIR, 'LICENSE')))
  chunks.push(() =>
    download(`https://cdn.jsdelivr.net/npm/${PKG}/package.json`, join(OUT_DIR, 'package.json')),
  )

  let done = 0
  const total = chunks.length
  await runPool(
    chunks.map((task) => async () => {
      await task()
      done += 1
      if (done % 20 === 0 || done === total) console.log(`  进度 ${done}/${total}`)
    }),
    CONCURRENCY,
  )

  console.log(`完成 → ${OUT_DIR}`)
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
