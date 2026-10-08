import type { z } from "zod";

import type {
  ActivityEventInput,
  DeleteAccountInput,
  CheckoutInput,
  GetConversationInput,
  ListConversationsInput,
  OnboardingInput,
  PallyApi,
  TurnInput,
  UpdateProfileInput,
} from "@/lib/api/contracts";
import { PallyApiError } from "@/lib/api/contracts";
import {
  NETWORK_ERROR_MESSAGE,
  SESSION_ERROR_MESSAGE,
  UNREADABLE_RESPONSE_MESSAGE,
  userFacingErrorMessage,
} from "@/lib/api/error-messages";
import {
  achievementsResponseSchema,
  deleteAccountResponseSchema,
  deleteConversationHistoryResponseSchema,
  billingProductsResponseSchema,
  billingOverviewResponseSchema,
  checkoutResponseSchema,
  conversationDetailResponseSchema,
  conversationListResponseSchema,
  conversationCompleteResponseSchema,
  conversationMutationResponseSchema,
  conversationResponseSchema,
  errorResponseSchema,
  profileResponseSchema,
  profileAvatarResponseSchema,
  recordedEventResponseSchema,
  speechResponseSchema,
  openerResponseSchema,
  subscriptionResponseSchema,
  turnResponseSchema,
  usageResponseSchema,
} from "@/lib/api/schemas";
import { supabase } from "@/lib/supabase/client";

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;

function createIdempotencyKey(): string {
  return crypto.randomUUID();
}

type AccountBinding = { expectedUserId: string };

async function getAccessToken(accountBinding?: AccountBinding): Promise<string> {
  const { data, error } = await supabase.auth.getSession();
  if (error) {
    console.error("Reading the login session failed", error);
    throw new PallyApiError(401, "unauthorized", SESSION_ERROR_MESSAGE);
  }
  const session = data.session;
  const token = session?.access_token;
  if (!token) throw new PallyApiError(401, "unauthorized", "로그인이 필요해요.");
  if (accountBinding && (!accountBinding.expectedUserId || session.user.id !== accountBinding.expectedUserId)) {
    throw new PallyApiError(401, "unauthorized", "로그인 계정이 변경됐어요. 다시 로그인해 주세요.");
  }
  return token;
}

type RequestOptions<TSchema extends z.ZodType> = {
  schema: TSchema;
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: BodyInit;
  contentType?: "application/json";
  idempotencyKey?: string;
  accountBinding?: AccountBinding;
};

