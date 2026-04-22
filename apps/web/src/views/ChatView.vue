<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { onBeforeUnmount, onMounted, ref } from 'vue';

import InputBar from '@/components/InputBar.vue';
import MessageList from '@/components/MessageList.vue';
import { useChatStore } from '@/stores/chat';

const chat = useChatStore();
const { messages, agentState, connection, lastError, session } = storeToRefs(chat);
const backendOk = ref<boolean | null>(null);
const backendVersion = ref('');

onMounted(async () => {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    backendOk.value = Boolean(data?.ok);
    backendVersion.value = data?.version ?? '';
  } catch {
    backendOk.value = false;
    return;
  }
  try {
    await chat.connectSocket();
  } catch {
    /* errors surfaced via lastError */
  }
});

onBeforeUnmount(() => chat.disconnect());

async function onSend(text: string) {
  await chat.submit(text, connection.value === 'open' ? 'ws' : 'rest');
}
</script>

<template>
  <section class="max-w-3xl mx-auto px-4 py-4 flex flex-col gap-3 h-[calc(100vh-60px)]">
    <div class="flex items-center gap-3 text-xs text-slate-500">
      <span>
        后端：
        <span v-if="backendOk === null">检查中…</span>
        <span v-else-if="backendOk" class="text-emerald-600">OK · v{{ backendVersion }}</span>
        <span v-else class="text-rose-600">未就绪（请启动 uvicorn）</span>
      </span>
      <span>·</span>
      <span>连接：{{ connection }}</span>
      <span>·</span>
      <span>状态：{{ agentState }}</span>
      <span v-if="session" class="text-slate-400">· {{ session.id }}</span>
      <span v-if="lastError" class="text-rose-600">· {{ lastError }}</span>
    </div>

    <div class="flex-1 min-h-0 border border-slate-200 rounded-lg overflow-hidden flex flex-col bg-white">
      <MessageList :messages="messages" class="flex-1 min-h-0" />
      <InputBar :disabled="connection === 'error'" @send="onSend" />
    </div>
  </section>
</template>
