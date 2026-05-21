export type Level = 'A2' | 'B1' | 'B2' | 'C1';

export interface Session {
  id: string;
  characterName: string;
  level: Level;
  createdAt: string; // ISO 8601
  endedAt?: string;  // ISO 8601
}
