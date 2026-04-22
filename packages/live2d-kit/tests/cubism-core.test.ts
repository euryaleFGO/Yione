import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ensureCubismCore, isCubismCoreLoaded } from '../src/cubism-core.js';

function setGlobal<T>(key: string, value: T): void {
  (globalThis as unknown as Record<string, unknown>)[key] = value;
}

describe('cubism-core', () => {
  let originalDocument: Document | undefined;

  beforeEach(() => {
    originalDocument = globalThis.document;
    setGlobal('window', {});
    // Minimal jsdom-free DOM stub: just the pieces ensureCubismCore uses.
    const head: { appendChild: (el: unknown) => unknown } = {
      appendChild: (el: unknown) => el,
    };
    setGlobal('document', { createElement: () => ({}), head });
  });

  afterEach(() => {
    if (originalDocument) setGlobal('document', originalDocument);
    else delete (globalThis as unknown as Record<string, unknown>).document;
    delete (globalThis as unknown as Record<string, unknown>).window;
    vi.restoreAllMocks();
  });

  it('returns true when Live2DCubismCore global is present', async () => {
    (globalThis as unknown as { window: Record<string, unknown> }).window.Live2DCubismCore = {};
    expect(isCubismCoreLoaded()).toBe(true);
    expect(await ensureCubismCore()).toBe(true);
  });

  it('falls back to false when the script load times out', async () => {
    // createElement returns a fake <script> whose onerror we manually fire.
    const tag: { src: string; onload?: () => void; onerror?: () => void; async?: boolean } = {
      src: '',
    };
    (globalThis as unknown as { document: { createElement: () => unknown; head: { appendChild: (el: unknown) => void } } }).document = {
      createElement: () => tag,
      head: {
        appendChild: () => {
          // Simulate loader failure on next tick
          queueMicrotask(() => tag.onerror?.());
        },
      },
    };
    const result = await ensureCubismCore({ timeoutMs: 500 });
    expect(result).toBe(false);
  });
});
