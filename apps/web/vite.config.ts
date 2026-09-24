import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import { resolve } from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),

    // PWA Plugin — generates SW manifest + precache
    VitePWA({
      registerType: 'prompt',          // Show update prompt to user
      strategies: 'injectManifest',    // Use our custom sw.ts
      srcDir: 'src',
      filename: 'sw.ts',
      injectManifest: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,wasm}'],
      },
      manifest: {
        name: 'FLIP — Krishi Bhoomi Setu',
        short_name: 'FLIP',
        description: 'Farm Lifecycle Intelligence Platform — Smart Farming for India',
        theme_color: '#22c55e',
        background_color: '#0a0e1a',
        display: 'standalone',
        orientation: 'portrait-primary',
        start_url: '/',
        scope: '/',
        lang: 'en',
        categories: ['agriculture', 'productivity', 'utilities'],
        icons: [
          { src: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icons/icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
        shortcuts: [
          {
            name: 'Dashboard',
            url: '/',
            icons: [{ src: '/icons/icon-96x96.png', sizes: '96x96' }],
          },
          {
            name: 'Disaster Alerts',
            url: '/disaster',
            icons: [{ src: '/icons/icon-96x96.png', sizes: '96x96' }],
          },
        ],
      },
    }),
  ],

  resolve: {
    alias: {
      '@flip/shared-types': resolve(__dirname, '../../packages/shared-types/src'),
    },
  },

  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/graphql': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },

  build: {
    target: 'esnext',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-map': ['maplibre-gl'],
          'vendor-i18n': ['i18next', 'react-i18next', 'i18next-browser-languagedetector', 'i18next-http-backend'],
          'vendor-state': ['zustand'],
          'vendor-auth': ['oidc-client-ts'],
          'vendor-gql': ['graphql-request'],
        },
      },
    },
    // Increase chunk warning threshold for WASM-heavy builds
    chunkSizeWarningLimit: 2000,
  },

  worker: {
    format: 'es',
  },

  optimizeDeps: {
    exclude: ['maplibre-gl'],
  },
});
