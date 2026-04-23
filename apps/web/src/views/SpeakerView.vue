<script setup lang="ts">
import { encodePcmInt16ToWav, startPcmRecorder, type PcmRecorder } from '@webling/core';
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

interface Speaker {
  id: string;
  name: string | null;
  enrolled_samples: number;
  created_at: string;
  updated_at: string;
  profile?: unknown;
}

const speakers = ref<Speaker[]>([]);
const loading = ref(true);
const banner = ref<{ kind: 'info' | 'error'; text: string } | null>(null);

// 注册表单：录音状态
const recording = ref(false);
const recordedWav = ref<Blob | null>(null);
const recordedDurationSec = ref(0);
const newName = ref('');
const registering = ref(false);

// 识别测试（临时验证用）
const identifying = ref(false);
const identifyResult = ref<{
  matched: boolean;
  name: string | null;
  score: number;
  threshold: number;
  engineAvailable: boolean;
} | null>(null);

let recorder: PcmRecorder | null = null;
let durationTimer: ReturnType<typeof setInterval> | null = null;

const hasRecorded = computed(() => recordedWav.value !== null);

async function load() {
  loading.value = true;
  try {
    const res = await fetch('/api/speakers');
    if (!res.ok) {
      banner.value = { kind: 'error', text: `加载失败：HTTP ${res.status}` };
      speakers.value = [];
      return;
    }
    const data = await res.json();
    // 后端返回 list[SpeakerInfo] 裸数组，不是 {speakers: [...]} 包装
    speakers.value = Array.isArray(data) ? data : (data.speakers ?? []);
    banner.value = null;
  } catch (err) {
    banner.value = {
      kind: 'error',
      text: `加载失败：${err instanceof Error ? err.message : String(err)}`,
    };
    speakers.value = [];
  } finally {
    loading.value = false;
  }
}

async function startRecording() {
  if (recording.value) return;
  banner.value = null;
  recordedWav.value = null;
  recordedDurationSec.value = 0;
  try {
    recorder = await startPcmRecorder({ sampleRate: 16000, maxSeconds: 20 });
    recording.value = true;
    durationTimer = setInterval(() => {
      if (recorder) recordedDurationSec.value = Math.floor(recorder.getSampleCount() / 16000);
    }, 250);
  } catch (err) {
    banner.value = {
      kind: 'error',
      text: `无法访问麦克风：${err instanceof Error ? err.message : String(err)}`,
    };
    recording.value = false;
  }
}

async function stopRecording() {
  if (!recorder || !recording.value) return;
  recording.value = false;
  if (durationTimer) {
    clearInterval(durationTimer);
    durationTimer = null;
  }
  const pcm = await recorder.stop();
  recorder = null;
  recordedDurationSec.value = Math.floor(pcm.length / 16000);
  if (pcm.length < 16000 * 2) {
    banner.value = { kind: 'error', text: '录音太短（<2s），建议至少 5 秒' };
    return;
  }
  recordedWav.value = encodePcmInt16ToWav(pcm, 16000);
}

function discardRecording() {
  recordedWav.value = null;
  recordedDurationSec.value = 0;
}

async function registerSpeaker() {
  if (!recordedWav.value) return;
  registering.value = true;
  banner.value = null;
  try {
    const form = new FormData();
    form.append('audio', recordedWav.value, 'sample.wav');
    if (newName.value.trim()) form.append('name', newName.value.trim());
    const res = await fetch('/api/speakers/register', { method: 'POST', body: form });
    if (!res.ok) {
      const body = await res.text();
      banner.value = { kind: 'error', text: `注册失败（${res.status}）：${body.slice(0, 200)}` };
      return;
    }
    const data = await res.json();
    banner.value = {
      kind: 'info',
      text: `注册成功 ${data.speaker?.id ?? ''}（向量维度 ${data.embedding_dim}）`,
    };
    newName.value = '';
    recordedWav.value = null;
    recordedDurationSec.value = 0;
    await load();
  } catch (err) {
    banner.value = {
      kind: 'error',
      text: `注册失败：${err instanceof Error ? err.message : String(err)}`,
    };
  } finally {
    registering.value = false;
  }
}

async function identifyCurrent() {
  if (!recordedWav.value) return;
  identifying.value = true;
  identifyResult.value = null;
  try {
    const form = new FormData();
    form.append('audio', recordedWav.value, 'probe.wav');
    const res = await fetch('/api/speakers/identify', { method: 'POST', body: form });
    if (!res.ok) {
      const body = await res.text();
      banner.value = { kind: 'error', text: `识别失败（${res.status}）：${body.slice(0, 200)}` };
      return;
    }
    const data = await res.json();
    identifyResult.value = {
      matched: data.matched,
      name: data.speaker?.name ?? data.speaker?.id ?? null,
      score: data.score,
      threshold: data.threshold,
      engineAvailable: data.engine_available,
    };
  } catch (err) {
    banner.value = {
      kind: 'error',
      text: `识别失败：${err instanceof Error ? err.message : String(err)}`,
    };
  } finally {
    identifying.value = false;
  }
}

