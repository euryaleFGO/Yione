/**
 * RMS → ParamMouthOpenY driver. M3 wires this to the TTS audio queue.
 * M2 ships a stub type so callers can reference the API early.
 */

export interface LipSyncDriver {
  /** Feed an RMS sample in `[0..1]`. */
  pushRms(rms: number): void;
  /** Stop driving; idempotent. */
  stop(): void;
}

export function createNoopLipSync(): LipSyncDriver {
  return {
    pushRms: () => {},
    stop: () => {},
  };
}
