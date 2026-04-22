/**
 * Cubism Core for Web is distributed by Live2D under a license that forbids
 * redistribution via npm. The SDK consumer drops `live2dcubismcore.min.js`
 * into their `public/` and references it from `index.html` (or dynamically
 * loads it at runtime).
 *
 * This helper checks for the global that the Cubism Core installs
 * (`window.Live2DCubismCore`). pixi-live2d-display reads the same global.
 */

declare global {
  interface Window {
    Live2DCubismCore?: unknown;
  }
}

export function isCubismCoreLoaded(): boolean {
  return typeof window !== 'undefined' && !!window.Live2DCubismCore;
}

export interface EnsureCubismOptions {
  /** URL to load if the global isn't present. Default `/live2dcubismcore.min.js`. */
  src?: string;
  /** Time budget in ms. Default 10000. */
  timeoutMs?: number;
}

/**
 * Dynamically inject a <script> tag for the Cubism core if it isn't yet loaded.
 * Returns true when the global is present, false otherwise (file missing, timeout, etc.).
 */
export async function ensureCubismCore(opts: EnsureCubismOptions = {}): Promise<boolean> {
  if (typeof window === 'undefined') return false;
  if (isCubismCoreLoaded()) return true;

  const src = opts.src ?? '/live2dcubismcore.min.js';
  const timeoutMs = opts.timeoutMs ?? 10_000;

  return new Promise<boolean>((resolve) => {
    const tag = document.createElement('script');
    tag.src = src;
    tag.async = true;
    let settled = false;
    const finish = (ok: boolean) => {
      if (settled) return;
      settled = true;
      resolve(ok && isCubismCoreLoaded());
    };
    tag.onload = () => finish(true);
    tag.onerror = () => finish(false);
    setTimeout(() => finish(false), timeoutMs);
    document.head.appendChild(tag);
  });
}
