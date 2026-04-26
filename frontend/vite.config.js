import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test-setup.js',
  },
  server: {
    proxy: {
      '/turn': 'http://localhost:8001',
      '/session': 'http://localhost:8001',
      '/sessions': 'http://localhost:8001',
      '/topics': 'http://localhost:8001',
      '/providers': 'http://localhost:8001',
      '/tts-voices': 'http://localhost:8001',
      '/flashcards': 'http://localhost:8001',
      '/translate': 'http://localhost:8001',
      '/pronunciation': 'http://localhost:8001',
    },
  },
})
