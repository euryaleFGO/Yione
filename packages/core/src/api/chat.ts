import type { HttpClient } from './http.js';

export interface SessionInfo {
  session_id: string;
  character_id: string;
  user_ref?: string | null;
  greeting: string;
  created_at: string;
}

export interface ChatReply {
  reply: string;
  emotion: string;
  motion?: string | null;
}

export class ChatApi {
  constructor(private readonly http: HttpClient) {}

  createSession(input: { characterId?: string; userRef?: string } = {}): Promise<SessionInfo> {
    return this.http.post<SessionInfo>('/api/sessions', {
      character_id: input.characterId ?? 'ling',
      user_ref: input.userRef,
    });
  }

  getSession(sessionId: string): Promise<SessionInfo> {
    return this.http.get<SessionInfo>(`/api/sessions/${sessionId}`);
  }

  send(sessionId: string, text: string): Promise<ChatReply> {
    return this.http.post<ChatReply>('/api/chat', { session_id: sessionId, text });
  }
}
