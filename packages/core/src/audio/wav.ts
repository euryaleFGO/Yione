/**
 * 浏览器侧 16k PCM 录音 + WAV 编码工具。
 *
 * 为什么自己编 WAV 而不用 MediaRecorder：MediaRecorder 浏览器原生只出 webm/opus，
 * 后端 soundfile/libsndfile 不解 opus。声纹注册走 getUserMedia + AudioContext +
 * scriptProcessor 路线，和 M18 ASR 采集复用，自己拼 PCM → WAV header。
 */

/** 在 DataView 指定 offset 处写入 ASCII 字符串。 */
function writeAscii(view: DataView, offset: number, str: string): void {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

/**
 * 把 Int16 PCM samples 编成合法 WAV blob（mono，16-bit，指定采样率）。
 * libsndfile / Python soundfile 能直接 decode。
 */
export function encodePcmInt16ToWav(
  pcm: Int16Array,
  sampleRate = 16000,
): Blob {
  const numChannels = 1;
  const bitDepth = 16;
  const byteRate = (sampleRate * numChannels * bitDepth) / 8;
  const blockAlign = (numChannels * bitDepth) / 8;
  const dataSize = pcm.length * 2;

  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  // RIFF header
  writeAscii(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true);
  writeAscii(view, 8, 'WAVE');
  // fmt chunk
  writeAscii(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // subchunk1Size
  view.setUint16(20, 1, true); // audioFormat = PCM
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitDepth, true);
  // data chunk
  writeAscii(view, 36, 'data');
  view.setUint32(40, dataSize, true);

  // PCM payload（little-endian）
  for (let i = 0; i < pcm.length; i++) {
    view.setInt16(44 + i * 2, pcm[i] ?? 0, true);
  }

  return new Blob([buffer], { type: 'audio/wav' });
}

/** 把 Float32 [-1, 1] clamp + 转 Int16。 */
export function floatToPcmInt16(float: Float32Array): Int16Array {
  const out = new Int16Array(float.length);
  for (let i = 0; i < float.length; i++) {
    const s = Math.max(-1, Math.min(1, float[i] ?? 0));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

export interface RecordPcmOptions {
  /** 采样率；默认 16k，跟声纹/ASR 对齐 */
  sampleRate?: number;
  /** 最长录音秒数；超过自动停 */
  maxSeconds?: number;
}

export interface PcmRecorder {
  /** 停止录音，resolve 累积的 PCM Int16（16k mono）。可重复调，第二次是 no-op。 */
  stop: () => Promise<Int16Array>;
  /** 已累积的样本数（便于 UI 显示"已录 X 秒"） */
  getSampleCount: () => number;
}

/**
 * 启动一个 16k mono PCM 录音会话。需要上游先在用户 gesture 里调用（getUserMedia）。
 * 返回的 handle 提供 stop()，停止后 resolve 合并后的 Int16Array。
 */
export async function startPcmRecorder(
  opts: RecordPcmOptions = {},
): Promise<PcmRecorder> {
  const sampleRate = opts.sampleRate ?? 16000;
  const maxSeconds = opts.maxSeconds ?? 30;

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      sampleRate,
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });

  const audioContext = new AudioContext({ sampleRate });
  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);

  const chunks: Int16Array[] = [];
  let totalSamples = 0;
  let stopped = false;
  let stopTimer: ReturnType<typeof setTimeout> | null = null;

  processor.onaudioprocess = (e) => {
    if (stopped) return;
    const data = e.inputBuffer.getChannelData(0);
    const pcm = floatToPcmInt16(data);
    chunks.push(pcm);
    totalSamples += pcm.length;
    if (totalSamples >= maxSeconds * sampleRate) {
      void stop();
    }
  };

  source.connect(processor);
  processor.connect(audioContext.destination);

  // 兜底停止计时
  stopTimer = setTimeout(() => { void stop(); }, (maxSeconds + 1) * 1000);

  async function stop(): Promise<Int16Array> {
    if (stopped) {
      return concatInt16(chunks, totalSamples);
    }
    stopped = true;
    if (stopTimer) {
      clearTimeout(stopTimer);
      stopTimer = null;
    }
    try { processor.disconnect(); } catch { /* ignore */ }
    try { source.disconnect(); } catch { /* ignore */ }
    try { await audioContext.close(); } catch { /* ignore */ }
    stream.getTracks().forEach((t) => t.stop());
    return concatInt16(chunks, totalSamples);
  }

  return {
    stop,
    getSampleCount: () => totalSamples,
  };
}

function concatInt16(chunks: Int16Array[], total: number): Int16Array {
  const out = new Int16Array(total);
  let offset = 0;
  for (const c of chunks) {
    out.set(c, offset);
    offset += c.length;
  }
  return out;
}