async function apiRequest<TSchema extends z.ZodType>(path: string, options: RequestOptions<TSchema>): Promise<z.infer<TSchema>> {
  if (!backendUrl) throw new PallyApiError(503, "service_unavailable", "NEXT_PUBLIC_BACKEND_URL이 설정되지 않았어요.");

  const token = await getAccessToken(options.accountBinding);
  const headers = new Headers({ Authorization: `Bearer ${token}` });
  if (options.contentType) headers.set("Content-Type", options.contentType);
  if (options.idempotencyKey) headers.set("Idempotency-Key", options.idempotencyKey);

  let response: Response;
  try {
    response = await fetch(`${backendUrl}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body,
    });
  } catch (error) {
    console.error("API request could not reach the server", { path, error });
    throw new PallyApiError(0, "network_error", NETWORK_ERROR_MESSAGE);
  }

  const payload: unknown = await response.json().catch((error: unknown) => {
    console.error("API response was not JSON", { path, status: response.status, error });
    throw new PallyApiError(502, "invalid_response", UNREADABLE_RESPONSE_MESSAGE);
  });

  if (!response.ok) {
    const parsedError = errorResponseSchema.safeParse(payload);
    if (!parsedError.success) {
      throw new PallyApiError(response.status, "invalid_response", `서버 오류 응답 형식이 올바르지 않아요. (${response.status})`);
    }
    const { code, message, request_id: requestId } = parsedError.data.error;
    console.error("API request failed", { path, status: response.status, code, message, requestId });
    throw new PallyApiError(response.status, code, userFacingErrorMessage(response.status, code, message), requestId);
  }

  const parsed = options.schema.safeParse(payload);
  if (!parsed.success) {
    console.error("API response validation failed", { path, issues: parsed.error.issues });
    throw new PallyApiError(502, "invalid_response", "서버 응답 형식이 앱과 맞지 않아요.");
  }
  return parsed.data;
}

function queryString(input: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(input)) {
    if (value !== undefined) params.set(key, String(value));
  }
  const value = params.toString();
  return value ? `?${value}` : "";
}

export const httpPallyApi: PallyApi = {
  getProfile: () => apiRequest("/api/profile", { schema: profileResponseSchema }),

  getProfileAvatar: () => apiRequest("/api/profile/avatar", { schema: profileAvatarResponseSchema }),

  onboard: (input: OnboardingInput) => apiRequest("/api/onboarding", {
    schema: profileResponseSchema,
    method: "POST",
    contentType: "application/json",
    idempotencyKey: createIdempotencyKey(),
    body: JSON.stringify(input),
  }),

  updateProfile: (input: UpdateProfileInput) => apiRequest("/api/profile", {
    schema: profileResponseSchema,
    method: "PATCH",
    contentType: "application/json",
    body: JSON.stringify(input),
  }),

  createConversation: (idempotencyKey: string) => apiRequest("/api/conversations", {
    schema: conversationResponseSchema,
    method: "POST",
    idempotencyKey,
  }),

  async createTurn(conversationId: string, input: TurnInput) {
    const formData = new FormData();
    const extension = input.audio.type.includes("wav") ? "wav" : input.audio.type.includes("mp4") ? "mp4" : "webm";
    formData.append("audio", input.audio, `recording.${extension}`);
    return apiRequest(`/api/conversations/${encodeURIComponent(conversationId)}/turns`, {
      schema: turnResponseSchema,
      method: "POST",
      idempotencyKey: input.idempotency_key,
      body: formData,
    });
  },

  createOpener: (conversationId: string, idempotencyKey: string) => apiRequest(`/api/conversations/${encodeURIComponent(conversationId)}/opener`, {
    schema: openerResponseSchema,
    method: "POST",
    idempotencyKey,
  }),

  synthesizeSpeech: (text: string) => apiRequest("/api/tts", {
    schema: speechResponseSchema,
    method: "POST",
    contentType: "application/json",
    body: JSON.stringify({ text }),
  }),

  completeConversation: (conversationId: string) => apiRequest(`/api/conversations/${encodeURIComponent(conversationId)}/complete`, {
    schema: conversationCompleteResponseSchema,
    method: "POST",
    idempotencyKey: createIdempotencyKey(),
  }),

  reopenConversation: (conversationId: string) => apiRequest(`/api/conversations/${encodeURIComponent(conversationId)}/reopen`, {
    schema: conversationMutationResponseSchema,
    method: "POST",
    idempotencyKey: createIdempotencyKey(),
  }),

  listConversations(input: ListConversationsInput = {}) {
    return apiRequest(`/api/conversations${queryString({ cursor: input.cursor, limit: input.limit, status: input.status })}`, { schema: conversationListResponseSchema });
  },

  getConversation(conversationId: string, input: GetConversationInput = {}) {
    return apiRequest(`/api/conversations/${encodeURIComponent(conversationId)}${queryString({ cursor: input.cursor, limit: input.limit })}`, {
      schema: conversationDetailResponseSchema,
    });
  },

  getUsage: () => apiRequest("/api/usage", { schema: usageResponseSchema }),

  async recordActivityEvent(input: ActivityEventInput) {
    await apiRequest("/api/activity-events", {
      schema: recordedEventResponseSchema,
      method: "POST",
      contentType: "application/json",
      idempotencyKey: createIdempotencyKey(),
      body: JSON.stringify(input),
    });
  },

  getAchievements: () => apiRequest("/api/achievements", { schema: achievementsResponseSchema }),

  getBillingProducts: () => apiRequest("/api/billing/products", { schema: billingProductsResponseSchema }),

  getBillingOverview: () => apiRequest("/api/billing/overview", { schema: billingOverviewResponseSchema }),

  createCheckout: (input: CheckoutInput, expectedUserId: string) => apiRequest("/api/billing/checkout", {
    schema: checkoutResponseSchema,
    method: "POST",
    contentType: "application/json",
    idempotencyKey: createIdempotencyKey(),
    body: JSON.stringify(input),
    accountBinding: { expectedUserId },
  }),

  getSubscription: () => apiRequest("/api/subscription", { schema: subscriptionResponseSchema }),

  refreshSubscription: (expectedUserId: string) => apiRequest("/api/subscription/refresh", {
    schema: subscriptionResponseSchema,
    method: "POST",
    idempotencyKey: createIdempotencyKey(),
    accountBinding: { expectedUserId },
  }),

  cancelSubscription: (expectedUserId: string) => apiRequest("/api/subscription/cancel", {
    schema: subscriptionResponseSchema,
    method: "POST",
    idempotencyKey: createIdempotencyKey(),
    accountBinding: { expectedUserId },
  }),

  deleteAccount: (input: DeleteAccountInput) => apiRequest("/api/account", {
    schema: deleteAccountResponseSchema,
    method: "DELETE",
    contentType: "application/json",
    body: JSON.stringify(input),
  }),

  deleteConversationHistory: (expectedUserId: string) => apiRequest("/api/conversations", {
    schema: deleteConversationHistoryResponseSchema,
    method: "DELETE",
    accountBinding: { expectedUserId },
  }),

};
