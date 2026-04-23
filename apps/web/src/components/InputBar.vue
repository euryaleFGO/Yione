<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue';

const props = defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{ send: [text: string] }>();

const text = ref('');
const composing = ref(false);
const recording = ref(false);

let recognition: any = null;

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

function toggleVoice() {
  if (recording.value) {
    stopVoice();
  } else {
    startVoice();
  }
}

function startVoice() {
  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert('当前浏览器不支持语音输入，请使用 Chrome 或 Edge');
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = 'zh-CN';
  recognition.continuous = false;
  recognition.interimResults = true;

  recognition.onresult = (event: any) => {
    let final = '';
    let interim = '';
    for (let i = 0; i < event.results.length; i++) {
      if (event.results[i].isFinal) {
        final += event.results[i][0].transcript;
      } else {
        interim += event.results[i][0].transcript;
      }
    }
    text.value = final || interim;
  };

  recognition.onend = () => {
    recording.value = false;
    // 如果有识别结果，自动发送
    if (text.value.trim()) {
      submit();
    }
  };

  recognition.onerror = () => {
    recording.value = false;
  };

  recognition.start();
  recording.value = true;
}

function stopVoice() {
  recognition?.stop();
  recording.value = false;
}

onBeforeUnmount(() => {
  recognition?.abort();
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
