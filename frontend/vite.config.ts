import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In dev, proxy API calls to the FastAPI server so the browser sees a single
// origin (localhost:5173) — mirroring the production single-origin deployment.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
