import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

// 檢查是否存在憑證檔案
const certPath = path.resolve(__dirname, 'cert')
const keyPath = path.resolve(__dirname, 'key.pem')
const certExists = fs.existsSync(certPath) && fs.existsSync(keyPath)

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    ...(certExists && {
      https: {
        key: fs.readFileSync(keyPath),
        cert: fs.readFileSync(certPath)
      }
    })
  }
})