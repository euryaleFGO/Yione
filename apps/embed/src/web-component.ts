/**
 * webLing Web Component — `<web-ling>` 自定义标签。
 *
 * 用法：
 *   <script src="https://your-domain.com/embed/web-component.js"></script>
 *   <web-ling api-key="your-key" character-id="ling"></web-ling>
 *
 * 属性：
 *   api-key      (必填) API Key
 *   character-id  角色 ID，默认 "ling"
 *   position     悬浮位置：bottom-right | bottom-left | top-right | top-left
 *   base-url     后端地址，默认当前域名
 */

const TEMPLATE = document.createElement('template');
TEMPLATE.innerHTML = `
<style>
  :host {
    position: fixed; z-index: 2147483647;
    width: 380px; height: 600px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  :host([position="bottom-right"]) { bottom: 20px; right: 20px; }
  :host([position="bottom-left"])  { bottom: 20px; left: 20px; }
  :host([position="top-right"])    { top: 20px; right: 20px; }
  :host([position="top-left"])     { top: 20px; left: 20px; }

  .panel {
    width: 100%; height: 100%; display: flex; flex-direction: column;
    border-radius: 16px; overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.15); background: #f8fafc;
  }
  .header {
    padding: 12px 16px; background: #6366f1; color: white;
    font-size: 14px; font-weight: 600;
    display: flex; align-items: center; gap: 8px;
  }
  .header .status { font-weight: 400; opacity: 0.8; font-size: 12px; }
  .messages {
    flex: 1; overflow-y: auto; padding: 16px;
    display: flex; flex-direction: column; gap: 8px;
  }
  .msg {
    max-width: 80%; padding: 10px 14px; border-radius: 12px;
    font-size: 14px; line-height: 1.5; word-break: break-word;
  }
  .msg.user {
    align-self: flex-end; background: #6366f1; color: white;
    border-bottom-right-radius: 4px;
  }
  .msg.assistant {
    align-self: flex-start; background: white; color: #1e293b;
    border: 1px solid #e2e8f0; border-bottom-left-radius: 4px;
  }
  .msg.system {
    align-self: center; background: #fef3c7; color: #92400e;
    font-size: 12px; border-radius: 8px;
  }
  .input-bar {
    padding: 12px 16px; border-top: 1px solid #e2e8f0; background: white;
    display: flex; gap: 8px;
  }
  .input-bar input {
    flex: 1; padding: 10px 14px; border: 1px solid #e2e8f0;
    border-radius: 8px; font-size: 14px; outline: none;
  }
  .input-bar input:focus { border-color: #6366f1; }
  .input-bar button {
    padding: 10px 16px; background: #6366f1; color: white;
    border: none; border-radius: 8px; cursor: pointer; font-size: 14px;
  }
  .input-bar button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
<div class="panel">
  <div class="header">
    <span>webLing</span>
    <span class="status">连接中...</span>
  </div>
  <div class="messages"></div>
  <div class="input-bar">
    <input type="text" placeholder="输入消息..." disabled>
    <button disabled>发送</button>
  </div>
</div>
`;

class WeblingElement extends HTMLElement {
  static get observedAttributes() {
    return ['api-key', 'character-id', 'position', 'base-url'];
  }

  private shadow: ShadowRoot;
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private token: string | null = null;

  constructor() {
    super();
    this.shadow = this.attachShadow({ mode: 'open' });
    this.shadow.appendChild(TEMPLATE.content.cloneNode(true));
  }

  connectedCallback() {
    this.init();
  }

  disconnectedCallback() {
    this.ws?.close();
  }

  attributeChangedCallback(name: string, oldVal: string, newVal: string) {
    if (oldVal !== newVal && this.isConnected) {
      this.init();
    }
  }

  private get apiKey(): string { return this.getAttribute('api-key') ?? ''; }
  private get characterId(): string { return this.getAttribute('character-id') ?? 'ling'; }
  private get baseUrl(): string { return this.getAttribute('base-url') ?? location.origin; }

  private get statusEl() { return this.shadow.querySelector('.status') as HTMLElement; }
  private get messagesEl() { return this.shadow.querySelector('.messages') as HTMLElement; }
  private get inputEl() { return this.shadow.querySelector('input') as HTMLInputElement; }
  private get sendEl() { return this.shadow.querySelector('button') as HTMLButtonElement; }

  private addMessage(text: string, role: string) {
    const div = document.createElement('div');
    div.className = 'msg ' + role;
    div.textContent = text;
    this.messagesEl.appendChild(div);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  private setStatus(text: string) {
    this.statusEl.textContent = text;
  }

  private async init() {
    if (!this.apiKey) {
      this.setStatus('缺少 api-key');
      return;
    }

    this.messagesEl.innerHTML = '';
    this.setStatus('初始化中...');

    try {
      // 获取 token
      const tokenRes = await fetch(`${this.baseUrl}/api/embed/token`, {
        method: 'POST',
        headers: { 'X-API-Key': this.apiKey },
      });
      if (!tokenRes.ok) throw new Error(`token: ${tokenRes.status}`);
      const tokenData = await tokenRes.json();
      this.token = tokenData.token;

      // 创建会话
      const sessRes = await fetch(`${this.baseUrl}/api/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ character_id: this.characterId }),
      });
      if (!sessRes.ok) throw new Error(`session: ${sessRes.status}`);
      const sessData = await sessRes.json();
      this.sessionId = sessData.session_id;

      if (sessData.greeting) this.addMessage(sessData.greeting, 'assistant');

      this.connectWs();
    } catch (err) {
      this.setStatus('错误');
      this.addMessage('初始化失败: ' + (err as Error).message, 'system');
    }
  }

  private connectWs() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${location.host}/ws/chat?session_id=${this.sessionId}&token=${this.token}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.setStatus('已连接');
      this.inputEl.disabled = false;
      this.sendEl.disabled = false;
      this.inputEl.focus();
    };

    this.ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      switch (data.type) {
        case 'state':
          if (data.value === 'idle') this.setStatus('已连接');
          else if (data.value === 'processing') this.setStatus('思考中...');
          else if (data.value === 'speaking') this.setStatus('说话中...');
          break;
        case 'subtitle':
          if (data.is_final) this.addMessage(data.text, 'assistant');
          break;
        case 'error':
          this.addMessage('错误: ' + data.message, 'system');
          break;
      }
    };

    this.ws.onclose = () => {
      this.setStatus('已断开');
      this.inputEl.disabled = true;
      this.sendEl.disabled = true;
    };

    // 绑定发送
    this.sendEl.onclick = () => this.send();
    this.inputEl.onkeydown = (e) => { if (e.key === 'Enter') this.send(); };
  }

  private send() {
    const text = this.inputEl.value.trim();
    if (!text || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.addMessage(text, 'user');
    this.ws.send(JSON.stringify({ type: 'user_message', text }));
    this.inputEl.value = '';
  }
}

customElements.define('web-ling', WeblingElement);
