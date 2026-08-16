import type { Axes } from "@/lib/types/character";
import type { Level } from "@/lib/types/session";

export type ConversationStatus = "active" | "completed";
export type TurnStatus = "processing" | "completed" | "partial" | "failed";

export interface CharacterParams {
  tone_casual: number;
  energy_level: number;
  humor_level: number;
}

export interface UserProfile {
  id: string;
  display_name: string;
  english_level: Level;
  onboarding_completed: boolean;
  traits: string[];
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  status: ConversationStatus;
  title: string | null;
  started_at: string;
  last_turn_at: string | null;
  completed_at: string | null;
  turn_count: number;
  current_axes: Axes;
}

export interface ConversationListItem extends Conversation {
  feedback_count: number;
  preview: string | null;
}

export interface FeedbackItem {
  original: string;
  corrected: string;
  explanation_ko: string;
}

export type ApiWarningCode = "tts_failed" | "feedback_failed";

export interface ApiWarning {
  code: ApiWarningCode;
  message: string;
}

export interface ConversationTurn {
  id: string;
  conversation_id: string;
  sequence: number;
  status: TurnStatus;
  user_transcript: string | null;
  pally_text: string | null;
  pally_audio_url: string | null;
  axes: Axes | null;
  character: CharacterParams | null;
  feedback: FeedbackItem[];
  warnings: ApiWarning[];
  created_at: string;
}

export interface UsageQuota {
  remaining_turns: number;
  daily_limit: number;
  exhausted: boolean;
  resets_at: string;
}

export interface ProfileResponse {
  profile: UserProfile;
}

export interface ConversationResponse {
  conversation: Conversation;
}

export interface ConversationListResponse {
  items: ConversationListItem[];
  next_cursor: string | null;
}

export interface ConversationDetailResponse {
  conversation: Conversation;
  turns: ConversationTurn[];
  next_cursor: string | null;
}

export interface TurnResponse {
  conversation_id: string;
  turn_id: string;
  status: "completed" | "partial";
  user: {
    transcript: string;
  };
  pally: {
    text: string;
    audio_url: string | null;
    audio_expires_at: string | null;
  };
  axes: Axes;
  character: CharacterParams;
  feedback: FeedbackItem[];
  warnings: ApiWarning[];
  quota: UsageQuota;
  created_at: string;
}

export interface UsageResponse {
  quota: UsageQuota;
  plan: "free";
}

export interface OnboardingInput {
  display_name: string;
  english_level: Level;
}

export interface UpdateProfileInput {
  display_name?: string;
  english_level?: Level;
}

export interface TurnInput {
  audio: Blob;
  client_started_at?: string;
  idempotency_key: string;
}

export interface ListConversationsInput {
  cursor?: string;
  limit?: number;
  status?: ConversationStatus;
}

export interface GetConversationInput {
  cursor?: string;
  limit?: number;
}

export interface PallyApi {
  getProfile(): Promise<ProfileResponse>;
  onboard(input: OnboardingInput): Promise<ProfileResponse>;
  updateProfile(input: UpdateProfileInput): Promise<ProfileResponse>;
  createConversation(idempotencyKey: string): Promise<ConversationResponse>;
  createTurn(conversationId: string, input: TurnInput): Promise<TurnResponse>;
  completeConversation(conversationId: string): Promise<ConversationResponse>;
  listConversations(input?: ListConversationsInput): Promise<ConversationListResponse>;
  getConversation(conversationId: string, input?: GetConversationInput): Promise<ConversationDetailResponse>;
  getUsage(): Promise<UsageResponse>;
  deleteConversations(idempotencyKey: string): Promise<void>;
  deleteAccount(idempotencyKey: string): Promise<void>;
}

export type ApiErrorCode =
  | "unauthorized"
  | "not_found"
  | "profile_not_found"
  | "invalid_audio"
  | "payload_too_large"
  | "validation_error"
  | "speech_not_recognized"
  | "quota_exceeded"
  | "conflict"
  | "conversation_closed"
  | "idempotency_conflict"
  | "persistence_failed"
  | "service_unavailable";

export class PallyApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number;
  readonly requestId: string;

  constructor(status: number, code: ApiErrorCode, message: string) {
    super(message);
    this.name = "PallyApiError";
    this.status = status;
    this.code = code;
    this.requestId = createRequestId();
  }
}

function createRequestId(): string {
  const suffix = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `req_${suffix}`;
}
