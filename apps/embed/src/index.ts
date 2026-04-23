/**
 * Script tag 接入入口（IIFE 产物：embed.js）。
 *
 * 第三方网站只需：
 *   <script
 *     src="https://<webling-host>/embed/embed.js"
 *     data-api-key="pk_xxx"
 *     data-character-id="ling"
 *     data-position="bottom-right"
 *     data-base-url="https://<webling-host>"
 *     async defer
 *   ></script>
 *
 * 会在页面右下角挂一个圆形按钮，点击切换 iframe 显隐。iframe 指向
 * {base-url}/embed/embed.html（完整 Vue 应用 + Live2D + TTS + 嘴型）。
 *
 * 也支持手动 API：`window.WeblingEmbed.mount({...})` / `.unmount()`。
 */
import {
  BUTTON_Z,
  PANEL_Z,
  buildEmbedUrl,
  cornerStyle,
  type Position,
} from './postmessage';

export interface EmbedOptions {
  apiKey: string;
  characterId?: string;
  /** 浮动按钮位置，默认 bottom-right */
  position?: Position;
  /** iframe 宿主所在域（要托管 /embed/embed.html）。默认读 data-base-url 或 script 所在域 */
  baseUrl?: string;
  /** backend API 所在域，默认等于 baseUrl */
  apiBase?: string;
  /** 默认展开，不显示浮动按钮 */
  openByDefault?: boolean;
  /** iframe 尺寸，默认 380×620 / 移动端全屏 */
  width?: number;
  height?: number;
}

export interface EmbedHandle {
  open(): void;
  close(): void;
  toggle(): void;
  send(text: string): void;
  interrupt(): void;
  unmount(): void;
  /** 已挂载的 iframe 元素，方便宿主自定义样式 */
  readonly iframe: HTMLIFrameElement;
}

function isMobile(): boolean {
  return window.matchMedia('(max-width: 640px)').matches;
}

function sendToIframe(iframe: HTMLIFrameElement, msg: Record<string, unknown>): void {
  try {
    iframe.contentWindow?.postMessage({ target: 'webling', ...msg }, '*');
  } catch {
    // iframe 未 ready 时会拒，忽略
  }
}

function createButton(position: Position, onClick: () => void): HTMLButtonElement {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.textContent = '\u{1F4AC}';
  btn.setAttribute('aria-label', '打开 webLing 聊天');
  btn.style.cssText = `
    position: fixed; ${cornerStyle(position)}
    width: 56px; height: 56px; border-radius: 50%;
    background: #6366f1; color: white; border: none; cursor: pointer;
    font-size: 24px; line-height: 56px; text-align: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    z-index: ${BUTTON_Z}; transition: transform 0.2s;
  `;
  btn.addEventListener('mouseenter', () => (btn.style.transform = 'scale(1.08)'));
  btn.addEventListener('mouseleave', () => (btn.style.transform = 'scale(1)'));
  btn.addEventListener('click', onClick);
  return btn;
}

function createIframe(src: string, position: Position, width: number, height: number): HTMLIFrameElement {
  const iframe = document.createElement('iframe');
  iframe.src = src;
  // 麦克风（M18 语音输入必需）+ 自动播放（TTS 必需）
  iframe.allow = 'microphone; autoplay; clipboard-write';
  iframe.setAttribute('title', 'webLing 聊天');
  const mobile = isMobile();
  const w = mobile ? window.innerWidth : width;
  const h = mobile ? window.innerHeight : height;
  iframe.style.cssText = `
    position: fixed; ${mobile ? 'top: 0; left: 0;' : cornerStyle(position)}
    width: ${w}px; height: ${h}px; border: none;
    border-radius: ${mobile ? '0' : '16px'}; overflow: hidden;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
    z-index: ${PANEL_Z}; display: none; background: white;
  `;
  return iframe;
}

export function mount(opts: EmbedOptions): EmbedHandle {
  if (!opts.apiKey) throw new Error('[webLing] apiKey is required');

  const position: Position = opts.position ?? 'bottom-right';
  const baseUrl = (opts.baseUrl ?? location.origin).replace(/\/$/, '');
  const width = opts.width ?? 380;
  const height = opts.height ?? 620;
  const src = buildEmbedUrl({
    baseUrl,
    apiKey: opts.apiKey,
    characterId: opts.characterId ?? 'ling',
    apiBase: opts.apiBase,
  });

  const iframe = createIframe(src, position, width, height);
  const button = opts.openByDefault ? null : createButton(position, () => handle.toggle());

  function open(): void {
    iframe.style.display = 'block';
    if (button) {
      button.textContent = '×';
      button.setAttribute('aria-label', '关闭 webLing 聊天');
    }
  }
  function close(): void {
    iframe.style.display = 'none';
    if (button) {
      button.textContent = '\u{1F4AC}';
      button.setAttribute('aria-label', '打开 webLing 聊天');
    }
  }
  function toggle(): void {
    if (iframe.style.display === 'none') open();
    else close();
  }

  // iframe 内部的关闭按钮（EmbedApp.vue header ×）会发 webling:request_close
  function onChildMessage(ev: MessageEvent): void {
    const data = ev.data;
    if (!data || data.source !== 'webling') return;
    if (data.type === 'webling:request_close') close();
  }
  window.addEventListener('message', onChildMessage);

  document.body.appendChild(iframe);
  if (button) document.body.appendChild(button);
  if (opts.openByDefault) open();

  const handle: EmbedHandle = {
    open,
    close,
    toggle,
    iframe,
    send(text: string) {
      sendToIframe(iframe, { type: 'send', text });
    },
    interrupt() {
      sendToIframe(iframe, { type: 'interrupt' });
    },
    unmount() {
      window.removeEventListener('message', onChildMessage);
      iframe.remove();
      button?.remove();
    },
  };

  return handle;
}

// 自动启动：扫描加载本 script 的 <script data-api-key="...">
function autoInit(): EmbedHandle | null {
  const scripts = document.querySelectorAll<HTMLScriptElement>('script[data-api-key]');
  // 最后一个（通常是当前刚插入的）
  const script = scripts[scripts.length - 1];
  if (!script) return null;
  const ds = script.dataset;
  if (!ds.apiKey) return null;
  return mount({
    apiKey: ds.apiKey,
    characterId: ds.characterId ?? 'ling',
    position: (ds.position as Position | undefined) ?? 'bottom-right',
    baseUrl: ds.baseUrl ?? new URL(script.src, location.href).origin,
    apiBase: ds.apiBase,
    openByDefault: ds.openByDefault === 'true' || ds.openByDefault === '1',
  });
}

// 自动启动（DOMContentLoaded 后）
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    autoInit();
  });
} else {
  // 已经 DOMContentLoaded，直接跑
  autoInit();
}

// 同时暴露给手动调用（window.WeblingEmbed.mount({...})）。
// IIFE 产物的 name='WeblingEmbed' 会把命名导出整体挂到 window 上，
// 所以 `window.WeblingEmbed.mount(...)` 和 `import { mount } from '@webling/embed'` 都能用。
