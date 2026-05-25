/**
 * Phase 1A — MediaRecorder MIME-type probe.
 *
 * Chrome / Firefox / Edge support audio/webm (Opus codec); iOS Safari 14.1+
 * only supports audio/mp4. Hardcoding either fails on the other.
 *
 * Probe order locked by CONTEXT D-05 + RESEARCH Pattern 3. Returns the first
 * supported MIME or null when nothing is supported (caller surfaces a
 * "이 브라우저는 음성 녹음을 지원하지 않아요." inline error per UI-SPEC
 * § Copywriting Contract → "Error and permission states").
 */

const CANDIDATES = [
  'audio/webm;codecs=opus',       // Chrome / Firefox / Edge — preferred
  'audio/webm',                    // Chrome / Firefox / Edge — fallback
  'audio/mp4',                     // Safari (iOS + macOS)
  'audio/mp4;codecs=mp4a.40.2',    // Safari — explicit AAC
] as const;

export function pickMimeType(): string | null {
  if (typeof MediaRecorder === 'undefined') {
    return null;
  }
  for (const mime of CANDIDATES) {
    if (MediaRecorder.isTypeSupported(mime)) {
      return mime;
    }
  }
  return null;
}
