import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus, { ElMessage } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import router from './router'
import { reportError } from './api/clientLog'
import { isApiError } from './api/error'
import { logger } from './utils/logger'
import './styles/tokens.css'
import 'element-plus/dist/index.css'
import './styles/base.css'
import './styles/element.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// ===== 全局异常兜底：记录 + 上报 + 节流提示 =====
let lastToastAt = 0

function notifyOnce() {
  const now = Date.now()
  if (now - lastToastAt < 3000) return
  lastToastAt = now
  ElMessage.error('页面出现异常，请刷新重试')
}

app.config.errorHandler = (error, _instance, info) => {
  logger.error('vue error', error, info)
  reportError('vue', error)
  notifyOnce()
}

window.addEventListener('unhandledrejection', (event) => {
  const reason: unknown = event.reason
  // API 错误已在拦截器记录/提示，不重复上报
  if (isApiError(reason)) return
  logger.error('unhandled rejection', reason)
  reportError('unhandledrejection', reason)
})

window.addEventListener('error', (event) => {
  logger.error('window error', event.message, event.filename, event.lineno)
  reportError('window', event.error ?? event.message ?? 'unknown window error')
})

router.onError((error) => {
  logger.error('router error', error)
  reportError('window', error)
})

app.mount('#app')
