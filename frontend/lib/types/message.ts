import type { FeedbackItem } from '@/lib/api/contracts';

export type MessageRole = 'user' | 'pally';

export interface Message {
  id: string;
  sessionId: string;
  role: MessageRole;
  transcript: string;
  createdAt: string; // ISO 8601
  feedback?: {
    items: FeedbackItem[];
    pending: boolean;
  };
}
