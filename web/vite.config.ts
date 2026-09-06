import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'
import { fileURLToPath, URL } from 'node:url'

// base is './' so the built app works from any path, including the Cloud Run root and a
// file:// load inside the native shells. HashRouter pairs with it (PLAN.md task 0.10).
export default defineConfig({
  base: './',
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'prompt',
      includeAssets: ['favicon.svg', 'gate.svg'],
      manifest: {
        name: 'HOLD',
        short_name: 'HOLD',
        description: 'The cheapest legal shooting order, and the statute behind every verdict.',
        theme_color: '#101010',
        background_color: '#101010',
        display: 'standalone',
        orientation: 'portrait',
        start_url: './index.html',
        scope: './',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon-512-maskable.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
        // The app shell is precached. API answers are cached by TanStack Query in IndexedDB,
        // not by the service worker, so a stale verdict is always labelled with its time.
        navigateFallback: 'index.html',
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [],
      },
      devOptions: { enabled: false },
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@fixtures': fileURLToPath(new URL('../data/fixtures', import.meta.url)),
      '@demo': fileURLToPath(new URL('../data/demo', import.meta.url)),
    },
  },
  server: {
    fs: { allow: ['..'] },
    proxy: {
      '/api': {
        target: process.env.VITE_DEV_API ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: { outDir: 'dist', sourcemap: false, target: 'es2022' },
})
