/** 完成进度的唯一口径（ADR-20261012 §5.4）：
 *  所有进度 UI（天徽章 / 详情页头部 / 列表卡 / 我的页）都从这里取值，
 *  0 分母返回 null（不变量 I5），调用方据此隐藏进度 UI。 */

export interface Progress {
  done: number
  total: number
  /** 0..100 四舍五入；仅用于展示与进度条宽度 */
  percent: number
}

/** 由计数构造进度；total<=0 → null；done 夹取到 [0,total]，进度条永不越界 */
export function progressOfCounts(done: number, total: number): Progress | null {
  if (!Number.isFinite(total) || total <= 0) return null
  const safeTotal = Math.trunc(total)
  const safeDone = Math.min(Math.max(Math.trunc(done) || 0, 0), safeTotal)
  return {
    done: safeDone,
    total: safeTotal,
    percent: Math.round((safeDone / safeTotal) * 100),
  }
}

/** 由条目数组构造进度（口径与后端 done_count 一致：含待定地点） */
export function progressOf(items: readonly { done: boolean }[]): Progress | null {
  let done = 0
  for (const item of items) {
    if (item.done) done += 1
  }
  return progressOfCounts(done, items.length)
}
