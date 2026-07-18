import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@live-master/ui': path.resolve(__dirname, '../../packages/ui/src'),
      '@live-master/shared': path.resolve(__dirname, '../../packages/shared/src'),
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    minify: 'terser',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          dnd: ['@dnd-kit/core', '@dnd-kit/sortable', '@dnd-kit/utilities'],
          supabase: ['@supabase/supabase-js'],
          query: ['@tanstack/react-query'],
          store: ['zustand'],
        },
      },
    },
  },
  server: {
    port: 3001,
    host: true,
    cors: true,
  },
})