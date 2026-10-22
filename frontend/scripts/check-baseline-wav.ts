import { strict as assert } from "node:assert";
import { blobToMonoWav } from "../lib/audio/blobToWav";

const originalContext = globalThis.AudioContext;
let closed = 0;
let rejectDecode = false;
const frames = 16000 * 30 + 1600;

class TestAudioContext {
  constructor(options: AudioContextOptions) {
    assert.equal(options.sampleRate, 16000);
  }
  async decodeAudioData() {
    if (rejectDecode) throw new Error("Unreadable audio");
    return {
      length: frames,
      numberOfChannels: 2,
      getChannelData: (channel: number) => new Float32Array(frames).fill(channel === 0 ? 0.75 : 0.25),
    };
  }
  async close() { closed += 1; }
}

async function check() {
  globalThis.AudioContext = TestAudioContext as unknown as typeof AudioContext;
  try {
    const capped = await blobToMonoWav(new Blob(["recording"]), 30);
    const view = new DataView(await capped.arrayBuffer());
    assert.equal(capped.type, "audio/wav");
    assert.equal(capped.size, 44 + 16000 * 30 * 2, "A late stop chunk must fit the server's strict 30-second limit");
    assert.equal(view.getUint32(4, true), capped.size - 8);
    assert.equal(view.getUint16(20, true), 1, "PCM encoding");
    assert.equal(view.getUint16(22, true), 1, "Stereo input must become mono");
    assert.equal(view.getUint32(24, true), 16000);
    assert.equal(view.getUint16(34, true), 16);
    assert.equal(view.getUint32(40, true), capped.size - 44);
    assert.equal(view.getInt16(44, true), 16383, "Mix both input channels instead of dropping one");
    const original = await blobToMonoWav(new Blob(["conversation"]));
    assert.equal(original.size, 44 + frames * 2, "Existing conversation callers retain their recording length");
    rejectDecode = true;
    await assert.rejects(() => blobToMonoWav(new Blob(["broken"]), 30), /Unreadable audio/);
    assert.equal(closed, 3, "Audio contexts close on success and failure");
  } finally {
    globalThis.AudioContext = originalContext;
  }
}

check().then(() => console.log("Baseline WAV checks passed: duration cap, PCM header, mono mixing, existing callers and cleanup."))
  .catch((error: unknown) => { console.error(error); process.exitCode = 1; });
