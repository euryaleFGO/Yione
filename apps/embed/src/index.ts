/**
 * webLing Embed Script — 第三方可通过 <script> 标签接入聊天功能。
 *
 * 用法：
 *   <script src="https://your-domain.com/embed.js"
 *     data-api-key="your-api-key"
 *     data-character-id="ling"
 *     data-position="bottom-right"
 *     data-base-url="https://api.your-domain.com">
 *   </script>
 */

interface EmbedConfig {
  apiKey: string;
  characterId: string;
  position: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
  baseUrl: string;
}

function readConfig(): EmbedConfig {
  const script = document.currentScript as HTMLScriptElement | null;
  const ds = script?.dataset ?? {};
  return {
    apiKey: ds.apiKey ?? '',
    characterId: ds.characterId ?? 'ling',
    position: (ds.position as EmbedConfig['position']) ?? 'bottom-right',
    baseUrl: ds.baseUrl ?? window.location.origin,
  };
}

function getPositionStyle(pos: EmbedConfig['position']): string {
  const [v, h] = pos.split('-');
  return `${v}: 20px; ${h}: 20px;`;
}

function createButton(config: EmbedConfig): HTMLButtonElement {
  const btn = document.createElement('button');
  btn.textContent = '\uD83D\uDCAC';
  btn.setAttribute('aria-label', '打开聊天');
  btn.style.cssText = `
    position: fixed; width: 56px; height: 56px; border-radius: 50%;
    background: #6366f1; color: white; border: none; cursor: pointer;
    font-size: 24px; line-height: 56px; text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 2147483647; transition: transform 0.2s;
    ${getPositionStyle(config.position)}
  `;
  btn.onmouseenter = () => {
    btn.style.transform = 'scale(1.1)';
  };
  btn.onmouseleave = () => {
    btn.style.transform = 'scale(1)';
  };
  return btn;
}

function createPanel(config: EmbedConfig): HTMLIFrameElement {
  const iframe = document.createElement('iframe');
  const url = new URL('/embed/embed.html', config.baseUrl);
  url.searchParams.set('apiKey', config.apiKey);
  url.searchParams.set('characterId', config.characterId);
  iframe.src = url.toString();
  iframe.allow = 'microphone';
  iframe.style.cssText = `
    position: fixed; width: 380px; height: 600px; border: none;
    border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.15);
    z-index: 2147483646; display: none; transition: opacity 0.3s;
    ${getPositionStyle(config.position)}
  `;
  return iframe;
}

function init(): void {
  const config = readConfig();
  if (!config.apiKey) {
    console.warn('[webling] data-api-key is required');
    return;
  }

  const btn = createButton(config);
  const panel = createPanel(config);
  let isOpen = false;

  btn.onclick = () => {
    isOpen = !isOpen;
    panel.style.display = isOpen ? 'block' : 'none';
    btn.textContent = isOpen ? '\u2715' : '\uD83D\uDCAC';
    btn.setAttribute('aria-label', isOpen ? '关闭聊天' : '打开聊天');
  };

  document.body.appendChild(btn);
  document.body.appendChild(panel);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
