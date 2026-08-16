import type {
  ConversationDetailResponse,
  ConversationListItem,
  ConversationListResponse,
  ConversationResponse,
  ConversationTurn,
  GetConversationInput,
  ListConversationsInput,
  OnboardingInput,
  PallyApi,
  ProfileResponse,
  TurnInput,
  TurnResponse,
  UpdateProfileInput,
  UsageResponse,
} from "@/lib/api/contracts";
import { PallyApiError } from "@/lib/api/contracts";
import {
  MOCK_CONVERSATIONS,
  MOCK_PROFILE,
  MOCK_QUOTA,
  MOCK_SILENT_AUDIO_URL,
  MOCK_TURNS,
  MOCK_TURN_SCRIPTS,
  createEmptyConversation,
} from "@/lib/api/mock-data";

const ALLOWED_AUDIO_TYPES = new Set([
  "audio/webm",
  "audio/wav",
  "audio/mp4",
  "audio/mpeg",
]);
const MAX_AUDIO_BYTES = 10 * 1024 * 1024;
const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 50;

interface MockConversationRecord {
  conversation: ConversationResponse["conversation"];
  turns: ConversationTurn[];
}

interface MockState {
  accountDeleted: boolean;
  profile: ProfileResponse["profile"];
  quota: UsageResponse["quota"];
  records: MockConversationRecord[];
}

interface IdempotencyEntry {
  operation: string;
  result: unknown;
}

const idempotencyCache = new Map<string, IdempotencyEntry>();
let mockState = createInitialState();

function createInitialState(): MockState {
  return {
    accountDeleted: false,
    profile: clone(MOCK_PROFILE),
    quota: clone(MOCK_QUOTA),
    records: MOCK_CONVERSATIONS.map((conversation) => ({
      conversation: clone(conversation),
      turns: MOCK_TURNS.filter((turn) => turn.conversation_id === conversation.id).map(clone),
    })),
  };
}

function clone<T>(value: T): T {
  return typeof structuredClone === "function"
    ? structuredClone(value)
    : JSON.parse(JSON.stringify(value)) as T;
}

function createUuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  const suffix = `${Date.now().toString(16)}${Math.random().toString(16).slice(2)}`.padEnd(32, "0").slice(0, 32);
  return `${suffix.slice(0, 8)}-${suffix.slice(8, 12)}-4${suffix.slice(13, 16)}-8${suffix.slice(17, 20)}-${suffix.slice(20)}`;
}

function ensureActiveAccount(): void {
  if (mockState.accountDeleted) {
    throw new PallyApiError(401, "unauthorized", "삭제된 mock 계정이에요. 로그인 화면에서 다시 시작해 주세요.");
  }
}

function getRecord(conversationId: string): MockConversationRecord {
  const record = mockState.records.find((item) => item.conversation.id === conversationId);
  if (!record) {
    throw new PallyApiError(404, "not_found", "대화를 찾을 수 없어요.");
  }
  return record;
}

function parseCursor(cursor?: string): number {
  if (!cursor) return 0;
  const match = /^cursor:(\d+)$/.exec(cursor);
  if (!match) {
    throw new PallyApiError(422, "validation_error", "올바르지 않은 cursor예요.");
  }
  return Number(match[1]);
}

function normalizeLimit(limit?: number): number {
  if (limit === undefined) return DEFAULT_LIMIT;
  if (!Number.isInteger(limit) || limit < 1 || limit > MAX_LIMIT) {
    throw new PallyApiError(422, "validation_error", `limit은 1~${MAX_LIMIT} 사이의 정수여야 해요.`);
  }
  return limit;
}

function withIdempotency<T>(key: string, operation: string, create: () => T): T {
  if (!key) {
    throw new PallyApiError(422, "validation_error", "Idempotency-Key가 필요해요.");
  }

  const cached = idempotencyCache.get(key);
  if (cached) {
    if (cached.operation !== operation) {
      throw new PallyApiError(409, "idempotency_conflict", "같은 idempotency key를 다른 요청에 사용할 수 없어요.");
    }
    return clone(cached.result as T);
  }

  const result = create();
  idempotencyCache.set(key, { operation, result: clone(result) });
  return clone(result);
}

