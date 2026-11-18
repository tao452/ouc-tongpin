import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// OUC同频 · 管理端（admin-web）构建配置
// CI 在 apps/admin-web 目录下执行 `npm ci && npm run lint && npm run test && npm run build`
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: true
  },
  build: {
    outDir: 'dist',
    sourcemap: false
  }
})
