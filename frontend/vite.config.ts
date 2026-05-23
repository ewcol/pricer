import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/analyze-preview': 'http://localhost:8000',
      '/analyze-stream':  { target: 'http://localhost:8000', changeOrigin: true },
      '/analyze-item':    'http://localhost:8000',
      '/tracked-items':   'http://localhost:8000',
      '/track-item':      'http://localhost:8000',
      '/schedule-check':  'http://localhost:8000',
      '/cancel-check':    'http://localhost:8000',
      '/health':          'http://localhost:8000',
    }
  },
  build: {
    outDir: 'dist',
  }
})
