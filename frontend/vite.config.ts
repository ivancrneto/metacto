import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In dev, proxy API calls to the FastAPI server so the browser sees a single
// origin (localhost:5173) — this keeps the identity cookie first-party and
// mirrors the production single-origin deployment.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
