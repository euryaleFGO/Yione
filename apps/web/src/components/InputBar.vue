<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{ send: [text: string] }>();

const text = ref('');
const composing = ref(false);

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
      type="submit"
      :disabled="disabled || !text.trim()"
      class="px-4 py-2 rounded-md bg-indigo-500 text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
    >
      发送
    </button>
  </form>
</template>
