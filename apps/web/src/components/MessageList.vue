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
</script>

<template>
  <div ref="root" class="h-full overflow-y-auto px-4 py-3 space-y-3 bg-slate-50">
    <div
      v-for="m in messages"
      :key="m.id"
      :class="[
        'flex',
        m.role === 'user' ? 'justify-end' : 'justify-start',
      ]"
    >
      <div
        :class="[
          'max-w-[70%] px-3 py-2 rounded-xl whitespace-pre-wrap leading-relaxed text-sm shadow-sm',
          m.role === 'user'
            ? 'bg-indigo-500 text-white rounded-br-sm'
            : 'bg-white text-slate-800 border border-slate-200 rounded-bl-sm',
        ]"
      >
        {{ m.text }}
      </div>
    </div>
  </div>
</template>
