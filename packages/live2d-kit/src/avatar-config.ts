export interface AvatarConfig {
  /** URL of the `.model3.json` (Cubism 4) file */
  modelUrl: string;
  /** Display scale (1 = fit). */
  scale?: number;
  /** Anchor point in [0..1, 0..1]. */
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
  scale: 0.22,
  anchor: [0.5, 0.9],
  motionMap: {},
  autoBlink: true,
  gazeMode: 'mouse',
};
