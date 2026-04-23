import { defineStore } from 'pinia';
import { ref } from 'vue';

const STORAGE_KEY = 'webling:auth';
// 到期前多少秒主动刷新，避免等 401
const RENEW_GUARD_SECONDS = 30;

interface PersistedAuth {
  token: string;
  expiresAt: number; // epoch seconds
  tenantId?: string;
  apiKey?: string; // 只有 embed 场景会带，主站未登录时为空
}

function load(): PersistedAuth | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedAuth;
    if (typeof parsed.token !== 'string' || typeof parsed.expiresAt !== 'number') return null;
    return parsed;
  } catch {
    return null;
  }
}

function save(v: PersistedAuth | null): void {
  try {
    if (v) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(v));
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* sessionStorage 可能在无痕模式下报错，吞掉即可 */
  }
}

/**
 * M6 鉴权 store。主站（公开 demo）默认没 token，HttpClient / ChatSocket 的
 * getToken 在没 token 时返回 null，后端配合 dev 环境放行；embed 场景会在页面
 * 启动时先调 /api/embed/token 拿到 JWT 再传入。
 */
export const useAuthStore = defineStore('auth', () => {
  const current = ref<PersistedAuth | null>(load());

  function isExpired(v: PersistedAuth | null): boolean {
    if (!v) return true;
    return Date.now() / 1000 >= v.expiresAt - RENEW_GUARD_SECONDS;
  }

  async function fetchEmbedToken(apiKey: string, apiBase: string): Promise<string> {
    const res = await fetch(`${apiBase.replace(/\/$/, '')}/api/embed/token`, {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
    });
    if (!res.ok) {
      throw new Error(`embed token ${res.status}: ${await res.text().catch(() => '')}`);
    }
    const data = (await res.json()) as { token: string; expires_in: number; tenant_id: string };
    const next: PersistedAuth = {
      token: data.token,
      expiresAt: Date.now() / 1000 + data.expires_in,
      tenantId: data.tenant_id,
      apiKey,
    };
    current.value = next;
    save(next);
    return next.token;
  }

  async function getToken(apiBase?: string): Promise<string | null> {
    const v = current.value;
    if (!v) return null;
    if (!isExpired(v)) return v.token;
    // 到期且手里有 apiKey → 自动续签；没 apiKey 就只能返回 null，让调用方处理
    if (v.apiKey && apiBase) {
      try {
        return await fetchEmbedToken(v.apiKey, apiBase);
      } catch {
        current.value = null;
        save(null);
        return null;
      }
    }
    current.value = null;
    save(null);
    return null;
  }

  function clear(): void {
    current.value = null;
    save(null);
  }

  return { current, fetchEmbedToken, getToken, clear };
});
