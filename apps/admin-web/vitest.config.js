import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.js'],
    setupFiles: ['tests/setup.js'],
    // Transform Element Plus imports so async-validator uses Vite's CJS interop.
    server: { deps: { inline: ['element-plus'] } },
    clearMocks: true,
    restoreMocks: true,
  },
})
