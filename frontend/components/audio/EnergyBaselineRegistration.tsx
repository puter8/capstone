"use client";

import { useEffect, useRef, useState } from "react";
import { pallyApi } from "@/lib/api";
import { blobToMonoWav } from "@/lib/audio/blobToWav";
import { useRecorder } from "@/lib/audio/useRecorder";

const PROMPTS = [
  "오늘 어떻게 하루를 보냈는지 평소 목소리로 이야기해 주세요.",
  "좋아하는 음식과 그 이유를 평소처럼 이야기해 주세요.",
  "이번 주에 하고 싶은 일을 편안하게 이야기해 주세요.",
];
type Clip = { blob: Blob; url: string };

export function EnergyBaselineRegistration({ onReady }: { onReady: () => void }) {
  const [clips, setClips] = useState<Clip[]>([]);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);
  const clipsRef = useRef<Clip[]>([]);
  const requestKey = useRef<string | null>(null);

  const recorder = useRecorder({
    enableTranscript: false,
    onStart: () => { setRecording(true); setBusy(false); },
    onStop: (blob) => {
      if (!mounted.current) return;
      setRecording(false);
      setBusy(true);
      void (async () => {
        try {
          if (!blob) throw new Error("목소리가 녹음되지 않았어요. 다시 시도해 주세요.");
          const wav = await blobToMonoWav(blob);
          // blobToMonoWav emits a 44-byte header and 16 kHz mono PCM16 samples.
          if ((wav.size - 44) / 32000 < 5) throw new Error("5초 이상 편안하게 이야기한 뒤 다시 녹음해 주세요.");
          if (!mounted.current) return;
          const next = [...clipsRef.current, { blob: wav, url: URL.createObjectURL(wav) }];
          clipsRef.current = next;
          setClips(next);
          requestKey.current = null;
        } catch (caught) {
          if (mounted.current) setError(caught instanceof Error ? caught.message : "녹음을 처리하지 못했어요.");
        } finally { if (mounted.current) setBusy(false); }
      })();
    },
    onPermissionDenied: () => { setBusy(false); setError("브라우저 설정에서 마이크 권한을 허용해 주세요."); },
    onError: (message) => { setRecording(false); setBusy(false); setError(message); },
  });
  const cancel = recorder.cancel;
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      cancel();
      clipsRef.current.forEach((clip) => URL.revokeObjectURL(clip.url));
    };
  }, [cancel]);

  const save = async () => {
    if (clips.length !== 3 || busy || recording) return;
    setBusy(true);
    setError(null);
    requestKey.current ??= crypto.randomUUID();
    try {
      const result = await pallyApi.registerEnergyBaseline([clips[0].blob, clips[1].blob, clips[2].blob], requestKey.current);
      if (result.status !== "ready") throw new Error("목소리 등록이 완료되지 않았어요. 다시 시도해 주세요.");
      if (mounted.current) onReady();
    } catch (caught) {
      if (mounted.current) setError(caught instanceof Error ? caught.message : "등록하지 못했어요. 다시 시도해 주세요.");
    } finally { if (mounted.current) setBusy(false); }
  };

  return (
    <section className="mx-auto flex w-full max-w-sm flex-col gap-4 px-5 pb-28 pt-12" aria-labelledby="baseline-title">
      <h1 id="baseline-title" className="text-title-1">평소 목소리를 알려 주세요</h1>
      <p className="text-body text-text-secondary">처음 한 번, 녹음 3개가 필요해요. 이전에 사용하셨던 분도 등록해 주세요. 평소 억양과 비교해 대화의 에너지를 살펴봐요.</p>
      <p className="text-body">각각 5~30초 동안 영어로, 평소 목소리로 이야기해 주세요. 캐릭터 변화는 대화를 마친 뒤 보여 드려요.</p>
      <p role="status">녹음 {clips.length} / 3 완료{recording ? " · 녹음 중" : busy ? " · 처리 중" : ""}</p>
      {clips.map((clip, index) => (
        <div key={clip.url} className="flex flex-col gap-2 rounded-xl bg-white p-3">
          <span>녹음 {index + 1}</span>
          <audio className="w-full min-w-0" controls src={clip.url} aria-label={`녹음 ${index + 1} 다시 듣기`} />
          <button className="self-start underline" type="button" disabled={busy || recording} onClick={() => {
            URL.revokeObjectURL(clip.url);
            const next = clips.filter((_, i) => i !== index);
            clipsRef.current = next; setClips(next); requestKey.current = null;
          }}>이 녹음 지우고 다시 하기</button>
        </div>
      ))}
      {clips.length < 3 ? <>
        <p>{PROMPTS[clips.length]}</p>
        <button className="rounded-full bg-primary p-4 text-white disabled:opacity-50" disabled={busy} type="button" onClick={() => {
          setError(null);
          if (recording) { setBusy(true); recorder.stop(); }
          else { setBusy(true); void recorder.start(); }
        }}>{recording ? "녹음 마치기" : `${clips.length + 1}번째 녹음 시작`}</button>
      </> : <button className="rounded-full bg-primary p-4 text-white disabled:opacity-50" disabled={busy} type="button" onClick={() => { void save(); }}>{busy ? "목소리 확인 중…" : "목소리 등록하고 시작하기"}</button>}
      {error ? <p role="alert" className="text-body text-red-700">{error}</p> : null}
    </section>
  );
}
