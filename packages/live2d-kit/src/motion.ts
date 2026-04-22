/** Motion dispatcher — M5 wires emotion tags to motion groups. */

export type EmotionName = string; // keep open for future tags

export interface MotionController {
  play(emotion: EmotionName): Promise<void>;
}

export function createNoopMotion(): MotionController {
  return {
    play: async () => {},
  };
}
