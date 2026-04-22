import { ChatApi, ChatSocket, HttpClient, type ServerEvent } from '@webling/core';

const apiBase = import.meta.env.VITE_API_BASE?.toString().replace(/\/$/, '') || '';
const wsBase =
  import.meta.env.VITE_WS_BASE?.toString().replace(/\/$/, '') ||
  (apiBase
    ? apiBase.replace(/^http/, 'ws')
    : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`);

export const http = new HttpClient({ baseUrl: apiBase });
export const chatApi = new ChatApi(http);

export function createChatSocket(sessionId: string, onEvent: (e: ServerEvent) => void) {
  return new ChatSocket({
    baseUrl: wsBase,
    sessionId,
    onEvent,
  });
}
