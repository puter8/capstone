/** Date and duration labels for the v2 screens, always in KST. */

const KST = "Asia/Seoul";

function kstDateKey(date: Date): string {
  return new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "2-digit", day: "2-digit", timeZone: KST }).format(date);
}

/** "오늘", "어제", "10월 15일" or "2025년 12월 3일" for a past year. */
export function formatDayGroup(iso: string, now: Date = new Date()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const key = kstDateKey(date);
  if (key === kstDateKey(now)) return "오늘";
  if (key === kstDateKey(new Date(now.getTime() - 86_400_000))) return "어제";
  const sameYear = key.slice(0, 4) === kstDateKey(now).slice(0, 4);
  return new Intl.DateTimeFormat("ko-KR", { ...(sameYear ? {} : { year: "numeric" }), month: "long", day: "numeric", timeZone: KST }).format(date);
}

/** "10월 23일 금요일" */
export function formatLongDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("ko-KR", { month: "long", day: "numeric", weekday: "long", timeZone: KST }).format(date);
}

/** "오후 9:41" */
export function formatClockTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("ko-KR", { hour: "numeric", minute: "2-digit", hour12: true, timeZone: KST }).format(date);
}

/** Whole minutes between start and end, at least 1; null when the end is unknown. */
export function formatDurationMinutes(startIso: string, endIso: string | null): string | null {
  if (!endIso) return null;
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return null;
  const minutes = Math.max(1, Math.round((end - start) / 60_000));
  return `${minutes}분`;
}
