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
  // M35：最近一次声纹识别命中的说话人，提交下条 user_message 时贴到消息上
  const lastSpeaker = shallowRef<{ id: string; name: string | null } | null>(null);

  let socket: ReturnType<typeof createChatSocket> | null = null;
  let streamingMessageId: string | null = null;

  // M36 嘴型时间轴配对：backend 对同一段 TTS 先发 AudioEvent 再发 VisemeTimelineEvent；
  // 两个事件都按 segment_idx 索引。先到的那个先塞进 map，第二个到了就配对 enqueue。
  // 50ms 没等到 timeline 就降级，光凭 url enqueue（viseme ticker 没数据时等价纯音量）。
  const pendingAudio = new Map<number, { url: string; sampleRate: number }>();
  const pendingTimelines = new Map<
    number,
    { char: string; t_start: number; t_end: number; viseme: string }[]
  >();
  const audioFlushTimers = new Map<number, ReturnType<typeof setTimeout>>();

  function enqueueSegment(
    segmentIdx: number,
    url: string,
    sampleRate: number,
    timeline?: { char: string; t_start: number; t_end: number; viseme: string }[],
  ): void {
    const t = audioFlushTimers.get(segmentIdx);
    if (t) {
      clearTimeout(t);
      audioFlushTimers.delete(segmentIdx);
    }
    pendingAudio.delete(segmentIdx);
    pendingTimelines.delete(segmentIdx);
    audioQueue.enqueue({ url, segmentIdx, sampleRate, timeline });
  }

  // 一组由 AvatarStage 在模型 ready 时注入的控制器。若头像没挂出来（比如缺 Cubism
  // Core），所有调用都静默降级，聊天 UI 仍可用。
  const noop: AvatarControls = {
    speak: () => Promise.resolve(),
    stopSpeaking: () => {},
    playMotion: () => Promise.resolve(),
    setExpression: () => Promise.resolve(),
    startPlaceholderMouth: () => {},
    stopPlaceholderMouth: () => {},
  };
  let avatar: AvatarControls = noop;

  const audioQueue = new AudioQueue({
    speak: async (url, opts) => {
      await avatar.speak(url, { timeline: opts?.timeline });
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
        case 'audio': {
          avatar.stopPlaceholderMouth();
          const existing = pendingTimelines.get(ev.segment_idx);
          if (existing) {
            enqueueSegment(ev.segment_idx, ev.url, ev.sample_rate, existing);
          } else {
            pendingAudio.set(ev.segment_idx, {
              url: ev.url,
              sampleRate: ev.sample_rate,
            });
            // 50ms 没等到 timeline 就降级 enqueue，不阻塞播放
            const flushTimer = setTimeout(() => {
              const buffered = pendingAudio.get(ev.segment_idx);
              if (buffered) {
                enqueueSegment(ev.segment_idx, buffered.url, buffered.sampleRate);
              }
            }, 50);
            audioFlushTimers.set(ev.segment_idx, flushTimer);
          }
          break;
        }
        case 'viseme_timeline': {
          const audio = pendingAudio.get(ev.segment_idx);
          if (audio) {
            enqueueSegment(ev.segment_idx, audio.url, audio.sampleRate, ev.timeline);
          } else {
            pendingTimelines.set(ev.segment_idx, ev.timeline);
          }
          break;
        }
        case 'motion':
          // 后端推 motion group 名（Hiyori: Tap@Body / Flick / ...），
          // 交给 Live2D 播一次动作；playMotion 内部已经吞错
          void avatar.playMotion(ev.name);
          break;
        case 'expression':
          // 情绪边沿触发的面部表情（joy/anger/crying/...）；setExpression 内部吞错
          void avatar.setExpression(ev.name);
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
        case 'speaker_detected': {
          // 后端声纹命中 → 记下当前说话人，同时把最近一条 user 消息贴上
          const spk = { id: ev.speaker_id, name: ev.name };
          lastSpeaker.value = spk;
          for (let i = messages.value.length - 1; i >= 0; i--) {
            const m = messages.value[i];
            if (m && m.role === 'user' && !m.speaker) {
              m.speaker = spk;
              break;
            }
          }
          break;
        }
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

  /**
   * M35：把一段 wav 音频喂给声纹 identify；命中时服务端会通过 WS 推回
   * speaker_detected 事件，上面的 onMessage case 'speaker_detected' 会处理。
   * 这里只管 fire-and-forget POST，不阻塞对话主流程。
   */
  async function identifySpeakerFromWav(wav: Blob): Promise<void> {
    if (!session.value) return;
    try {
      const form = new FormData();
      form.append('audio', wav, 'utterance.wav');
      form.append('session_id', session.value.id);
      await fetch('/api/speakers/identify', { method: 'POST', body: form });
    } catch {
      /* 声纹失败不影响对话；后端 fail-close 会返 503，静默吞掉 */
    }
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
    identifySpeakerFromWav,
    lastSpeaker,
    disconnect,
    setAvatarControls,
    fetchCharacters,
    changeCharacter,
  };
});
