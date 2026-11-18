import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
<<<<<<< HEAD
import router from './router'

const app = createApp(App)
app.use(ElementPlus)
app.use(router)
app.mount('#app')
=======

// 全量注册 Element Plus（含 el-row/el-col/el-card/el-icon 等，DataBoard.vue 用到）
// 后续可按需引入（unplugin-auto-import + unplugin-vue-components）优化体积
createApp(App).use(ElementPlus).mount('#app')
>>>>>>> develop
