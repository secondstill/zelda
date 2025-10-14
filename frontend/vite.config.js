import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: 'localhost',
    proxy: {
      '/api': {
        target: 'http://localhost:8091',
        changeOrigin: true,
        secure: false
      }
    }
    // Uncomment the following lines for HTTPS development
    // https: true,
    // For custom certificates, use:
    // https: {
    //   key: './localhost-key.pem',
    //   cert: './localhost.pem'
    // }
  }
})
