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
  // Single-shot so Live2DModel.registerTicker isn't called twice across mounts.
  if (bindingsPromise) return bindingsPromise;

  bindingsPromise = (async () => {
    const PIXI = await import('pixi.js');
    // pixi-live2d-display reads `window.PIXI` at import-evaluation time to
    // pick up Ticker/DisplayObject — must be set BEFORE the live2d import.
    if (typeof window !== 'undefined') window.PIXI = window.PIXI ?? PIXI;
    const live2d = await import('pixi-live2d-display-lipsyncpatch/cubism4');
    // Motion updates are driven by PIXI.Ticker. If this isn't registered, the
    // model's internal drawable arrays never initialize and the first render
    // crashes in CubismRenderer.doDrawModel (see PLAN §14 "关键风险").
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

type AnyDisplayObject = { width: number; height: number; position: { set(x: number, y: number): void }; scale: { set(v: number): void } };

export class AvatarStage {
  private appAny: unknown = null;
  private model: AnyDisplayObject | null = null;
  private resizeObserver: ResizeObserver | null = null;
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
      host.appendChild(app.view as unknown as HTMLCanvasElement);
      this.appAny = app;

      const model = (await live2d.Live2DModel.from(config.modelUrl)) as unknown as AnyDisplayObject & {
        anchor?: { set: (x: number, y: number) => void };
      };
      this.model = model;

      const [ax, ay] = config.anchor ?? [0.5, 0.9];
      model.anchor?.set(ax, ay);
      model.scale.set(config.scale ?? (DEFAULT_AVATAR.scale as number));
      this.centerModel();

      app.stage.addChild(model as unknown as Parameters<typeof app.stage.addChild>[0]);

      this.resizeObserver = new ResizeObserver(() => this.centerModel());
      this.resizeObserver.observe(host);

      this.setStatus({ kind: 'ready' });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.setStatus({ kind: 'error', message });
    }
    return this.status;
  }

  unmount(): void {
    this.resizeObserver?.disconnect();
    this.resizeObserver = null;
    this.model = null;
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

  private centerModel(): void {
    const app = this.appAny as { renderer?: { width: number; height: number } } | null;
    if (!this.model || !app?.renderer) return;
    this.model.position.set(app.renderer.width / 2, app.renderer.height);
  }

  private setStatus(next: StageStatus): void {
    this.status = next;
    this.cb.onStatusChange?.(next);
  }
}
