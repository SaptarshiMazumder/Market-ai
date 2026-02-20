import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/models': { target: 'http://localhost:5001', changeOrigin: true },
      '/api/train': { target: 'http://localhost:5001', changeOrigin: true },
      '/api/training-status': { target: 'http://localhost:5001', changeOrigin: true },
      '/api/debug': { target: 'http://localhost:5001', changeOrigin: true },
      '/api/generate': { target: 'http://localhost:5002', changeOrigin: true },
      '/api/upscale': { target: 'http://localhost:5002', changeOrigin: true },
      '/api/images': { target: 'http://localhost:5002', changeOrigin: true },
      '/api/template': { target: 'http://localhost:5003', changeOrigin: true },
    }
  }
})