function toListItem(record: MockConversationRecord): ConversationListItem {
  const userTurn = record.turns.find((turn) => turn.user_transcript);
  return {
    ...clone(record.conversation),
    feedback_count: record.turns.reduce((sum, turn) => sum + turn.feedback.length, 0),
    preview: userTurn?.user_transcript ?? null,
  };
}

function delay(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 120));
}

export function resetMockPallyApi(): void {
  mockState = createInitialState();
  idempotencyCache.clear();
  if (typeof window !== "undefined") {
    window.localStorage.removeItem("pally:conversationId");
  }
}

export const mockPallyApi: PallyApi = {
  async getProfile() {
    await delay();
    ensureActiveAccount();
    return { profile: clone(mockState.profile) };
  },

  async onboard(input: OnboardingInput) {
    await delay();
    ensureActiveAccount();
    if (mockState.profile.onboarding_completed) {
      throw new PallyApiError(409, "conflict", "이미 온보딩을 완료했어요.");
    }

    const displayName = input.display_name.trim();
    if (displayName.length < 1 || displayName.length > 30) {
      throw new PallyApiError(422, "validation_error", "이름은 1~30자로 입력해 주세요.");
    }

    mockState.profile = {
      ...mockState.profile,
      display_name: displayName,
      english_level: input.english_level,
      onboarding_completed: true,
      updated_at: new Date().toISOString(),
    };
    return { profile: clone(mockState.profile) };
  },

  async updateProfile(input: UpdateProfileInput) {
    await delay();
    ensureActiveAccount();
    if (input.display_name === undefined && input.english_level === undefined) {
      throw new PallyApiError(422, "validation_error", "수정할 프로필 필드가 필요해요.");
    }

    const nextName = input.display_name?.trim();
    if (nextName !== undefined && (nextName.length < 1 || nextName.length > 30)) {
      throw new PallyApiError(422, "validation_error", "이름은 1~30자로 입력해 주세요.");
    }

    mockState.profile = {
      ...mockState.profile,
      ...(nextName === undefined ? {} : { display_name: nextName }),
      ...(input.english_level === undefined ? {} : { english_level: input.english_level }),
      updated_at: new Date().toISOString(),
    };
    return { profile: clone(mockState.profile) };
  },

  async createConversation(idempotencyKey: string) {
    await delay();
    ensureActiveAccount();
    return withIdempotency(idempotencyKey, "create_conversation", () => {
      const now = new Date().toISOString();
      const record: MockConversationRecord = {
        conversation: createEmptyConversation(createUuid(), now),
        turns: [],
      };
      mockState.records.unshift(record);
      return { conversation: record.conversation };
    });
  },

  async createTurn(conversationId: string, input: TurnInput) {
    await delay();
    ensureActiveAccount();
    const operation = `create_turn:${conversationId}`;
    return withIdempotency(input.idempotency_key, operation, () => {
      const record = getRecord(conversationId);
      if (record.conversation.status !== "active") {
        throw new PallyApiError(409, "conversation_closed", "종료된 대화에는 turn을 추가할 수 없어요.");
      }
      if (input.audio.size === 0) {
        throw new PallyApiError(422, "speech_not_recognized", "인식할 수 있는 음성이 없어요.");
      }
      if (input.audio.size > MAX_AUDIO_BYTES) {
        throw new PallyApiError(413, "payload_too_large", "오디오는 10 MiB 이하여야 해요.");
      }
      const mime = input.audio.type.split(";", 1)[0];
      if (!ALLOWED_AUDIO_TYPES.has(mime)) {
        throw new PallyApiError(400, "invalid_audio", "지원하지 않는 오디오 형식이에요.");
      }
      if (mockState.quota.exhausted || mockState.quota.remaining_turns <= 0) {
        throw new PallyApiError(429, "quota_exceeded", "오늘 사용할 수 있는 대화를 모두 사용했어요.");
      }

      const totalTurns = mockState.records.reduce((sum, item) => sum + item.turns.length, 0);
      const script = MOCK_TURN_SCRIPTS[totalTurns % MOCK_TURN_SCRIPTS.length];
      const createdAt = new Date().toISOString();
      const expiresAt = new Date(Date.now() + 60 * 60 * 1000).toISOString();
      const turnId = createUuid();
      const turn: ConversationTurn = {
        id: turnId,
        conversation_id: conversationId,
        sequence: record.turns.length + 1,
        status: "completed",
        user_transcript: script.transcript,
        pally_text: script.reply,
        pally_audio_url: MOCK_SILENT_AUDIO_URL,
        axes: clone(script.axes),
        character: clone(script.character),
        feedback: clone(script.feedback),
        warnings: [],
        created_at: createdAt,
      };

      record.turns.push(turn);
      record.conversation = {
        ...record.conversation,
        title: record.conversation.title ?? "New Pally conversation",
        last_turn_at: createdAt,
        turn_count: record.turns.length,
        current_axes: clone(script.axes),
      };
      mockState.quota = {
        ...mockState.quota,
        remaining_turns: mockState.quota.remaining_turns - 1,
        exhausted: mockState.quota.remaining_turns - 1 === 0,
      };

      const response: TurnResponse = {
        conversation_id: conversationId,
        turn_id: turnId,
        status: "completed",
        user: { transcript: script.transcript },
        pally: {
          text: script.reply,
          audio_url: MOCK_SILENT_AUDIO_URL,
          audio_expires_at: expiresAt,
        },
        axes: clone(script.axes),
        character: clone(script.character),
        feedback: clone(script.feedback),
        warnings: [],
        quota: clone(mockState.quota),
        created_at: createdAt,
      };
      return response;
    });
  },

  async completeConversation(conversationId: string) {
    await delay();
    ensureActiveAccount();
    const record = getRecord(conversationId);
    if (record.conversation.status === "active") {
      record.conversation = {
        ...record.conversation,
        status: "completed",
        completed_at: new Date().toISOString(),
      };
    }
    return { conversation: clone(record.conversation) };
  },

  async listConversations(input: ListConversationsInput = {}): Promise<ConversationListResponse> {
    await delay();
    ensureActiveAccount();
    const start = parseCursor(input.cursor);
    const limit = normalizeLimit(input.limit);
    const records = mockState.records
      .filter((record) => !input.status || record.conversation.status === input.status)
      .sort((a, b) => {
        const aDate = a.conversation.last_turn_at ?? a.conversation.started_at;
        const bDate = b.conversation.last_turn_at ?? b.conversation.started_at;
        return bDate.localeCompare(aDate);
      });
    const page = records.slice(start, start + limit);
    return {
      items: page.map(toListItem),
      next_cursor: start + limit < records.length ? `cursor:${start + limit}` : null,
    };
  },

  async getConversation(conversationId: string, input: GetConversationInput = {}): Promise<ConversationDetailResponse> {
    await delay();
    ensureActiveAccount();
    const record = getRecord(conversationId);
    const start = parseCursor(input.cursor);
    const limit = normalizeLimit(input.limit);
    return {
      conversation: clone(record.conversation),
      turns: record.turns.slice(start, start + limit).map(clone),
      next_cursor: start + limit < record.turns.length ? `cursor:${start + limit}` : null,
    };
  },

  async getUsage() {
    await delay();
    ensureActiveAccount();
    return { quota: clone(mockState.quota), plan: "free" };
  },

  async deleteConversations(idempotencyKey: string) {
    await delay();
    ensureActiveAccount();
    withIdempotency(idempotencyKey, "delete_conversations", () => {
      mockState.records = [];
      return null;
    });
  },

  async deleteAccount(idempotencyKey: string) {
    await delay();
    withIdempotency(idempotencyKey, "delete_account", () => {
      mockState.records = [];
      mockState.accountDeleted = true;
      return null;
    });
  },
};
