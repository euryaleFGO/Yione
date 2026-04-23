<script setup lang="ts">
import { onMounted, ref } from 'vue';

interface Prompt {
  id: string;
  name: string;
  template: string;
  version: number;
  updated_at: string | null;
}

const prompts = ref<Prompt[]>([]);
const loading = ref(true);
const editing = ref<string | null>(null);
const editTemplate = ref('');

async function load() {
  loading.value = true;
  try {
    const res = await fetch('/api/prompts');
    if (res.ok) {
      const data = await res.json();
      prompts.value = data.prompts ?? [];
    }
  } finally {
    loading.value = false;
  }
}

function startEdit(p: Prompt) {
  editing.value = p.id;
  editTemplate.value = p.template;
}

async function save(id: string) {
  await fetch(`/api/prompts/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template: editTemplate.value }),
  });
  editing.value = null;
  await load();
}

onMounted(load);
</script>

<template>
  <section class="max-w-4xl mx-auto px-6 py-10">
    <h1 class="text-2xl font-bold mb-6">Prompt 管理</h1>

    <div v-if="loading" class="text-slate-500">加载中...</div>

    <div v-else-if="prompts.length === 0" class="text-slate-500">
      暂无 Prompt 模板
    </div>

    <div v-else class="space-y-4">
      <div
        v-for="p in prompts"
        :key="p.id"
        class="border border-slate-200 rounded-lg overflow-hidden"
      >
        <div class="px-4 py-3 bg-slate-50 flex items-center justify-between">
          <div>
            <span class="font-medium">{{ p.name }}</span>
            <span class="text-xs text-slate-400 ml-2">v{{ p.version }}</span>
          </div>
          <button
            type="button"
            class="text-xs text-indigo-600 hover:text-indigo-700"
            @click="editing === p.id ? editing = null : startEdit(p)"
          >
            {{ editing === p.id ? '取消' : '编辑' }}
          </button>
        </div>

        <div class="p-4">
          <pre v-if="editing !== p.id" class="text-sm text-slate-700 whitespace-pre-wrap font-mono">{{ p.template }}</pre>
          <div v-else>
            <textarea
              v-model="editTemplate"
              rows="8"
              class="w-full border border-slate-200 rounded p-3 text-sm font-mono"
            ></textarea>
            <button
              type="button"
              class="mt-2 px-4 py-1.5 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
              @click="save(p.id)"
            >
              保存 v{{ p.version + 1 }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
