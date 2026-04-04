import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  // Load env from both current dir and parent to handle local vs docker build contexts
  const env = { ...loadEnv(mode, '../', ''), ...loadEnv(mode, '.', ''), ...process.env }
  
  const apiTarget = env.VITE_API_PROXY_HOST || env.VITE_API_PROXY || 'http://127.0.0.1:8000'
  const apiPrefix = env.VITE_API_PROXY || '/api'

  return {
    envDir: './', // Standardize to project root
    plugins: [react(), tailwindcss()],
    server: {
      allowedHosts: true,
      proxy: {
        [apiPrefix]: {
          target: apiTarget,
          changeOrigin: true,
          rewrite: (path) => apiPrefix === '/' ? path : path.replace(new RegExp(`^${apiPrefix}`), '/api')
        }
      },
    },
  }
})
