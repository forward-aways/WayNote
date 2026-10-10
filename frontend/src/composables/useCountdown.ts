import { onUnmounted, ref } from 'vue'

/**
 * 秒级倒计时（验证码重发冷却）。
 *
 * 起点由服务端返回（`cooldown_seconds`），前端不自己发明冷却时长——
 * 服务端限流才是权威，这里只是把它可视化，避免用户点了没反应。
 */
export function useCountdown() {
  const seconds = ref(0)
  let timer: ReturnType<typeof setInterval> | null = null

  function stop() {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
  }

  function start(from: number) {
    stop()
    seconds.value = Math.max(0, Math.floor(from))
    if (seconds.value === 0) return
    timer = setInterval(() => {
      seconds.value -= 1
      if (seconds.value <= 0) stop()
    }, 1000)
  }

  onUnmounted(stop)

  return { seconds, start, stop }
}
