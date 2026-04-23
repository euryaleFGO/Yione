export type Role = 'user' | 'assistant' | 'system';

export interface Message {
  id: string;
  role: Role;
  text: string;
  createdAt: string; // ISO8601
  emotion?: string;
  /** M16/M35：声纹识别命中的说话人；仅 user 消息有意义 */
  speaker?: { id: string; name: string | null };
}

export interface SessionSummary {
  id: string;
  characterId: string;
  userRef?: string;
  greeting?: string;
  createdAt: string;
}
