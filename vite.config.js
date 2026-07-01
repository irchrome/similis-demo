import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base для GitHub Pages = '/<repo>/'. Дефолт /similis-demo/; или GHPAGES_BASE=/repo/ npm run deploy.
export default defineConfig({
  plugins: [react()],
  base: process.env.GHPAGES_BASE || '/similis-demo/',
  // Явный пустой PostCSS: не даёт Vite подхватить чужой ~/postcss.config.js (tailwind).
  css: { postcss: {} },
})