async function updateName(id: string, name: string) {
  await fetch(`/api/speakers/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: name.trim() || null }),
  });
  await load();
}

async function deleteSpeaker(id: string) {
  if (!confirm('确定删除？声纹向量将被清掉，无法恢复。')) return;
  await fetch(`/api/speakers/${id}`, { method: 'DELETE' });
  await load();
}

onMounted(load);

onBeforeUnmount(() => {
  if (durationTimer) clearInterval(durationTimer);
  if (recorder) void recorder.stop();
});
</script>

<template>
  <section class="max-w-3xl mx-auto px-6 py-10 space-y-8">
    <header>
      <h1 class="text-2xl font-bold">说话人管理</h1>
      <p class="mt-1 text-sm text-slate-500">
        录一段 5-15 秒清晰语音，系统会提取 192 维声纹向量；识别时余弦相似度 ≥ 0.38 视为命中。
      </p>
    </header>

    <div
      v-if="banner"
      class="rounded-md px-3 py-2 text-sm"
      :class="banner.kind === 'error' ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'"
    >
      {{ banner.text }}
    </div>

    <!-- 注册面板 -->
    <section class="border border-slate-200 rounded-lg p-4 space-y-3 bg-white">
      <h2 class="font-medium">注册 / 采集声纹</h2>

      <div class="flex items-center gap-3">
        <button
          v-if="!recording"
          type="button"
          class="px-4 py-2 rounded-md bg-indigo-500 text-white text-sm hover:bg-indigo-600"
          :disabled="registering"
          @click="startRecording"
        >
          🎙 开始录音
        </button>
        <button
          v-else
          type="button"
          class="px-4 py-2 rounded-md bg-rose-500 text-white text-sm hover:bg-rose-600 animate-pulse"
          @click="stopRecording"
        >
          ■ 停止（{{ recordedDurationSec }}s）
        </button>

        <span v-if="hasRecorded" class="text-sm text-slate-600">
          已录 {{ recordedDurationSec }}s
        </span>
        <button
          v-if="hasRecorded"
          type="button"
          class="text-xs text-slate-500 hover:text-slate-700"
          @click="discardRecording"
        >
          丢弃重录
        </button>
      </div>

      <div v-if="hasRecorded" class="flex items-center gap-2 pt-2 border-t border-slate-100">
        <input
          v-model="newName"
          placeholder="昵称（可空）"
          class="flex-1 border border-slate-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring focus:ring-indigo-200"
          :disabled="registering"
        >
        <button
          type="button"
          class="px-3 py-1.5 rounded-md bg-indigo-500 text-white text-sm hover:bg-indigo-600 disabled:bg-slate-300"
          :disabled="registering || identifying"
          @click="registerSpeaker"
        >
          {{ registering ? '注册中…' : '注册新说话人' }}
        </button>
        <button
          type="button"
          class="px-3 py-1.5 rounded-md border border-slate-300 text-slate-700 text-sm hover:bg-slate-50 disabled:text-slate-400"
          :disabled="registering || identifying"
          @click="identifyCurrent"
        >
          {{ identifying ? '识别中…' : '识别（不注册）' }}
        </button>
      </div>

      <div
        v-if="identifyResult"
        class="text-xs bg-slate-50 border border-slate-200 rounded px-3 py-2 space-y-0.5"
      >
        <div v-if="!identifyResult.engineAvailable" class="text-rose-600">
          ⚠️ 声纹引擎不可用（check [sv] 依赖和 Ling 仓库路径）
        </div>
        <div v-else>
          <span v-if="identifyResult.matched" class="text-emerald-700">
            ✓ 命中：{{ identifyResult.name ?? '(未命名)' }}
          </span>
          <span v-else class="text-slate-600">未命中现有说话人</span>
          <span class="text-slate-500 ml-2">
            score={{ identifyResult.score.toFixed(3) }} / threshold={{ identifyResult.threshold.toFixed(2) }}
          </span>
        </div>
      </div>
    </section>

    <!-- 已注册列表 -->
    <section class="space-y-3">
      <h2 class="font-medium">已注册（{{ speakers.length }}）</h2>
      <div v-if="loading" class="text-slate-500 text-sm">加载中...</div>
      <div v-else-if="speakers.length === 0" class="text-slate-500 text-sm">
        还没有注册说话人。用上面的录音按钮录一段语音开始。
      </div>
      <div v-else class="space-y-2">
        <div
          v-for="spk in speakers"
          :key="spk.id"
          class="p-4 border border-slate-200 rounded-lg flex items-center justify-between bg-white"
        >
          <div class="min-w-0">
            <input
              :value="spk.name ?? ''"
              placeholder="未命名"
              class="font-medium bg-transparent border-b border-transparent hover:border-slate-300 focus:border-indigo-500 outline-none"
              @blur="(e) => updateName(spk.id, (e.target as HTMLInputElement).value)"
            >
            <div class="text-xs text-slate-500 mt-1 truncate">
              {{ spk.id }} · {{ spk.enrolled_samples }} 样本 · 注册 {{ new Date(spk.created_at).toLocaleString() }}
            </div>
          </div>
          <button
            type="button"
            class="shrink-0 text-xs text-rose-600 hover:text-rose-700 ml-3"
            @click="deleteSpeaker(spk.id)"
          >
            删除
          </button>
        </div>
      </div>
    </section>
  </section>
</template>
