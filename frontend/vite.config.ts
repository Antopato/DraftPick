import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In local dev the frontend talks to the backend through this proxy, so the
// app can use relative /api and /ws URLs. In production set VITE_API_URL.
const proxyTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: proxyTarget, changeOrigin: true },
      '/ws': { target: proxyTarget, ws: true },
    },
  },
})
