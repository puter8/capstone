import { z } from "zod";
import { normalizePallySegments } from "@/lib/api/pally-segments";

export const axesSchema = z.object({
  Formality: z.number().min(0).max(100),
  Energy: z.number().min(0).max(100),
  Intimacy: z.number().min(0).max(100),
  Humor: z.number().min(0).max(100),
  Curiosity: z.number().min(0).max(100),
});

const characterSchema = z.object({
  tone_casual: z.number().min(0).max(100),
  energy_level: z.number().min(0).max(100),
  humor_level: z.number().min(0).max(100),
});

const feedbackSchema = z.object({
  id: z.string().optional(),
  original: z.string(),
  corrected: z.string(),
  explanation_ko: z.string(),
  replacement: z.string().optional(),
});

const warningSchema = z.object({
  code: z.enum(["tts_failed", "feedback_failed", "traits_update_failed", "energy_unavailable"]),
  message: z.string(),
});

export const openerResponseSchema = z.object({
  text: z.string().trim().min(1),
  audio: z.string().nullable(),
  warnings: z.array(warningSchema),
});

const conversationSchema = z.object({
  id: z.string().uuid(),
  status: z.enum(["active", "completed"]),
  title: z.string().nullable(),
  started_at: z.string(),
  last_turn_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  turn_count: z.number().int().nonnegative(),
  current_axes: axesSchema.optional(),
  reopened_at: z.string().nullable().optional(),
  reopen_count: z.number().int().nonnegative().optional(),
});

export const profileResponseSchema = z.object({
  profile: z.object({
    id: z.string().uuid(),
    display_name: z.string(),
    english_level: z.enum(["A2", "B1", "B2", "C1"]),
    onboarding_completed: z.boolean(),
    traits: z.array(z.string()),
    avatar_url: z.string().url().nullable(),
    created_at: z.string(),
    updated_at: z.string(),
    // Pally's current look: the final axes of the last conversation the user spoke in.
    // Optional so the frontend keeps validating against a backend deployed before it.
    current_axes: axesSchema.optional(),
  }),
});

export const profileAvatarResponseSchema = z.object({
  avatar_url: z.string().url().nullable(),
});

export const conversationResponseSchema = z.object({ conversation: conversationSchema });

export const conversationMutationResponseSchema = z.object({
  conversation: conversationSchema.partial().required({ id: true, status: true }),
});

export const speechResponseSchema = z.object({
  audio_b64: z.string().min(1),
  voice: z.string(),
  encoding: z.literal("MP3"),
});

export const conversationCompleteResponseSchema = conversationMutationResponseSchema.extend({
  warnings: z.array(warningSchema),
  // 음성 Energy 를 껐을 때는 서버가 보내지 않으므로 optional.
  current_axes: axesSchema.optional(),
  energy: z.object({
    status: z.string(),
    score: z.number().min(0).max(100).nullable(),
    reason: z.string().nullable(),
  }).optional(),
});

const energyBaselinePromptsSchema = z.tuple([
  z.string().trim().min(1),
  z.string().trim().min(1),
  z.string().trim().min(1),
]);

const energyBaselineLimitsSchema = z.object({
  clips: z.literal(3),
  min_seconds: z.number().finite().positive().max(30),
  max_seconds: z.number().finite().positive().max(30),
}).refine((limits) => limits.min_seconds <= limits.max_seconds, {
  message: "The minimum recording length cannot exceed the maximum.",
  path: ["min_seconds"],
});

export const energyBaselineResponseSchema = z.discriminatedUnion("status", [
  z.object({
    status: z.literal("ready"),
    baseline: z.object({
      range_st: z.number().finite().nonnegative(),
      valid_clips: z.literal(3),
      method_version: z.string().min(1),
    }),
    prompts: energyBaselinePromptsSchema,
    limits: energyBaselineLimitsSchema,
  }),
  z.object({
    status: z.literal("required"),
    baseline: z.null(),
    prompts: energyBaselinePromptsSchema,
    limits: energyBaselineLimitsSchema,
  }),
  z.object({ status: z.literal("disabled"), baseline: z.null(), prompts: z.tuple([]), limits: z.null() }),
]);

export const conversationListResponseSchema = z.object({
  items: z.array(conversationSchema.extend({
    title: z.string().nullable(),
    started_at: z.string(),
    last_turn_at: z.string().nullable(),
    completed_at: z.string().nullable(),
    turn_count: z.number().int().nonnegative(),
    feedback_count: z.number().int().nonnegative(),
    preview: z.string().nullable(),
  })),
  next_cursor: z.string().nullable(),
});

