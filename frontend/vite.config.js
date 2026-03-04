import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api/templates': 'http://localhost:5003',
      '/api/template-images': 'http://localhost:5003',
'/api/generate': 'http://localhost:5008',
      '/api/mask': 'http://localhost:5008',
      '/api/masks': 'http://localhost:5008',
      '/api/inpaint': 'http://localhost:5008',
      '/api/inpainted': 'http://localhost:5008',
      '/api/pipeline': 'http://localhost:5009',
    },
  },
})
