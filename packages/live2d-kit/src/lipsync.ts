/**
 * RMS → ``ParamMouthOpenY`` / ``ParamMouthForm`` driver.
 *
 * Cubism 4 models expose a mouth-open parameter in [0..1]. RMS from the audio
 * queue is roughly in [0..0.4], so we apply a gentle compression curve + EMA
 * smoothing so the mouth shape tracks speech without twitching between
 * silence frames.
 */

export interface LipSyncDriver {
  /** Feed an RMS sample (0..1) from the audio analyser. */
  pushRms(rms: number): void;
  /** Force mouth closed (e.g. when audio ends). */
  reset(): void;
  /** Detach from the model. Idempotent. */
  dispose(): void;
}

interface LipSyncTargetParams {
  addParameterValueById?(id: string, value: number, weight?: number): void;
  setParameterValueById?(id: string, value: number): void;
  getParameterMaximumValue?(id: string): number;
}

interface LipSyncTarget {
  /** Cubism 4: `model.internalModel.coreModel` exposes these setters. */
  internalModel?: { coreModel?: LipSyncTargetParams };
  /** Fallback: some wrappers expose the params on the root object. */
  setParameterValueById?: (id: string, value: number) => void;
  addParameterValueById?: (id: string, value: number, weight?: number) => void;
}

export interface LipSyncOptions {
  /** Smoothing factor for the EMA (0..1). Larger = more responsive. Default 0.35. */
  smoothing?: number;
  /** Multiplier applied before clamping. Default 2.2 for CosyVoice output. */
  gain?: number;
  /** Cubism parameter id. Default "ParamMouthOpenY". */
  paramId?: string;
}

export function createLipSync(model: LipSyncTarget, options: LipSyncOptions = {}): LipSyncDriver {
  const smoothing = clamp01(options.smoothing ?? 0.35);
  const gain = options.gain ?? 2.2;
  const paramId = options.paramId ?? 'ParamMouthOpenY';
  let level = 0;
  let disposed = false;

  const writer = pickWriter(model, paramId);

  return {
    pushRms(rms: number): void {
      if (disposed) return;
      const target = clamp01(rms * gain);
      level = level + smoothing * (target - level);
      writer(level);
    },
    reset(): void {
      if (disposed) return;
      level = 0;
      writer(0);
    },
    dispose(): void {
      disposed = true;
    },
  };
}

export function createNoopLipSync(): LipSyncDriver {
  return {
    pushRms: () => {},
    reset: () => {},
    dispose: () => {},
  };
}

function clamp01(v: number): number {
  if (v < 0) return 0;
  if (v > 1) return 1;
  return v;
}

function pickWriter(model: LipSyncTarget, paramId: string): (value: number) => void {
  const core = model.internalModel?.coreModel;
  if (core?.setParameterValueById) {
    return (v) => core.setParameterValueById!(paramId, v);
  }
  if (core?.addParameterValueById) {
    // The add-style setter accumulates; we reset to the target each frame
    // by using weight=1 which overwrites the existing delta.
    return (v) => core.addParameterValueById!(paramId, v, 1);
  }
  if (model.setParameterValueById) {
    return (v) => model.setParameterValueById!(paramId, v);
  }
  if (model.addParameterValueById) {
    return (v) => model.addParameterValueById!(paramId, v, 1);
  }
  // No-op fallback keeps the rest of the pipeline running even if the
  // runtime doesn't expose parameter writers (older fork / mock).
  return () => {};
}
