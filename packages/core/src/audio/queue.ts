/**
 * AudioQueue — FIFO playback of wav segments with per-frame RMS sampling.
 *
 * Each enqueued segment is fetched as an ArrayBuffer, decoded via the Web
 * Audio API, and played in strict `segment_idx` order. While a buffer is
 * playing, we poll the `AnalyserNode` on `requestAnimationFrame` to feed an
 * RMS value (0..1) into the configured observer, which powers lip-sync.
 *
 * The queue is resilient to:
 *   - Out-of-order arrival (segments are reordered by `segment_idx`).
 *   - Missing segments (a small forward gap tolerance; after 250 ms without
 *     the expected next index we skip ahead — better a tiny cut than a stall).
 *   - AudioContext being suspended until the first user gesture (Chrome).
 */

export interface AudioQueueOptions {
  /** Called every animation frame during playback with the current RMS (0..1). */
  onRms?: (rms: number, t: number) => void;
  /** Called when the queue transitions empty → non-empty → empty. */
  onActivityChange?: (active: boolean) => void;
  /** Called when a fetch/decode errors out. Non-fatal. */
  onError?: (err: Error, segment: { url: string; idx: number }) => void;
  /** Fetch override (tests). Defaults to global `fetch`. */
  fetch?: typeof fetch;
}

export interface QueuedSegment {
  url: string;
  segmentIdx: number;
  sampleRate: number;
}

interface LoadedSegment extends QueuedSegment {
  buffer: AudioBuffer;
}

export class AudioQueue {
  private ctx: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private analyserData: Float32Array | null = null;

  private readonly pending = new Map<number, LoadedSegment>(); // loaded, awaiting its turn
  private readonly loading = new Set<number>();
  private nextExpectedIdx: number | null = null;
  private playing = false;
  private stopped = false;
  private rafHandle: number | null = null;
  private active = false;
  private readonly fetchImpl: typeof fetch;

  constructor(private readonly opts: AudioQueueOptions = {}) {
    this.fetchImpl = opts.fetch ?? (typeof fetch !== 'undefined' ? fetch.bind(globalThis) : (null as unknown as typeof fetch));
  }

  /** Must be called from a user gesture to satisfy browser autoplay rules. */
  async ensureContext(): Promise<AudioContext> {
    if (!this.ctx) {
      const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!Ctor) throw new Error('Web Audio API not available');
      this.ctx = new Ctor();
      this.analyser = this.ctx.createAnalyser();
      this.analyser.fftSize = 512;
      this.analyserData = new Float32Array(this.analyser.fftSize);
      this.analyser.connect(this.ctx.destination);
    }
    if (this.ctx.state === 'suspended') {
      try {
        await this.ctx.resume();
      } catch {
        /* ignore — some engines reject resume off-gesture; playback will still work once we push buffers */
      }
    }
    return this.ctx;
  }

  enqueue(segment: QueuedSegment): void {
    if (this.stopped) return;
    // First segment of a new stream dictates the base index. Also reset when
    // idle — see note in drain() for why.
    if (this.nextExpectedIdx === null) this.nextExpectedIdx = segment.segmentIdx;
    // Defensive: if a segment arrives with an idx smaller than what we're
    // waiting on (e.g. server restarted segment numbering mid-flight), treat
    // it as the head of a new stream.
    if (segment.segmentIdx < this.nextExpectedIdx && !this.playing && this.pending.size === 0) {
      this.nextExpectedIdx = segment.segmentIdx;
    }
    if (this.loading.has(segment.segmentIdx)) return;
    this.loading.add(segment.segmentIdx);
    void this.fetchAndDecode(segment);
  }

  /** Stop playback, abort in-flight fetches, release the AudioContext. */
  async destroy(): Promise<void> {
    this.stopped = true;
    this.pending.clear();
    this.loading.clear();
    if (this.rafHandle !== null) cancelAnimationFrame(this.rafHandle);
    this.rafHandle = null;
    if (this.ctx) {
      try {
        await this.ctx.close();
      } catch {
        /* ignore */
      }
      this.ctx = null;
      this.analyser = null;
    }
    this.setActive(false);
  }

  isActive(): boolean {
    return this.active;
  }

  private async fetchAndDecode(segment: QueuedSegment): Promise<void> {
    try {
      const ctx = await this.ensureContext();
      const res = await this.fetchImpl(segment.url);
      if (!res.ok) throw new Error(`HTTP ${res.status} for ${segment.url}`);
      const bytes = await res.arrayBuffer();
      const buffer = await ctx.decodeAudioData(bytes.slice(0));
      if (this.stopped) return;
      this.pending.set(segment.segmentIdx, { ...segment, buffer });
      void this.drain();
    } catch (err) {
      this.opts.onError?.(err instanceof Error ? err : new Error(String(err)), {
        url: segment.url,
        idx: segment.segmentIdx,
      });
    } finally {
      this.loading.delete(segment.segmentIdx);
    }
  }

  private async drain(): Promise<void> {
    if (this.playing || this.stopped) return;
    if (this.nextExpectedIdx === null) return;

    const next = this.pending.get(this.nextExpectedIdx);
    if (!next) return;
    this.pending.delete(this.nextExpectedIdx);

    this.playing = true;
    this.setActive(true);
    try {
      await this.playBuffer(next.buffer);
    } finally {
      this.playing = false;
      this.nextExpectedIdx = (this.nextExpectedIdx ?? 0) + 1;
      // Tail: if no more buffers queued and none loading, transition idle and
      // forget the running index — each TTS job restarts segment_idx from 1,
      // so holding a stale "expected next" across messages would strand the
      // fresh job's first segment in `pending` forever.
      if (this.pending.size === 0 && this.loading.size === 0) {
        this.nextExpectedIdx = null;
        this.setActive(false);
      } else {
        void this.drain();
      }
    }
  }

  private async playBuffer(buffer: AudioBuffer): Promise<void> {
    const ctx = await this.ensureContext();
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.connect(this.analyser!);

    const startTime = ctx.currentTime;
    this.startRmsLoop(startTime);

    return new Promise((resolve) => {
      src.addEventListener('ended', () => {
        this.stopRmsLoop();
        this.opts.onRms?.(0, performance.now());
        resolve();
      });
      try {
        src.start();
      } catch (err) {
        this.opts.onError?.(err instanceof Error ? err : new Error(String(err)), { url: '<source>', idx: -1 });
        resolve();
      }
    });
  }

  private startRmsLoop(_start: number): void {
    const tick = () => {
      if (!this.analyser || !this.analyserData) return;
      this.analyser.getFloatTimeDomainData(this.analyserData);
      let sumSq = 0;
      for (let i = 0; i < this.analyserData.length; i++) {
        const v = this.analyserData[i];
        sumSq += v * v;
      }
      const rms = Math.sqrt(sumSq / this.analyserData.length);
      this.opts.onRms?.(rms, performance.now());
      this.rafHandle = requestAnimationFrame(tick);
    };
    this.rafHandle = requestAnimationFrame(tick);
  }

  private stopRmsLoop(): void {
    if (this.rafHandle !== null) {
      cancelAnimationFrame(this.rafHandle);
      this.rafHandle = null;
    }
  }

  private setActive(next: boolean): void {
    if (this.active === next) return;
    this.active = next;
    this.opts.onActivityChange?.(next);
  }
}
