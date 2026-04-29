import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import naive from 'naive-ui'
import 'element-plus/dist/index.css'
import './style.css'
import App from './App.vue'
import router from './router'
import { initializeAuth } from './utils/auth-bootstrap'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
await initializeAuth()
app.use(router)
app.use(ElementPlus)
app.use(naive)

app.mount('#app')
