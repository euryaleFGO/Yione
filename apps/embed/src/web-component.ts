/**
 * `<web-ling>` Custom Element —— 声明式嵌入。
 *
 *   <script src="https://<webling-host>/embed/web-component.js" defer></script>
 *   <web-ling api-key="pk_xxx" character-id="ling"
 *             base-url="https://<webling-host>" embedded></web-ling>
 *
 * 默认模式（不带 `embedded` 属性）与 Script tag 一致：在 body 上挂浮动按钮 + 切换 iframe。
 * 加 `embedded` 属性则直接把 iframe 渲染在自身位置（由宿主页决定尺寸和布局），
 * 适合已有聊天面板空间的站点。
 *
 * 实现策略：三形态共用 mount/EmbedHandle（从 ./index 里的 library export 过来），
 * 避免重复实现浮动按钮 / postMessage / resize 等逻辑。
 */
import { mount, type EmbedHandle, type EmbedOptions } from './index';
import { buildEmbedUrl, type Position } from './postmessage';

const OBSERVED = ['api-key', 'character-id', 'position', 'base-url', 'api-base', 'embedded'] as const;

function pickOpts(el: HTMLElement): EmbedOptions {
  return {
    apiKey: el.getAttribute('api-key') ?? '',
    characterId: el.getAttribute('character-id') ?? 'ling',
    position: (el.getAttribute('position') as Position | null) ?? 'bottom-right',
    baseUrl: el.getAttribute('base-url') ?? location.origin,
    apiBase: el.getAttribute('api-base') ?? undefined,
  };
}

class WeblingElement extends HTMLElement {
  static get observedAttributes(): readonly string[] {
    return OBSERVED;
  }

  private handle: EmbedHandle | null = null;
  /** inline / embedded 模式：不挂 body，而是把 iframe 渲染在自身里 */
  private inlineIframe: HTMLIFrameElement | null = null;

  connectedCallback(): void {
    this.render();
  }

  disconnectedCallback(): void {
    this.teardown();
  }

  attributeChangedCallback(_name: string, oldVal: string | null, newVal: string | null): void {
    if (oldVal === newVal) return;
    if (this.isConnected) this.render();
  }

  private teardown(): void {
    this.handle?.unmount();
    this.handle = null;
    if (this.inlineIframe) {
      this.inlineIframe.remove();
      this.inlineIframe = null;
    }
  }

  private render(): void {
    this.teardown();
    const opts = pickOpts(this);
    if (!opts.apiKey) {
      console.warn('[webLing] <web-ling> 需要 api-key 属性');
      return;
    }

    if (this.hasAttribute('embedded')) {
      // 内联模式：iframe 直接进到 <web-ling> 自己里，不挂 body
      const iframe = document.createElement('iframe');
      iframe.src = buildEmbedUrl({
        baseUrl: (opts.baseUrl ?? location.origin).replace(/\/$/, ''),
        apiKey: opts.apiKey,
        characterId: opts.characterId ?? 'ling',
        apiBase: opts.apiBase,
      });
      iframe.allow = 'microphone; autoplay; clipboard-write';
      iframe.setAttribute('title', 'webLing 聊天');
      iframe.style.cssText = 'width: 100%; height: 100%; border: none; display: block;';
      this.style.display = this.style.display || 'block';
      this.appendChild(iframe);
      this.inlineIframe = iframe;
      return;
    }

    // 默认浮动模式：复用 Script tag 的 mount
    this.handle = mount(opts);
  }
}

if (!customElements.get('web-ling')) {
  customElements.define('web-ling', WeblingElement);
}
