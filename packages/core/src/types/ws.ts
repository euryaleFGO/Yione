/**
 * WebSocket 协议：前后端共享的 **唯一事实来源**。
 * 后端 `backend/app/schemas/ws.py` 必须保持同构。
 * 任何改动都应伴随对应后端 schema 更新（M4 会加 CI 一致性检查）。
 */

export type Emotion =
  | 'neutral'
  | 'joy'
  | 'sadness'
  | 'anger'
  | 'fear'
  | 'surprise'
  | 'disgust'
  | 'affection';

// -------- Client → Server --------

export type ClientEvent =
  | { type: 'user_message'; text: string }
  | { type: 'cancel' }
  | { type: 'ping' }
  | { type: 'change_character'; character_id: string };

// -------- Server → Client --------

export type AgentState = 'listening' | 'processing' | 'speaking' | 'idle';

export type ServerEvent =
  | { type: 'state'; value: AgentState }
  | { type: 'subtitle'; text: string; is_final: boolean; emotion: Emotion }
  | { type: 'motion'; name: string }
  | { type: 'audio'; url: string; segment_idx: number; sample_rate: number }
  | { type: 'audio_rms'; rms: number; t: number }
  | { type: 'viseme'; open_y: number; form: number }
  | { type: 'error'; code: string; message: string }
  | { type: 'pong' };

export function isServerEvent(value: unknown): value is ServerEvent {
  return (
    typeof value === 'object' &&
    value !== null &&
    'type' in value &&
    typeof (value as { type: unknown }).type === 'string'
  );
}
