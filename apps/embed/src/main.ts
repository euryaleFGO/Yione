/**
 * iframe 宿主页的 Vue 挂载入口。
 *
 * 启动流程：
 *   1. 从 URL query 读 api_key / character_id / api_base
 *   2. auth.fetchEmbedToken(apiKey, apiBase) 换 embed JWT
 *   3. EmbedApp 挂载，内部通过 chat store 建会话、连 WS、拿 TTS/嘴型/情绪
 *
 * 父页面通信走 postMessage：
 *   - 向父：ready / state / error / subtitle / speaker
 *   - 来自父：init(apiKey override) / send(text) / close
 */
import { createPinia } from 'pinia';
import { createApp } from 'vue';

import { useAuthStore } from '@/stores/auth';

import EmbedApp from './EmbedApp.vue';
import './style.css';

const app = createApp(EmbedApp);
const pinia = createPinia();
app.use(pinia);
app.mount('#app');

// EmbedApp 里会 useAuthStore().fetchEmbedToken() —— 这里什么都不用做，
// URL query 的解析在组件 onMounted 里处理，方便在 Vue 响应式体系内做错误展示。
// 保留这个 import 是为了 tree-shaking 不把 auth store 裁掉（实际 EmbedApp 会用到）。
void useAuthStore;

// 通知父页面 iframe 已就绪。真正的 chat 运行状态走 EmbedApp 自己发 state 消息。
try {
  window.parent.postMessage({ type: 'webling:ready' }, '*');
} catch {
  // 跨源 parent 拒绝时 postMessage 直接丢弃；父页面会等 init 超时自行重试
}
