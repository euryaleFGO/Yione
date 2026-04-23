<script setup lang="ts">
import { onMounted, ref } from 'vue';

interface Speaker {
  id: string;
  name: string | null;
  enrolled_samples: number;
  created_at: string;
}

const speakers = ref<Speaker[]>([]);
const loading = ref(true);

async function load() {
  loading.value = true;
  try {
    const res = await fetch('/api/speakers');
    if (res.ok) {
      const data = await res.json();
      speakers.value = data.speakers ?? [];
    }
  } finally {
    loading.value = false;
  }
}

async function updateName(id: string, name: string) {
  await fetch(`/api/speakers/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  await load();
}

async function deleteSpeaker(id: string) {
  if (!confirm('确定删除？')) return;
  await fetch(`/api/speakers/${id}`, { method: 'DELETE' });
  await load();
}

onMounted(load);
</script>

<template>
  <section class="max-w-3xl mx-auto px-6 py-10">
    <h1 class="text-2xl font-bold mb-6">说话人管理</h1>

    <div v-if="loading" class="text-slate-500">加载中...</div>

    <div v-else-if="speakers.length === 0" class="text-slate-500">
      暂无已注册说话人
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="spk in speakers"
        :key="spk.id"
        class="p-4 border border-slate-200 rounded-lg flex items-center justify-between"
      >
        <div>
          <input
            :value="spk.name ?? ''"
            placeholder="未命名"
            class="font-medium bg-transparent border-b border-transparent hover:border-slate-300 focus:border-indigo-500 outline-none"
            @blur="(e) => updateName(spk.id, (e.target as HTMLInputElement).value)"
          >
          <div class="text-xs text-slate-500 mt-1">
            {{ spk.id }} · {{ spk.enrolled_samples }} 样本
          </div>
        </div>
        <button
          type="button"
          class="text-xs text-rose-600 hover:text-rose-700"
          @click="deleteSpeaker(spk.id)"
        >
          删除
        </button>
      </div>
    </div>
  </section>
</template>
