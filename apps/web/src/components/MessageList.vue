<script setup lang="ts">
import type { Message } from '@webling/core';
import { nextTick, ref, watch } from 'vue';

const props = defineProps<{ messages: Message[] }>();
const root = ref<HTMLDivElement | null>(null);

watch(
  () => props.messages.length,
  async () => {
    await nextTick();
    if (root.value) root.value.scrollTop = root.value.scrollHeight;
  },
);

// 情绪 → assistant 气泡的 tailwind 配色；neutral 走默认白底。
// 只调底色/边框，不动文字颜色，保证可读。
const EMOTION_CLASSES: Record<string, string> = {
  joy: 'bg-amber-50 border-amber-300',
  affection: 'bg-pink-50 border-pink-300',
  sadness: 'bg-sky-50 border-sky-300',
  anger: 'bg-rose-50 border-rose-300',
  fear: 'bg-violet-50 border-violet-300',
  surprise: 'bg-emerald-50 border-emerald-300',
  disgust: 'bg-lime-50 border-lime-300',
};

function assistantBubbleClass(m: Message): string {
  if (!m.emotion || m.emotion === 'neutral') return 'bg-white border-slate-200';
  return EMOTION_CLASSES[m.emotion] ?? 'bg-white border-slate-200';
}
</script>

<template>
  <div ref="root" class="h-full overflow-y-auto px-4 py-3 space-y-3 bg-slate-50">
    <div
      v-for="m in messages"
      :key="m.id"
      :class="[
        'flex flex-col',
        m.role === 'user' ? 'items-end' : 'items-start',
      ]"
    >
      <div
        v-if="m.role === 'user' && m.speaker"
        class="text-[10px] text-slate-500 mb-0.5 pr-1"
      >
        {{ m.speaker.name ?? m.speaker.id }}
      </div>
      <div
        :class="[
          'max-w-[70%] px-3 py-2 rounded-xl whitespace-pre-wrap leading-relaxed text-sm shadow-sm',
          m.role === 'user'
            ? 'bg-indigo-500 text-white rounded-br-sm'
            : ['text-slate-800 border rounded-bl-sm', assistantBubbleClass(m)],
        ]"
      >
        {{ m.text }}
      </div>
    </div>
  </div>
</template>
