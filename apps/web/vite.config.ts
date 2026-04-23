import { fileURLToPath, URL } from 'node:url';

import vue from '@vitejs/plugin-vue';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const apiBase = env.VITE_API_BASE || 'http://localhost:8000';

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': { target: apiBase, changeOrigin: true },
        '/ws/chat': { target: apiBase.replace(/^http/, 'ws'), ws: true, changeOrigin: true },
        '/ws/asr': { target: apiBase.replace(/^http/, 'ws'), ws: true, changeOrigin: true },
        '/static': { target: apiBase, changeOrigin: true },
        '/docs': { target: apiBase, changeOrigin: true },
        '/openapi.json': { target: apiBase, changeOrigin: true },
      },
    },
  };
});
