/**
 * AvatarStage — PIXI application + Cubism 4 model wrapper.
 *
 * Designed to be *forgiving*: if Cubism Core isn't loaded, the stage stays in
 * a placeholder state (no crash, no PIXI leak) so the rest of the app keeps
 * working while the user installs the Core.
 *
 * PIXI + pixi-live2d-display are loaded dynamically to keep the host app's
 * initial bundle small; the cost is only paid once an avatar is actually
 * mounted.
 */

import { DEFAULT_AVATAR, type AvatarConfig } from './avatar-config.js';
import { ensureCubismCore, isCubismCoreLoaded } from './cubism-core.js';

type PixiModule = typeof import('pixi.js');
type Live2DBindings = typeof import('pixi-live2d-display-lipsyncpatch/cubism4');

declare global {
  interface Window {
    PIXI?: PixiModule;
  }
}

let bindingsPromise: Promise<{ PIXI: PixiModule; live2d: Live2DBindings }> | null = null;

async function loadBindings(): Promise<{ PIXI: PixiModule; live2d: Live2DBindings }> {
  if (bindingsPromise) return bindingsPromise;
  bindingsPromise = (async () => {
    const PIXI = await import('pixi.js');
    if (typeof window !== 'undefined') window.PIXI = window.PIXI ?? PIXI;
    const live2d = await import('pixi-live2d-display-lipsyncpatch/cubism4');
    const LiveCtor = live2d.Live2DModel as unknown as {
      registerTicker?: (ticker: unknown) => void;
    };
    LiveCtor.registerTicker?.(PIXI.Ticker);
    return { PIXI, live2d };
  })();
  return bindingsPromise;
}

export type StageStatus =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'ready' }
  | { kind: 'cubism_missing' }
  | { kind: 'error'; message: string };

export interface StageCallbacks {
  onStatusChange?: (status: StageStatus) => void;
}

export interface SpeakOptions {
  volume?: number;
  crossOrigin?: string;
}

type Live2DInstance = {
  width: number;
  height: number;
  position: { set(x: number, y: number): void };
  scale: { set(v: number): void; x: number; y: number };
  anchor?: { set(x: number, y: number): void };
  internalModel?: {
    width: number;
    height: number;
    originalWidth?: number;
    originalHeight?: number;
  };
  /** lipsyncpatch fork: speaks audio + drives mouth sync internally. */
  speak?: (
    sound: string,
    opts?: {
      volume?: number;
      crossOrigin?: string;
      resetExpression?: boolean;
      onFinish?: () => void;
      onError?: (e: Error) => void;
    },
  ) => Promise<boolean>;
  /** Stop current speak + lipsync. */
  stopSpeaking?: () => void;
};

export class AvatarStage {
  private appAny: unknown = null;
  private model: Live2DInstance | null = null;
  private resizeObserver: ResizeObserver | null = null;
  private host: HTMLElement | null = null;
  private config: AvatarConfig = DEFAULT_AVATAR;
  private status: StageStatus = { kind: 'idle' };

  constructor(private readonly cb: StageCallbacks = {}) {}

  async mount(host: HTMLElement, config: AvatarConfig = DEFAULT_AVATAR): Promise<StageStatus> {
    this.unmount();
    this.setStatus({ kind: 'loading' });

    const cubismReady = isCubismCoreLoaded() || (await ensureCubismCore());
    if (!cubismReady) {
      this.setStatus({ kind: 'cubism_missing' });
      return this.status;
    }

    try {
      const { PIXI, live2d } = await loadBindings();

      const app = new PIXI.Application({
        resizeTo: host,
        backgroundAlpha: 0,
        antialias: true,
        autoDensity: true,
        resolution: Math.min(window.devicePixelRatio || 1, 2),
      });
      const canvas = app.view as unknown as HTMLCanvasElement;
      canvas.style.display = 'block';
      canvas.style.width = '100%';
      canvas.style.height = '100%';
      host.appendChild(canvas);

      this.appAny = app;
      this.host = host;
      this.config = config;

      const model = (await live2d.Live2DModel.from(config.modelUrl)) as unknown as Live2DInstance;
      this.model = model;
      model.anchor?.set(0.5, 0.5);

      app.stage.addChild(model as unknown as Parameters<typeof app.stage.addChild>[0]);
      this.fitModel();

      // Re-fit on container resize. `resizeTo` on PIXI polls via ticker and
      // can race with user events; we reposition ourselves against CSS pixels
      // instead of renderer-buffer pixels to avoid DPR scaling surprises.
      this.resizeObserver = new ResizeObserver(() => this.fitModel());
      this.resizeObserver.observe(host);
      // One extra rAF settle — some browsers emit initial host dims of 0
      requestAnimationFrame(() => this.fitModel());

      this.setStatus({ kind: 'ready' });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.setStatus({ kind: 'error', message });
    }
    return this.status;
  }

  /**
   * Play a sound through the model and drive lipsync automatically.
   *
   * The lipsyncpatch fork handles the whole pipeline internally: it creates
   * an <audio> / AnalyserNode, connects output to speakers, and writes
   * ParamMouthOpenY each frame *after* motion updates so idle animations
   * don't overwrite the mouth shape. Returns a Promise that resolves when
   * playback finishes.
   */
  async speak(soundUrl: string, opts: SpeakOptions = {}): Promise<void> {
    const model = this.model;
    if (!model?.speak) return;
    await new Promise<void>((resolve) => {
      void model.speak!(soundUrl, {
        volume: opts.volume ?? 1,
        crossOrigin: opts.crossOrigin,
        resetExpression: false,
        onFinish: () => resolve(),
        onError: () => resolve(),
      });
    });
  }

  /** Abort any in-flight speak() and release its audio. */
  stopSpeaking(): void {
    this.model?.stopSpeaking?.();
  }

  unmount(): void {
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    this.model?.stopSpeaking?.();
    this.model = null;
    this.host = null;
    const app = this.appAny as { destroy?: (a?: boolean, b?: unknown) => void } | null;
    if (app?.destroy) {
      app.destroy(true, { children: true, texture: true, baseTexture: true });
    }
    this.appAny = null;
    this.setStatus({ kind: 'idle' });
  }

  getStatus(): StageStatus {
    return this.status;
  }

  /**
   * Fit the model to the host element (CSS pixels), centered with a bit of
   * vertical offset so the face sits comfortably high in the frame.
   */
  private fitModel(): void {
    const host = this.host;
    const model = this.model;
    if (!host || !model) return;

    const w = host.clientWidth;
    const h = host.clientHeight;
    if (w <= 0 || h <= 0) return;

    // The model's natural dimensions (before any scale applied). For Cubism 4
    // models the original canvas size is available on the internalModel; fall
    // back to a sensible default if not.
    const naturalH =
      model.internalModel?.originalHeight ??
      model.internalModel?.height ??
      model.height / (model.scale.y || 1) ??
      2000;

    const fillFactor = this.config.scale ?? 0.9; // fraction of host height to fill
    const desiredScale = (h * fillFactor) / naturalH;

    model.scale.set(desiredScale);

    // Center horizontally; anchor 0.5/0.5 means model center aligns with pos.
    const [, ay] = this.config.anchor ?? [0.5, 0.5];
    const biasY = (ay - 0.5) * model.height; // interpret legacy anchor Y as vertical bias
    model.position.set(w / 2, h / 2 + biasY);
  }

  private setStatus(next: StageStatus): void {
    this.status = next;
    this.cb.onStatusChange?.(next);
  }
}
