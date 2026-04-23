import { AudioQueue, type Message, type SessionSummary } from '@webling/core';
import type { AvatarControls } from '@webling/live2d-kit';
import type { AvatarConfig } from '@webling/live2d-kit';
import { defineStore } from 'pinia';
import { ref, shallowRef } from 'vue';

import { chatApi, createChatSocket } from '@/lib/webling-clients';

type ConnectionState = 'idle' | 'connecting' | 'open' | 'closed' | 'error';
type AgentState = 'idle' | 'processing' | 'speaking' | 'listening';

export interface CharacterInfo {
  id: string;
  name: string;
  avatar_config: AvatarConfig;
  greeting: string;
  system_prompt: string;
  voice_id: string | null;
  enabled: boolean;
}

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
  const characters = ref<CharacterInfo[]>([]);
  const currentCharacter = shallowRef<CharacterInfo | null>(null);

  let socket: ReturnType<typeof createChatSocket> | null = null;
  let streamingMessageId: string | null = null;

  // 一组由 AvatarStage 在模型 ready 时注入的控制器。若头像没挂出来（比如缺 Cubism
  // Core），所有调用都静默降级，聊天 UI 仍可用。
  const noop: AvatarControls = {
    speak: () => Promise.resolve(),
    stopSpeaking: () => {},
    playMotion: () => Promise.resolve(),
    startPlaceholderMouth: () => {},
    stopPlaceholderMouth: () => {},
  };
  let avatar: AvatarControls = noop;

  const audioQueue = new AudioQueue({
    speak: async (url) => {
      await avatar.speak(url);
    },
    onError: (err) => {
      lastError.value = `audio: ${err.message}`;
    },
  });

  function setAvatarControls(controls: AvatarControls): void {
    avatar = controls;
  }

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
          if (ev.value === 'idle') {
            avatar.stopPlaceholderMouth();
          }
          break;
        case 'subtitle':
          upsertStreamingAssistantMessage(ev.text, ev.is_final, ev.emotion);
          break;
        case 'audio':
          avatar.stopPlaceholderMouth();
          audioQueue.enqueue({
            url: ev.url,
            segmentIdx: ev.segment_idx,
            sampleRate: ev.sample_rate,
          });
          break;
        case 'motion':
          // 后端推 motion group 名（Hiyori: Tap@Body / Flick / ...），
          // 交给 Live2D 播一次动作；playMotion 内部已经吞错
          void avatar.playMotion(ev.name);
          break;
        case 'placeholder_mouth':
          if (ev.action === 'start') {
            avatar.startPlaceholderMouth();
          } else {
            avatar.stopPlaceholderMouth();
          }
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
    messages.value.push({
      id: uid('m'),
      role: 'user',
      text,
      createdAt: new Date().toISOString(),
    });
    // 新消息隐式打断当前 turn；前端这边把未播的段清掉，进行中的那段由 stage 停
    audioQueue.clear();
    avatar.stopSpeaking();
    streamingMessageId = null;
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

  /** M4：用户点停止/打断时调用。 */
  function interrupt(): void {
    socket?.cancel();
    audioQueue.clear();
    avatar.stopSpeaking();
    streamingMessageId = null;
  }

  /** M34：实时对话循环中检测到用户开口（ASR partial 到达），通知服务端 barge-in。 */
  function sendSpeechStart(): void {
    socket?.sendSpeechStart();
    audioQueue.clear();
    avatar.stopSpeaking();
    streamingMessageId = null;
  }

  async function disconnect(): Promise<void> {
    socket?.close();
    socket = null;
    connection.value = 'closed';
    await audioQueue.destroy();
  }

  async function fetchCharacters(): Promise<void> {
    try {
      const resp = await fetch('/api/characters');
      if (!resp.ok) return;
      const data = await resp.json();
      characters.value = data.characters ?? [];
      if (characters.value.length > 0 && !currentCharacter.value) {
        currentCharacter.value = characters.value[0];
      }
    } catch {
      // 静默失败，UI 显示空列表
    }
  }

  async function changeCharacter(characterId: string): Promise<void> {
    const char = characters.value.find((c) => c.id === characterId);
    if (!char) return;
    currentCharacter.value = char;
    // 如果已连接 WS，发送 change_character 事件
    if (socket && connection.value === 'open') {
      socket.send({ type: 'change_character', character_id: characterId });
    }
  }

  return {
    session,
    messages,
    draft,
    connection,
    agentState,
    lastError,
    characters,
    currentCharacter,
    ensureSession,
    connectSocket,
    submit,
    interrupt,
    sendSpeechStart,
    disconnect,
    setAvatarControls,
    fetchCharacters,
    changeCharacter,
  };
});
