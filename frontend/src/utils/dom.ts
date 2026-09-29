/** DOM 工具：把函数式 ref 的回调值解析成真实元素（组件 ref 拿到的是组件实例） */

function isElement(value: unknown): value is HTMLElement {
  return typeof HTMLElement !== 'undefined' && value instanceof HTMLElement
}

/**
 * 解析函数式 ref 的值：
 * - 原生元素 → 直接返回
 * - 组件实例（如 router-link）→ 返回其根元素 $el
 * - 其他（null / 文本 vnode 等）→ null
 */
export function resolveElement(value: unknown): HTMLElement | null {
  if (isElement(value)) return value
  const maybe = value as { $el?: unknown } | null | undefined
  const root = maybe?.$el
  return isElement(root) ? root : null
}
