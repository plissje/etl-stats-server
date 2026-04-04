import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '../', '')
  const apiTarget = env.VITE_API_PROXY || 'http://127.0.0.1:8000'
  return {
    envDir: '../',
    plugins: [react(), tailwindcss()],
    server: {
      allowedHosts: true,
      proxy: {
        '/api': apiTarget,
        '/health': apiTarget,
      },
    },
  }
})
