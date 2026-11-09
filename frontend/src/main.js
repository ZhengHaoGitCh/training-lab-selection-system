import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import { bindAuth } from './api/http'
import { useAuthStore } from './stores/auth'
import './styles/theme.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
bindAuth(() => useAuthStore(pinia))
app.use(router)
app.use(ElementPlus, { locale: zhCn })

for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, component)
}

app.mount('#app')
