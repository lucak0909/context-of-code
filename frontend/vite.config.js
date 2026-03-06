import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy API calls to the Flask backend during development.
// Change VITE_API_URL in .env to point at the production VM instead.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:5000',
      '/health': 'http://localhost:5000',
    },
  },
})
