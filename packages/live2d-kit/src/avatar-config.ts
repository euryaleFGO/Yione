export interface AvatarConfig {
  /** URL of the `.model3.json` (Cubism 4) file */
  modelUrl: string;
  /**
   * Fraction of host height the model should fill (0..1). Default 0.9.
   * Interpreted as a fill factor, not a raw PIXI scale — the stage auto-fits
   * to the container on every resize.
   */
  scale?: number;
  /**
   * Anchor-Y bias in [0..1], interpreted as vertical offset from host center
   * (0.5 = true center, 0.9 = head-high in the frame). Anchor-X is always 0.5
   * (centered horizontally).
   */
  anchor?: [number, number];
  /** Emotion → motion-group mapping (e.g. `{ joy: "Tap@Body" }`). */
  motionMap?: Record<string, string>;
  /** Auto-blink loop. */
  autoBlink?: boolean;
  /** Mouse-gaze tracking. `"off"` disables. */
  gazeMode?: 'mouse' | 'off';
  /** Background color as CSS string (transparent by default). */
  background?: string;
}

export const DEFAULT_AVATAR: AvatarConfig = {
  modelUrl: '/avatars/hiyori/hiyori_free_t08.model3.json',
  scale: 0.9,
  anchor: [0.5, 0.5],
  motionMap: {},
  autoBlink: true,
  gazeMode: 'mouse',
};
