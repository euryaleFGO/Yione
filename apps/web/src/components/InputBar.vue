<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue';

const props = defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{ send: [text: string] }>();

const text = ref('');
const composing = ref(false);
const recording = ref(false);
const asrText = ref('');

let mediaRecorder: MediaRecorder | null = null;
let asrWs: WebSocket | null = null;
let speechRecognition: any = null;

function submit() {
  const trimmed = text.value.trim();
  if (!trimmed || props.disabled) return;
  emit('send', trimmed);
  text.value = '';
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey && !composing.value) {
    e.preventDefault();
    submit();
  }
}

async function toggleVoice() {
  if (recording.value) {
    stopVoice();
  } else {
    await startVoice();
  }
}

async function startVoice() {
  // 优先尝试 FunASR（需要 HTTPS 或 localhost）
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    await startFunASR(stream);
    return;
  } catch {
    // 降级到 Web Speech API
  }

  // Web Speech API 降级
  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert('语音输入需要：\n1. 使用 localhost 访问（推荐）\n2. 或使用 Chrome/Edge 浏览器');
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = 'zh-CN';
  recognition.continuous = false;
  recognition.interimResults = true;

  recognition.onresult = (event: any) => {
    let final = '';
    for (let i = 0; i < event.results.length; i++) {
      if (event.results[i].isFinal) {
        final += event.results[i][0].transcript;
      } else {
        text.value = event.results[i][0].transcript;
      }
    }
    if (final) text.value = final;
  };

  recognition.onend = () => {
    recording.value = false;
    if (text.value.trim()) submit();
  };

  recognition.onerror = () => {
    recording.value = false;
  };

  recognition.start();
  speechRecognition = recognition;
  recording.value = true;
}

async function startFunASR(stream: MediaStream) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  asrWs = new WebSocket(`${proto}://${location.host}/ws/asr`);

  asrWs.onopen = () => {
    asrWs!.send(JSON.stringify({ sample_rate: 16000 }));
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0 && asrWs?.readyState === WebSocket.OPEN) {
        e.data.arrayBuffer().then((buf) => asrWs!.send(buf));
      }
    };
    mediaRecorder.start(250);
    recording.value = true;
    asrText.value = '';
  };

  asrWs.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    if (data.type === 'asr_result') {
      if (data.text) { asrText.value = data.text; text.value = data.text; }
      if (data.is_final) { stopVoice(); if (text.value.trim()) submit(); }
    } else if (data.type === 'asr_error') {
      stopVoice();
    }
  };

  asrWs.onerror = () => stopVoice();
  asrWs.onclose = () => { if (recording.value) stopVoice(); };
}

function stopVoice() {
  recording.value = false;

  if (mediaRecorder?.state === 'recording') {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach((t) => t.stop());
  }
  mediaRecorder = null;

  if (asrWs?.readyState === WebSocket.OPEN) {
    asrWs.close();
  }
  asrWs = null;

  if (speechRecognition) {
    speechRecognition.abort();
    speechRecognition = null;
  }
}

onBeforeUnmount(() => {
  stopVoice();
});
</script>

<template>
  <form
    class="border-t border-slate-200 bg-white px-3 py-2 flex gap-2 items-end"
    @submit.prevent="submit"
  >
    <textarea
      v-model="text"
      :disabled="disabled"
      rows="2"
      class="flex-1 resize-none rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:bg-slate-100"
      placeholder="和玲说点什么，Enter 发送，Shift+Enter 换行"
      @keydown="onKeydown"
      @compositionstart="composing = true"
      @compositionend="composing = false"
    />
    <button
      type="button"
      :class="[
        'px-3 py-2 rounded-md text-sm transition-colors',
        recording
          ? 'bg-red-500 text-white animate-pulse'
          : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
      ]"
      :title="recording ? '停止录音' : '语音输入'"
      @click="toggleVoice"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
        <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
      </svg>
    </button>
    <button
      type="submit"
      :disabled="disabled || !text.trim()"
      class="px-4 py-2 rounded-md bg-indigo-500 text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
    >
      发送
    </button>
  </form>
</template>
