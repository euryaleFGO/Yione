import { AudioQueue, type Message, type SessionSummary } from '@webling/core';
import { defineStore } from 'pinia';
import { ref, shallowRef } from 'vue';

import { chatApi, createChatSocket } from '@/lib/webling-clients';

type ConnectionState = 'idle' | 'connecting' | 'open' | 'closed' | 'error';
type AgentState = 'idle' | 'processing' | 'speaking' | 'listening';

function uid(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

export const useChatStore = defineStore('chat', () => {
  const session = shallowRef<SessionSummary | null>(null);
  const messages = ref<Message[]>([]);
  const draft = ref('');
  const connection = ref<ConnectionState>('idle');
  const agentState = ref<AgentState>('idle');
  const lastError = ref<string | null>(null);
  /** Per-frame RMS sample from the current TTS playback; 0 when silent. */
  const rms = ref(0);

  let socket: ReturnType<typeof createChatSocket> | null = null;
  let streamingMessageId: string | null = null;

  const audioQueue = new AudioQueue({
    onRms: (v) => {
      rms.value = v;
    },
    onActivityChange: (active) => {
      if (!active) rms.value = 0;
    },
    onError: (err) => {
      lastError.value = `audio: ${err.message}`;
    },
  });

  async function ensureSession(characterId = 'ling'): Promise<SessionSummary> {
    if (session.value) return session.value;
    const info = await chatApi.createSession({ characterId });
    const summary: SessionSummary = {
      id: info.session_id,
      characterId: info.character_id,
      userRef: info.user_ref ?? undefined,
      greeting: info.greeting,
      createdAt: info.created_at,
    };
    session.value = summary;
    if (summary.greeting) {
      messages.value.push({
        id: uid('m'),
        role: 'assistant',
        text: summary.greeting,
        createdAt: new Date().toISOString(),
      });
    }
    return summary;
  }

  async function connectSocket(): Promise<void> {
    if (socket) return;
    const info = await ensureSession();
    connection.value = 'connecting';
    socket = createChatSocket(info.id, (ev) => {
      switch (ev.type) {
        case 'state':
          agentState.value = ev.value;
          break;
        case 'subtitle':
          upsertStreamingAssistantMessage(ev.text, ev.is_final, ev.emotion);
          break;
        case 'audio':
          audioQueue.enqueue({
            url: ev.url,
            segmentIdx: ev.segment_idx,
            sampleRate: ev.sample_rate,
          });
          break;
        case 'error':
          lastError.value = `${ev.code}: ${ev.message}`;
          break;
        default:
          break;
      }
    });
    try {
      await socket.connect();
      connection.value = 'open';
    } catch (err) {
      connection.value = 'error';
      lastError.value = err instanceof Error ? err.message : String(err);
    }
  }

  function upsertStreamingAssistantMessage(
    text: string,
    isFinal: boolean,
    emotion: string,
  ): void {
    if (!streamingMessageId) {
      streamingMessageId = uid('m');
      messages.value.push({
        id: streamingMessageId,
        role: 'assistant',
        text,
        emotion,
        createdAt: new Date().toISOString(),
      });
    } else {
      const msg = messages.value.find((m) => m.id === streamingMessageId);
      if (msg) {
        msg.text = text;
        msg.emotion = emotion;
      }
    }
    if (isFinal) streamingMessageId = null;
  }

  async function sendViaWs(text: string): Promise<void> {
    await connectSocket();
    if (!socket) return;
    // Kick the AudioContext alive from this user-gesture turn so the first
    // `audio` event can start playing without the autoplay block.
    void audioQueue.ensureContext();
    messages.value.push({
      id: uid('m'),
      role: 'user',
      text,
      createdAt: new Date().toISOString(),
    });
    socket.sendUserMessage(text);
  }

  async function sendViaRest(text: string): Promise<void> {
    const info = await ensureSession();
    messages.value.push({
      id: uid('m'),
      role: 'user',
      text,
      createdAt: new Date().toISOString(),
    });
    agentState.value = 'processing';
    try {
      const reply = await chatApi.send(info.id, text);
      messages.value.push({
        id: uid('m'),
        role: 'assistant',
        text: reply.reply,
        emotion: reply.emotion,
        createdAt: new Date().toISOString(),
      });
    } finally {
      agentState.value = 'idle';
    }
  }

  async function submit(text: string, transport: 'ws' | 'rest' = 'ws'): Promise<void> {
    const trimmed = text.trim();
    if (!trimmed) return;
    lastError.value = null;
    if (transport === 'rest') {
      await sendViaRest(trimmed);
    } else {
      await sendViaWs(trimmed);
    }
  }

  async function disconnect(): Promise<void> {
    socket?.close();
    socket = null;
    connection.value = 'closed';
    await audioQueue.destroy();
  }

  return {
    session,
    messages,
    draft,
    connection,
    agentState,
    lastError,
    rms,
    ensureSession,
    connectSocket,
    submit,
    disconnect,
  };
});
