const TARGET_SAMPLE_RATE = 16000;

function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const dataLen = samples.length * 2; // 16-bit PCM
  const buffer = new ArrayBuffer(44 + dataLen);
  const view = new DataView(buffer);

  const writeStr = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i));
  };

  writeStr(0, 'RIFF');
  view.setUint32(4, 36 + dataLen, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);       // PCM
  view.setUint16(22, 1, true);       // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true);       // block align
  view.setUint16(34, 16, true);      // bits per sample
  writeStr(36, 'data');
  view.setUint32(40, dataLen, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }

  return buffer;
}

/**
 * Converts any audio Blob (WEBM/Opus from Chrome, MP4/AAC from Safari, etc.)
 * to mono 16 kHz WAV using the Web Audio API.
 *
 * Why: Google Cloud STT v1 returns empty results for Chrome's WEBM_OPUS.
 * LINEAR16 WAV at 16 kHz is the most reliably supported STT input format.
 * AudioContext constructed at 16 kHz resamples automatically in decodeAudioData.
 * decodeAudioData works even on a suspended AudioContext — no user gesture needed.
 */
export async function blobToMonoWav(blob: Blob): Promise<Blob> {
  const ctx = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
  try {
    const decoded = await ctx.decodeAudioData(await blob.arrayBuffer());

    const len = decoded.length;
    const mono = new Float32Array(len);
    for (let ch = 0; ch < decoded.numberOfChannels; ch++) {
      const chData = decoded.getChannelData(ch);
      for (let i = 0; i < len; i++) mono[i] += chData[i] / decoded.numberOfChannels;
    }

    return new Blob([encodeWav(mono, TARGET_SAMPLE_RATE)], { type: 'audio/wav' });
  } finally {
    await ctx.close();
  }
}
