import { ChatApi, ChatSocket, HttpClient, type ServerEvent } from '@webling/core';

import { useAuthStore } from '@/stores/auth';

const apiBase = import.meta.env.VITE_API_BASE?.toString().replace(/\/$/, '') || '';
const wsBase =
  import.meta.env.VITE_WS_BASE?.toString().replace(/\/$/, '') ||
  (apiBase
    ? apiBase.replace(/^http/, 'ws')
    : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`);

// getToken 是个函数，每次请求都现取一次 —— 支持 embed token 过期自动续签，
// 以及主站这种根本不登录场景（返回 null，后端 dev 模式兜底）。
async function getToken(): Promise<string | null> {
  // useAuthStore 需要 Pinia 已经 installed 才能调用；本 module 在 main.ts 里
  // 挂 Pinia 之后才被用到（HttpClient / ChatSocket 都是懒构造），因此没问题。
  const auth = useAuthStore();
  return auth.getToken(apiBase);
}

export const http = new HttpClient({ baseUrl: apiBase, getToken });
export const chatApi = new ChatApi(http);

export function createChatSocket(sessionId: string, onEvent: (e: ServerEvent) => void) {
  return new ChatSocket({
    baseUrl: wsBase,
    sessionId,
    onEvent,
    getToken,
  });
}