export const conversationDetailResponseSchema = z.object({
  conversation: conversationSchema.extend({
    title: z.string().nullable(),
    started_at: z.string(),
    last_turn_at: z.string().nullable(),
    completed_at: z.string().nullable(),
    turn_count: z.number().int().nonnegative(),
  }),
  turns: z.array(z.object({
    id: z.string().uuid(),
    sequence: z.number().int().positive(),
    status: z.enum(["processing", "completed", "partial", "failed"]),
    user_transcript: z.string().nullable(),
    pally_text: z.string().nullable(),
    pally_segments: z.unknown().optional(),
    feedback: z.array(feedbackSchema),
    feedback_pending: z.boolean(),
    created_at: z.string(),
  })),
  next_cursor: z.string().nullable(),
}).transform((response) => ({
  ...response,
  turns: response.turns.map((turn, index) => ({
    ...turn,
    pally_segments: normalizePallySegments(turn.pally_segments, turn.pally_text, {
      response: "conversation_detail",
      path: ["turns", index, "pally_segments"],
    }),
  })),
}));

export const turnResponseSchema = z.object({
  conversation_id: z.string().uuid(),
  turn_id: z.string().uuid().nullable(),
  status: z.enum(["completed", "partial"]),
  replayed: z.boolean(),
  user: z.object({ transcript: z.string() }),
  pally: z.object({
    text: z.string(),
    audio: z.string().nullable(),
    segments: z.unknown().optional(),
  }),
  axes: axesSchema,
  character: characterSchema,
  feedback: z.array(feedbackSchema),
  feedback_pending: z.boolean(),
  warnings: z.array(warningSchema),
  quota: z.object({
    used_turns: z.number().int().nonnegative().optional(),
    remaining_turns: z.number().int().nonnegative().nullable(),
    daily_limit: z.number().int().positive().nullable(),
    exhausted: z.boolean(),
    resets_at: z.string(),
  }).optional(),
  created_at: z.string().nullable(),
}).transform((response) => ({
  ...response,
  pally: {
    ...response.pally,
    segments: normalizePallySegments(response.pally.segments, response.pally.text, {
      response: "turn",
      path: ["pally", "segments"],
    }),
  },
}));

export const usageResponseSchema = z.object({
  plan: z.enum(["free", "pro"]),
  date: z.string(),
  timezone: z.literal("Asia/Seoul"),
  used_turns: z.number().int().nonnegative(),
  remaining_turns: z.number().int().nonnegative().nullable(),
  daily_limit: z.number().int().positive().nullable(),
  reset_at: z.string(),
});

export const achievementsResponseSchema = z.object({
  date: z.string(),
  timezone: z.literal("Asia/Seoul"),
  streak_count: z.number().int().nonnegative(),
  daily_tasks: z.array(z.object({
    id: z.string(),
    title: z.string(),
    description: z.string(),
    status: z.enum(["completed", "default"]),
    completed_at: z.string().nullable(),
  })).length(3),
});

export const billingProductsResponseSchema = z.object({
  test_mode: z.boolean(),
  products: z.array(z.object({
    id: z.string(),
    name: z.string(),
    interval: z.enum(["month", "year"]),
    amount_minor: z.number().int().nonnegative(),
    currency: z.string(),
    display_price: z.string(),
    trial_days: z.number().int().nonnegative(),
  })),
});

export const checkoutResponseSchema = z.object({
  checkout: z.object({
    product_id: z.string(),
    checkout_url: z.string().url(),
    expires_at: z.string(),
  }),
});

export const subscriptionResponseSchema = z.object({
  subscription: z.object({
    plan: z.enum(["free", "pro"]),
    status: z.string(),
    entitled: z.boolean(),
    product_id: z.string().nullable(),
    current_period_end: z.string().nullable(),
    will_renew: z.boolean(),
    entitlements: z.array(z.string()),
    updated_at: z.string().nullable(),
  }),
});

const billingOrderSummarySchema = z.object({
  id: z.string().uuid(),
  product_id: z.enum(["pro_monthly", "pro_yearly"]),
  amount: z.number().int().nonnegative(),
  currency: z.literal("KRW"),
  kind: z.enum(["initial", "renewal"]),
  trial_days: z.union([z.literal(0), z.literal(7)]),
  created_at: z.iso.datetime({ offset: true }),
});

export const billingHistoryEntrySchema = billingOrderSummarySchema.extend({
  status: z.literal("approved"),
  approved_at: z.iso.datetime({ offset: true }),
});

export const pendingBillingOrderSchema = billingOrderSummarySchema.extend({
  status: z.enum(["preparing", "ready", "processing", "uncertain"]),
  expires_at: z.iso.datetime({ offset: true }),
});

export const billingOverviewResponseSchema = z.object({
  subscription: subscriptionResponseSchema.shape.subscription,
  history: z.array(billingHistoryEntrySchema),
  history_has_more: z.boolean(),
  pending_order: pendingBillingOrderSchema.nullable(),
  checkout_blocked_reason: z.enum([
    "subscription_active",
    "payment_pending",
    "renewal_active",
    "deactivation_pending",
  ]).nullable(),
});

export const deleteAccountResponseSchema = z.object({
  status: z.literal("deleted"),
});

export const deleteConversationHistoryResponseSchema = z.object({
  status: z.literal("deleted"),
  deleted_conversations: z.number().int().nonnegative(),
});

export const errorResponseSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    request_id: z.string().optional(),
    details: z.record(z.string(), z.unknown()).optional(),
  }),
});

export const recordedEventResponseSchema = z.object({ recorded: z.literal(true) });
