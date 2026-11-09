import { z } from "zod";

export const pallySegmentSchema = z.object({
  // Older saved replies keep their text, without a separate expression category.
  kind: z.preprocess(
    (kind) => kind === "new_expr" ? "own_remark" : kind,
    z.enum(["correction", "own_remark", "question", "plain"]),
  ),
  text: z.string(),
});

export const pallySegmentsSchema = z.array(pallySegmentSchema).min(1);

export type PallySegment = z.infer<typeof pallySegmentSchema>;

interface PallySegmentsSource {
  response: "turn" | "conversation_detail";
  path: readonly (string | number)[];
}

export function normalizePallySegments(
  raw: unknown,
  text: string | null,
  source: PallySegmentsSource,
): PallySegment[] | null {
  if (raw === null || raw === undefined) return null;

  const parsed = pallySegmentsSchema.safeParse(raw);
  if (!parsed.success) {
    console.error("Invalid Pally segments.", {
      ...source,
      reason: "invalid_shape",
      issues: parsed.error.issues.map((issue) => ({
        code: issue.code,
        path: [...source.path, ...issue.path],
      })),
    });
    return null;
  }

  if (text === null) {
    console.error("Invalid Pally segments.", { ...source, reason: "missing_text" });
    return null;
  }

  if (parsed.data.map((segment) => segment.text).join("") !== text) {
    console.error("Invalid Pally segments.", { ...source, reason: "text_mismatch" });
    return null;
  }

  return parsed.data;
}
