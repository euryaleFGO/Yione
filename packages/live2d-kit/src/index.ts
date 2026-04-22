export interface AvatarConfig {
  modelUrl: string;
  scale?: number;
  anchor?: [number, number];
  motionMap?: Record<string, string>;
  autoBlink?: boolean;
  gazeMode?: 'mouse' | 'off';
}

// 具体实现（stage/lipsync/motion/blink/gaze）在 M2 写入。
export const PLACEHOLDER = 'live2d-kit-m0';
