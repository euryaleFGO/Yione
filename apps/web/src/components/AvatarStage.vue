<script setup lang="ts">
import {
  AvatarStage as Live2DStage,
  DEFAULT_AVATAR,
  type AvatarConfig,
  type StageStatus,
} from '@webling/live2d-kit';
import { onBeforeUnmount, onMounted, ref } from 'vue';

const props = withDefaults(defineProps<{ config?: AvatarConfig }>(), {
  config: () => DEFAULT_AVATAR,
});

const hostEl = ref<HTMLDivElement | null>(null);
const status = ref<StageStatus>({ kind: 'idle' });
let stage: Live2DStage | null = null;

onMounted(async () => {
  if (!hostEl.value) return;
  stage = new Live2DStage({ onStatusChange: (s) => (status.value = s) });
  await stage.mount(hostEl.value, props.config);
});

onBeforeUnmount(() => stage?.unmount());

defineExpose({
  pushRms: (rms: number) => stage?.pushRms(rms),
  resetLipSync: () => stage?.resetLipSync(),
});
</script>

<template>
  <div class="relative w-full h-full bg-gradient-to-b from-sky-50 to-slate-100 overflow-hidden">
    <div ref="hostEl" class="absolute inset-0" />

    <div
      v-if="status.kind === 'loading'"
      class="absolute inset-0 flex items-center justify-center text-slate-400 text-sm"
    >
      加载 Live2D…
    </div>

    <div
      v-else-if="status.kind === 'cubism_missing'"
      class="absolute inset-0 flex flex-col items-center justify-center text-center px-6 text-sm text-slate-600 gap-2"
    >
      <div class="text-3xl">🎭</div>
      <div class="font-medium">缺少 Cubism Core</div>
      <p class="text-slate-500 max-w-xs leading-relaxed">
        请从
        <a
          href="https://www.live2d.com/download/cubism-sdk/"
          target="_blank"
          class="underline text-indigo-500"
        >
          Live2D 官网
        </a>
        下载 Cubism SDK for Web，把 <code class="bg-slate-100 px-1 rounded">Core/live2dcubismcore.min.js</code>
        放到 <code class="bg-slate-100 px-1 rounded">apps/web/public/</code>，刷新即可显示玲。
      </p>
    </div>

    <div
      v-else-if="status.kind === 'error'"
      class="absolute inset-0 flex flex-col items-center justify-center text-rose-600 text-sm px-6 gap-1"
    >
      <div>Live2D 初始化失败</div>
      <code class="text-xs text-rose-500">{{ status.message }}</code>
    </div>
  </div>
</template>
