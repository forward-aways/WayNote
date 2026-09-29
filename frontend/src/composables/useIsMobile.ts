import { onBeforeUnmount, ref, type Ref } from 'vue'

/** 响应式移动端断点（默认 <768px），在组件 setup 中调用 */
export function useIsMobile(query = '(max-width: 767px)'): Ref<boolean> {
  const mql = window.matchMedia(query)
  const isMobile = ref(mql.matches)
  const onChange = (event: MediaQueryListEvent) => {
    isMobile.value = event.matches
  }
  mql.addEventListener('change', onChange)
  onBeforeUnmount(() => mql.removeEventListener('change', onChange))
  return isMobile
}
