import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api/templates': 'http://localhost:5003',
      '/api/template-images': 'http://localhost:5003',
      '/api/z-turbo': 'http://localhost:5007',
      '/api/generate': 'http://localhost:5008',
    },
  },
})
