/**
 * Script tag / Custom Element（父）与 iframe 宿主页（EmbedApp，子）之间
 * 的 postMessage 协议。三形态共用同一个消息合约。
 *
 * - 父 → 子：target: 'webling' + type
 * - 子 → 父：source: 'webling' + type
 *
 * 加 target/source 是为了避免浏览器扩展 / 其他 iframe 的噪声 message 被当作指令。
 */

export type ParentToChildMessage =
  | { target: 'webling'; type: 'send'; text: string }
  | { target: 'webling'; type: 'interrupt' }
  | { target: 'webling'; type: 'close' };

export type ChildToParentMessage =
  | { source: 'webling'; type: 'webling:ready' }
  | { source: 'webling'; type: 'webling:session'; character_id: string }
  | { source: 'webling'; type: 'webling:state'; value: 'idle' | 'processing' | 'speaking' | 'listening' }
  | { source: 'webling'; type: 'webling:message'; role: 'user' | 'assistant' | 'system'; text: string; id: string }
  | { source: 'webling'; type: 'webling:error'; code: string; message: string }
  | { source: 'webling'; type: 'webling:closed' }
  | { source: 'webling'; type: 'webling:request_close' };

export const BUTTON_Z = 2147483647;
export const PANEL_Z = 2147483646;

export type Position = 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';

export function cornerStyle(pos: Position, offset = 20): string {
  const [v, h] = pos.split('-') as ['top' | 'bottom', 'left' | 'right'];
  return `${v}: ${offset}px; ${h}: ${offset}px;`;
}

/**
 * 构造 iframe src —— apiKey 进 URL query。
 *
 * 安全注意：embed 场景下 apiKey 本就是半公开的（任何第三方接入页都在 HTML 里
 * 明文放 data-api-key），真正的访问控制在后端的 Origin 白名单 + daily_quota。
 * 所以 apiKey 进 URL referer 不比进 HTML 源码更糟。
 *
 * 短期 JWT 永远不进 URL —— 它在 iframe 内部通过 auth.fetchEmbedToken 拿，
 * 放 sessionStorage，过期自动续签。
 */
export function buildEmbedUrl(opts: {
  baseUrl: string;
  apiKey: string;
  characterId: string;
  apiBase?: string;
}): string {
  const url = new URL('/embed/embed.html', opts.baseUrl);
  url.searchParams.set('api_key', opts.apiKey);
  url.searchParams.set('character_id', opts.characterId);
  if (opts.apiBase) url.searchParams.set('api_base', opts.apiBase);
  return url.toString();
}
