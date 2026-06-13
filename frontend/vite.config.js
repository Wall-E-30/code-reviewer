import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/optimize': 'http://127.0.0.1:7860',
      '/optimize_full': 'http://127.0.0.1:7860',
      '/reset': 'http://127.0.0.1:7860',
      '/step': 'http://127.0.0.1:7860',
      '/state': 'http://127.0.0.1:7860',
      '/run_benchmark': 'http://127.0.0.1:7860',
    }
  }
})
