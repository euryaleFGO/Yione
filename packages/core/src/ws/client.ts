import { isServerEvent, type ClientEvent, type ServerEvent } from '../types/ws.js';

export interface ChatSocketOptions {
  /** Base WebSocket URL, e.g. `ws://localhost:8000`. No trailing slash. */
  baseUrl: string;
  sessionId: string;
  /** Called for every decoded server event. */
  onEvent: (event: ServerEvent) => void;
  /** Called when the underlying socket opens/closes (useful for UI state). */
  onOpen?: () => void;
  onClose?: (code: number, reason: string) => void;
  /** Called on fatal transport error (malformed JSON, etc). */
  onError?: (err: Error) => void;
  /** Minimum backoff (ms). Default 500. */
  minReconnectDelay?: number;
  /** Maximum backoff (ms). Default 8000. */
  maxReconnectDelay?: number;
  /** Optional bearer token accessor (M6 will use it). */
  getToken?: () => string | null | Promise<string | null>;
  /** Override WebSocket constructor (tests). */
  WebSocketImpl?: typeof WebSocket;
}

export class ChatSocket {
  private ws: WebSocket | null = null;
  private readonly WS: typeof WebSocket;
  private reconnectDelay: number;
  private stopped = false;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(private readonly opts: ChatSocketOptions) {
    this.WS = opts.WebSocketImpl ?? WebSocket;
    this.reconnectDelay = opts.minReconnectDelay ?? 500;
  }

  async connect(): Promise<void> {
    if (this.stopped) return;
    const base = this.opts.baseUrl.replace(/\/$/, '');
    const token = await this.opts.getToken?.();
    const params = new URLSearchParams({ session_id: this.opts.sessionId });
    if (token) params.set('token', token);
    const url = `${base}/ws/chat?${params.toString()}`;

    const ws = new this.WS(url);
    this.ws = ws;

    // The caller expects `await connect()` to mean the socket is OPEN and
    // ready to send. Resolve on the first of open/error/close so a pending
    // `sendUserMessage` never races a CONNECTING socket.
    return new Promise<void>((resolve, reject) => {
      let settled = false;
      const settle = (fn: () => void) => {
        if (settled) return;
        settled = true;
        fn();
      };

      ws.onopen = () => {
        this.reconnectDelay = this.opts.minReconnectDelay ?? 500;
        this.opts.onOpen?.();
        settle(resolve);
      };
      ws.onmessage = (ev) => this.handleMessage(ev.data);
      ws.onerror = () => {
        this.opts.onError?.(new Error('websocket error'));
        settle(() => reject(new Error('websocket error')));
      };
      ws.onclose = (ev) => {
        this.opts.onClose?.(ev.code, ev.reason);
        this.ws = null;
        if (!this.stopped) this.scheduleReconnect();
        settle(() => reject(new Error(`websocket closed before open (code=${ev.code})`)));
      };
    });
  }

  /** True iff the socket is OPEN (not CONNECTING / CLOSING / CLOSED). */
  get isOpen(): boolean {
    return this.ws?.readyState === this.WS.OPEN;
  }

  send(event: ClientEvent): void {
    if (!this.isOpen) {
      throw new Error('WebSocket is not open');
    }
    this.ws!.send(JSON.stringify(event));
  }

  sendUserMessage(text: string): void {
    this.send({ type: 'user_message', text });
  }

  ping(): void {
    if (this.ws?.readyState === this.WS.OPEN) {
      this.send({ type: 'ping' });
    }
  }

  close(): void {
    this.stopped = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
  }

  private handleMessage(data: unknown): void {
    let parsed: unknown;
    try {
      parsed = typeof data === 'string' ? JSON.parse(data) : data;
    } catch (err) {
      this.opts.onError?.(err instanceof Error ? err : new Error(String(err)));
      return;
    }
    if (!isServerEvent(parsed)) {
      this.opts.onError?.(new Error(`unrecognized server event: ${JSON.stringify(parsed)}`));
      return;
    }
    this.opts.onEvent(parsed);
  }

  private scheduleReconnect(): void {
    const max = this.opts.maxReconnectDelay ?? 8000;
    const delay = Math.min(this.reconnectDelay, max);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, max);
      void this.connect();
    }, delay);
  }
}
