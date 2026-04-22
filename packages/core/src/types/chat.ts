export type Role = 'user' | 'assistant' | 'system';

export interface Message {
  id: string;
  role: Role;
  text: string;
  createdAt: string; // ISO8601
  emotion?: string;
}

export interface SessionSummary {
  id: string;
  characterId: string;
  userRef?: string;
  greeting?: string;
  createdAt: string;
}
