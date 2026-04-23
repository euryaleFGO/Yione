<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { useChatStore } from '@/stores/chat';

const chat = useChatStore();

interface Voice {
  id: string;
  name: string;
  provider: string;
}

const voices = ref<Voice[]>([]);
const selectedVoice = ref<string>('');
const provider = ref<string>('cosyvoice');
const loading = ref(false);

const PROVIDER_VOICES: Record<string, Voice[]> = {
  cosyvoice: [
    { id: 'default', name: '默认', provider: 'cosyvoice' },
  ],
  'edge-tts': [
    { id: 'zh-CN-XiaoyiNeural', name: '晓艺 (女声)', provider: 'edge-tts' },
    { id: 'zh-CN-YunxiNeural', name: '云希 (男声)', provider: 'edge-tts' },
    { id: 'zh-CN-XiaoxiaoNeural', name: '晓晓 (女声)', provider: 'edge-tts' },
    { id: 'zh-CN-YunjianNeural', name: '云健 (男声)', provider: 'edge-tts' },
  ],
};

function loadVoices() {
  voices.value = PROVIDER_VOICES[provider.value] ?? [];
  if (voices.value.length > 0 && !selectedVoice.value) {
    selectedVoice.value = voices.value[0].id;
  }
}

function switchProvider(p: string) {
  provider.value = p;
  selectedVoice.value = '';
  loadVoices();
}

async function save() {
  loading.value = true;
  try {
    // 保存到 localStorage（后端 API 可后续扩展）
    localStorage.setItem('tts_provider', provider.value);
    localStorage.setItem('tts_voice', selectedVoice.value);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  provider.value = localStorage.getItem('tts_provider') ?? 'cosyvoice';
  selectedVoice.value = localStorage.getItem('tts_voice') ?? '';
  loadVoices();
});
</script>

<template>
  <section class="max-w-3xl mx-auto px-6 py-10">
    <h1 class="text-2xl font-bold mb-6">音色管理</h1>

    <div class="space-y-6">
      <!-- Provider 选择 -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-2">TTS 引擎</label>
        <div class="flex gap-3">
          <button
            v-for="p in ['cosyvoice', 'edge-tts']"
            :key="p"
            type="button"
            class="px-4 py-2 rounded-lg border text-sm transition-colors"
            :class="{
              'border-indigo-500 bg-indigo-50 text-indigo-700': provider === p,
              'border-slate-200 hover:border-slate-300': provider !== p,
            }"
            @click="switchProvider(p)"
          >
            {{ p === 'cosyvoice' ? 'CosyVoice' : 'Edge TTS' }}
          </button>
        </div>
      </div>

      <!-- 音色列表 -->
      <div>
        <label class="block text-sm font-medium text-slate-700 mb-2">选择音色</label>
        <div class="grid grid-cols-2 gap-3">
          <button
            v-for="voice in voices"
            :key="voice.id"
            type="button"
            class="p-3 border rounded-lg text-left text-sm transition-colors"
            :class="{
              'border-indigo-500 bg-indigo-50': selectedVoice === voice.id,
              'border-slate-200 hover:border-slate-300': selectedVoice !== voice.id,
            }"
            @click="selectedVoice = voice.id"
          >
            <div class="font-medium">{{ voice.name }}</div>
            <div class="text-xs text-slate-500 mt-0.5">{{ voice.id }}</div>
          </button>
        </div>
      </div>

      <!-- 保存 -->
      <button
        type="button"
        class="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        :disabled="loading"
        @click="save"
      >
        {{ loading ? '保存中...' : '保存' }}
      </button>
    </div>
  </section>
</template>
