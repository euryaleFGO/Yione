<script setup lang="ts">
import { onMounted, ref } from 'vue';

interface HistoryItem {
  session_id: string;
  character_id: string;
  created_at: string;
  message_count: number;
}

const items = ref<HistoryItem[]>([]);
const loading = ref(true);

onMounted(async () => {
  try {
    const res = await fetch('/api/sessions');
    if (res.ok) {
      const data = await res.json();
      items.value = data.sessions ?? [];
    }
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="max-w-3xl mx-auto px-6 py-10">
    <h1 class="text-2xl font-bold mb-6">对话历史</h1>

    <div v-if="loading" class="text-slate-500">加载中...</div>

    <div v-else-if="items.length === 0" class="text-slate-500">
      暂无对话记录
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="item in items"
        :key="item.session_id"
        class="p-4 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors"
      >
        <div class="flex items-center justify-between">
          <div>
            <div class="font-medium">{{ item.character_id }}</div>
            <div class="text-xs text-slate-500 mt-1">{{ item.session_id }}</div>
          </div>
          <div class="text-xs text-slate-400">
            {{ new Date(item.created_at).toLocaleString() }}
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
