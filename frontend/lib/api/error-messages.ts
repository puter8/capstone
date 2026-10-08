import { PallyApiError } from "@/lib/api/contracts";

// The backend writes some error messages in English for logs and API clients.
// Screens show `PallyApiError.message` as-is, so the API client converts them here.

export const NETWORK_ERROR_MESSAGE = "인터넷 연결을 확인하고 다시 시도해 주세요.";
export const UNREADABLE_RESPONSE_MESSAGE = "서버 응답을 읽지 못했어요. 잠시 후 다시 시도해 주세요.";
export const SESSION_ERROR_MESSAGE = "로그인 정보를 확인하지 못했어요. 다시 로그인해 주세요.";
export const SIGN_IN_ERROR_MESSAGE = "로그인을 완료하지 못했어요. 다시 시도해 주세요.";

const HANGUL = /[가-힣]/;

const MESSAGES_BY_CODE: Record<string, string> = {
  unauthorized: "로그인이 필요해요.",
  auth_unavailable: "로그인 상태를 확인하지 못했어요. 잠시 후 다시 시도해 주세요.",
  not_found: "찾을 수 없는 내용이에요.",
  profile_not_found: "프로필을 찾을 수 없어요.",
  invalid_audio: "녹음된 소리가 없어요. 다시 녹음해 주세요.",
  payload_too_large: "녹음이 너무 길어요. 조금 짧게 말해 주세요.",
  speech_not_recognized: "목소리가 잘 들리지 않았어요. 조금 더 또렷하게 다시 말해 주세요.",
  stt_failed: "음성을 인식하지 못했어요. 잠시 후 다시 시도해 주세요.",
  ai_engine_failed: "Pally가 지금 답하지 못했어요. 잠시 후 다시 시도해 주세요.",
  opener_failed: "Pally가 말을 걸지 못했어요. 다시 시도해 주세요.",
  validation_error: "입력한 내용을 확인해 주세요.",
  conflict: "이미 처리된 요청이에요.",
  quota_exceeded: "오늘 사용할 수 있는 대화를 모두 사용했어요.",
  conversation_closed: "이미 종료된 대화예요.",
  conversation_started: "이미 시작된 대화예요.",
  conversation_already_active: "대화가 이미 다시 열려 있어요. 화면을 새로고침해 주세요.",
  duplicate_turn: "같은 요청을 이미 처리하고 있어요. 잠시만 기다려 주세요.",
  idempotency_conflict: "같은 요청을 이미 처리하고 있어요. 잠시만 기다려 주세요.",
  persistence_failed: "데이터를 처리하지 못했어요. 잠시 후 다시 시도해 주세요.",
  service_unavailable: "서비스를 잠시 사용할 수 없어요. 잠시 후 다시 시도해 주세요.",
};

/** Sign-in fails in Supabase Auth (English text) or in our API (already Korean, kept as is). */
export function signInErrorMessage(caught: unknown): string {
  return caught instanceof PallyApiError ? caught.message : SIGN_IN_ERROR_MESSAGE;
}

/**
 * Korean text for an API error. A server message that is already Korean was written
 * for the user (billing, account deletion), so it is kept; English text is replaced
 * by the message for its code, or by a generic one when the code is unknown.
 */
export function userFacingErrorMessage(status: number, code: string, serverMessage: string): string {
  if (HANGUL.test(serverMessage)) return serverMessage;
  const known = MESSAGES_BY_CODE[code];
  if (known) return known;
  return status >= 500
    ? "서버에 문제가 생겼어요. 잠시 후 다시 시도해 주세요."
    : "요청을 처리하지 못했어요. 다시 시도해 주세요.";
}
