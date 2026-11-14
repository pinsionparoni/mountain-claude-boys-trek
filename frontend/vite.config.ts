import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Let a phone open the dev server through a Cloudflare quick tunnel
    // (https://<random>.trycloudflare.com, see SETUP.md). Vite refuses
    // unknown host names by default; only this domain is added.
    allowedHosts: ['.trycloudflare.com'],
    // Forward /api/... to the FastAPI backend (uvicorn's default port), without
    // the /api prefix: the backend's routes are /chat, /customers/... .
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
