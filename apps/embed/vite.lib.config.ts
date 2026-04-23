/**
 * Library 模式 —— Script tag 自启脚本（embed.js）和 Custom Element（web-component.js）。
 *
 * 这两个产物都是"宿主页 wrapper"，体积极小（<5KB gzip），不含 Vue/Live2D。
 * 真正的 chat 运行时在 iframe 里的 embed.html（vite.app.config.ts 产物）。
 *
 * 通过环境变量 ENTRY=index / ENTRY=web-component 切换入口：
 *   pnpm build:lib → 先后各跑一遍
 */
import { resolve } from 'node:path';

import { defineConfig } from 'vite';

const entry = process.env.ENTRY || 'index';

export default defineConfig({
  // library 模式下禁用 publicDir，避免把 web 的 5MB avatars 拷进 dist 又被覆盖
  publicDir: false,
  build: {
    outDir: 'dist',
    // 先跑 app build（已 emptyOutDir），两次 lib build 都不能清空
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, `src/${entry}.ts`),
      name: entry === 'index' ? 'WeblingEmbed' : 'WeblingComponent',
      formats: ['iife'],
      fileName: () => (entry === 'index' ? 'embed.js' : 'web-component.js'),
    },
    minify: 'esbuild',
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
  },
});
