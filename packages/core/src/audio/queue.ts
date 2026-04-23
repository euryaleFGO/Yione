/**
 * AudioSpeakQueue — FIFO ordering of TTS segment URLs, dispatched to a
 * consumer one at a time. The actual playback + lipsync is done by whatever
 * implements ``SpeakFn`` (webLing wires this to Live2DModel.speak from the
 * ``pixi-live2d-display-lipsyncpatch`` fork, which handles audio output and
 * ParamMouthOpenY in lockstep — manual RMS→mouth drivers get overwritten by
 * idle motions on each frame, which is why our earlier approach failed).
 *
 * The queue reorders by ``segment_idx`` (CosyVoice can send them out of
 * order if the backend pipelines multiple synth jobs).
 */

export interface VisemeTimelineItem {
  char: string;
  t_start: number;
  t_end: number;
  viseme: string;
}

export type SpeakFn = (
  soundUrl: string,
  opts?: { timeline?: VisemeTimelineItem[] },
) => Promise<void> | void;

export interface AudioQueueOptions {
  /** Consumer that actually plays the audio and drives lipsync. */
  speak: SpeakFn;
  /** Called when the queue transitions empty→non-empty→empty. */
  onActivityChange?: (active: boolean) => void;
  /** Called on a consumer error (swallowed — queue continues). */
  onError?: (err: Error, segment: { url: string; idx: number }) => void;
}

export interface QueuedSegment {
  url: string;
  segmentIdx: number;
  sampleRate: number;
  /** M36 wav2vec2 forced alignment 产出的字符级嘴型时间轴（可选） */
  timeline?: VisemeTimelineItem[];
}

export class AudioQueue {
  private readonly pending = new Map<number, QueuedSegment>();
  private nextExpectedIdx: number | null = null;
  private playing = false;
  private stopped = false;
  private active = false;

  constructor(private readonly opts: AudioQueueOptions) {}

  /** No-op kept for API compat with the Web Audio version. */
  async ensureContext(): Promise<void> {
    /* Live2DModel.speak sets up its own AudioContext on first use. */
  }

  enqueue(segment: QueuedSegment): void {
    if (this.stopped) return;
    if (this.nextExpectedIdx === null) this.nextExpectedIdx = segment.segmentIdx;
    if (
      segment.segmentIdx < this.nextExpectedIdx &&
      !this.playing &&
      this.pending.size === 0
    ) {
      // New stream started before old one drained — resync.
      this.nextExpectedIdx = segment.segmentIdx;
    }
    if (this.pending.has(segment.segmentIdx)) return;
    this.pending.set(segment.segmentIdx, segment);
    void this.drain();
  }

  async destroy(): Promise<void> {
    this.stopped = true;
    this.pending.clear();
    this.nextExpectedIdx = null;
    this.setActive(false);
  }

  /**
   * 清掉还没播放的段（用于 M4 打断）。不改 stopped，调用方后续还能继续 enqueue
   * 新 turn 的段；下一个段到来时会重新设置 nextExpectedIdx。
   * 注意：正在播放中的那一段无法从这里停，需要上层调 stage.stopSpeaking()。
   */
  clear(): void {
    this.pending.clear();
    this.nextExpectedIdx = null;
    if (!this.playing) this.setActive(false);
  }

  isActive(): boolean {
    return this.active;
  }

  private async drain(): Promise<void> {
    if (this.playing || this.stopped) return;
    if (this.nextExpectedIdx === null) return;
    const next = this.pending.get(this.nextExpectedIdx);
    if (!next) return;
    this.pending.delete(this.nextExpectedIdx);

    const playedIdx = next.segmentIdx;
    this.playing = true;
    this.setActive(true);
    try {
      await this.opts.speak(next.url, { timeline: next.timeline });
    } catch (err) {
      this.opts.onError?.(err instanceof Error ? err : new Error(String(err)), {
        url: next.url,
        idx: playedIdx,
      });
    } finally {
      this.playing = false;
      // 打断场景：clear() 在 await 期间把 nextExpectedIdx 置 null，随后新 turn 的
      // enqueue() 又把它设成新 base。此时 `nextExpectedIdx !== playedIdx` —— 绝不
      // 能盲目 +1 覆盖新 base（那会让新段的 idx 永远拿不到）。只有"没被 clear 过"
      // 的情形（当前仍 == playedIdx）才推进到 playedIdx + 1。
      if (this.nextExpectedIdx === playedIdx) {
        this.nextExpectedIdx = playedIdx + 1;
      }
      if (this.pending.size === 0) {
        // 自然耗尽：重置 base 等下一个 turn；clear() 路径下 nextExpectedIdx 已是
        // null 或新 base，分别保留不动
        if (this.nextExpectedIdx === playedIdx + 1) {
          this.nextExpectedIdx = null;
        }
        this.setActive(false);
      } else {
        void this.drain();
      }
    }
  }

  private setActive(next: boolean): void {
    if (this.active === next) return;
    this.active = next;
    this.opts.onActivityChange?.(next);
  }
}
