import { fileURLToPath, URL } from 'node:url';

import vue from '@vitejs/plugin-vue';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const apiBase = env.VITE_API_BASE || 'http://localhost:8000';

  // HMR 配置：
  // - 反代场景（VITE_HMR_HOST=<公共域名>）走 wss 公共入口，避免浏览器
  //   fallback 到 localhost:5173 连不上
  // - VITE_HMR_DISABLE=1 彻底禁用，反代不转发 ws upgrade 时也没控制台噪音
  // - 默认本地开发走同源 ws，无需配置
  const hmrHost = env.VITE_HMR_HOST;
  const hmrClientPort = env.VITE_HMR_CLIENT_PORT
    ? Number(env.VITE_HMR_CLIENT_PORT)
    : undefined;
  const hmrProtocol = (env.VITE_HMR_PROTOCOL as 'ws' | 'wss' | undefined) || 'wss';
  const hmrDisabled = env.VITE_HMR_DISABLE === '1';

  const hmr = hmrDisabled
    ? false
    : hmrHost
      ? { host: hmrHost, clientPort: hmrClientPort, protocol: hmrProtocol }
      : true;

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      port: 5173,
      allowedHosts: ['webling.955id.com'],
      hmr,
      proxy: {
        // 后端冷启动 + 声纹懒加载可能几秒到十几秒，放宽 proxy 超时避免前端吃 504
        '/api': { target: apiBase, changeOrigin: true, timeout: 120_000, proxyTimeout: 120_000 },
        '/ws/chat': { target: apiBase.replace(/^http/, 'ws'), ws: true, changeOrigin: true },
        '/ws/asr': { target: apiBase.replace(/^http/, 'ws'), ws: true, changeOrigin: true },
        '/static': { target: apiBase, changeOrigin: true },
        '/docs': { target: apiBase, changeOrigin: true },
        '/openapi.json': { target: apiBase, changeOrigin: true },
      },
    },
  };
});
