/**
 * iframe 宿主页（embed.html）的 Vite MPA 配置：一个完整 Vue 应用，
 * 复用 apps/web 的组件与 store，在 380×620 面板里跑 Live2D + TTS + 情绪。
 *
 * 构建产物（dist/）：
 *   - embed.html
 *   - assets/embed-[hash].js / embed-[hash].css
 *
 * 生产由 backend 挂在 /embed/，第三方 iframe 直接指向
 * https://<host>/embed/embed.html?api_key=...&character_id=...
 */
import { fileURLToPath, URL } from 'node:url';

import vue from '@vitejs/plugin-vue';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [vue()],
  // publicDir 这里指 apps/embed/public，dev 时自己的 demo.html 等静态能访问。
  // build 产物里 public 的内容会被拷到 dist 根；avatars/live2dcubismcore 走 build:copy-assets 脚本从 web 那边复制。
  publicDir: 'public',
  resolve: {
    alias: {
      // 复用 apps/web 的组件（AvatarStage/InputBar/MessageList）和 store（chat/auth）。
      // 这些 @/ 路径在 embed 里能正常 resolve，因为它们就是从 web 那边相对来引用的。
      '@': fileURLToPath(new URL('../web/src', import.meta.url)),
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: fileURLToPath(new URL('./embed.html', import.meta.url)),
    },
  },
  server: {
    port: 5174,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8000', ws: true, changeOrigin: true },
      '/static': { target: 'http://localhost:8000', changeOrigin: true },
      // dev 时 avatars / live2dcubismcore 走到 web 的 5173
      '/avatars': { target: 'http://localhost:5173', changeOrigin: true },
      '/live2dcubismcore.min.js': { target: 'http://localhost:5173', changeOrigin: true },
    },
  },
});
