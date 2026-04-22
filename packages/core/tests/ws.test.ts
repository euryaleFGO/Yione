import { describe, expect, it, vi } from 'vitest';

import { ChatSocket, type ClientEvent, type ServerEvent } from '../src/index.js';

type Listener = ((ev: MessageEvent) => void) | null;

class MockSocket {
  static OPEN = 1;
  static CLOSED = 3;
  readonly OPEN = 1;
  readonly CLOSED = 3;
  readyState = 1;
  onopen: (() => void) | null = null;
  onclose: ((ev: { code: number; reason: string }) => void) | null = null;
  onmessage: Listener = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];
  constructor(public readonly url: string) {
    queueMicrotask(() => this.onopen?.());
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.readyState = 3;
    this.onclose?.({ code: 1000, reason: 'test' });
  }
  dispatch(event: ServerEvent) {
    this.onmessage?.({ data: JSON.stringify(event) } as MessageEvent);
  }
}

describe('ChatSocket', () => {
  it('sends user_message and dispatches parsed server events', async () => {
    const instances: MockSocket[] = [];
    const onEvent = vi.fn<(e: ServerEvent) => void>();

    const socket = new ChatSocket({
      baseUrl: 'ws://test.local',
      sessionId: 'sess_1',
      onEvent,
      WebSocketImpl: class extends MockSocket {
        constructor(url: string) {
          super(url);
          instances.push(this);
        }
      } as unknown as typeof WebSocket,
    });

    await socket.connect();
    await Promise.resolve(); // flush microtasks for onopen

    expect(instances.length).toBe(1);
    expect(instances[0].url).toContain('/ws/chat?session_id=sess_1');

    socket.sendUserMessage('hi');
    expect(instances[0].sent).toEqual([
      JSON.stringify({ type: 'user_message', text: 'hi' } satisfies ClientEvent),
    ]);

    instances[0].dispatch({ type: 'state', value: 'processing' });
    expect(onEvent).toHaveBeenCalledWith({ type: 'state', value: 'processing' });

    socket.close();
  });

  it('reports parse errors via onError', async () => {
    const onError = vi.fn<(err: Error) => void>();
    const instances: MockSocket[] = [];
    const socket = new ChatSocket({
      baseUrl: 'ws://test.local',
      sessionId: 's',
      onEvent: () => {},
      onError,
      WebSocketImpl: class extends MockSocket {
        constructor(url: string) {
          super(url);
          instances.push(this);
        }
      } as unknown as typeof WebSocket,
    });
    await socket.connect();
    await Promise.resolve();

    instances[0].onmessage?.({ data: 'not-json' } as MessageEvent);
    expect(onError).toHaveBeenCalled();

    socket.close();
  });
});
