<script setup lang="ts">
import { onMounted, ref } from 'vue';

interface KGNode {
  id: string;
  label: string;
  type: string;
  x?: number;
  y?: number;
}

interface KGEdge {
  source: string;
  target: string;
  label: string;
}

const nodes = ref<KGNode[]>([]);
const edges = ref<KGEdge[]>([]);
const loading = ref(true);

const COLORS: Record<string, string> = {
  character: '#6366f1',
  technology: '#10b981',
  provider: '#f59e0b',
  database: '#ef4444',
  framework: '#8b5cf6',
};

onMounted(async () => {
  try {
    const res = await fetch('/api/knowledge-graph');
    if (res.ok) {
      const data = await res.json();
      nodes.value = data.nodes ?? [];
      edges.value = data.edges ?? [];
      layoutNodes();
    }
  } finally {
    loading.value = false;
  }
});

function layoutNodes() {
  const cx = 400, cy = 250, r = 180;
  nodes.value.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / nodes.value.length - Math.PI / 2;
    n.x = cx + r * Math.cos(angle);
    n.y = cy + r * Math.sin(angle);
  });
}

function getNode(id: string) {
  return nodes.value.find(n => n.id === id);
}
</script>

<template>
  <section class="max-w-4xl mx-auto px-6 py-10">
    <h1 class="text-2xl font-bold mb-6">知识图谱</h1>

    <div v-if="loading" class="text-slate-500">加载中...</div>

    <div v-else class="border border-slate-200 rounded-lg overflow-hidden bg-white">
      <svg viewBox="0 0 800 500" class="w-full">
        <!-- 边 -->
        <g v-for="(edge, i) in edges" :key="'e'+i">
          <line
            v-if="getNode(edge.source) && getNode(edge.target)"
            :x1="getNode(edge.source)!.x"
            :y1="getNode(edge.source)!.y"
            :x2="getNode(edge.target)!.x"
            :y2="getNode(edge.target)!.y"
            stroke="#cbd5e1"
            stroke-width="1.5"
          />
          <text
            v-if="getNode(edge.source) && getNode(edge.target)"
            :x="(getNode(edge.source)!.x! + getNode(edge.target)!.x!) / 2"
            :y="(getNode(edge.source)!.y! + getNode(edge.target)!.y!) / 2 - 6"
            text-anchor="middle"
            class="text-[10px] fill-slate-400"
          >{{ edge.label }}</text>
        </g>

        <!-- 节点 -->
        <g v-for="node in nodes" :key="node.id">
          <circle
            :cx="node.x"
            :cy="node.y"
            r="28"
            :fill="COLORS[node.type] ?? '#94a3b8'"
            class="cursor-pointer hover:opacity-80"
          />
          <text
            :x="node.x"
            :y="node.y! + 4"
            text-anchor="middle"
            class="text-xs fill-white font-medium pointer-events-none"
          >{{ node.label }}</text>
        </g>
      </svg>

      <!-- 图例 -->
      <div class="flex gap-4 px-4 py-3 border-t border-slate-100 text-xs text-slate-500">
        <span v-for="(color, type) in COLORS" :key="type" class="flex items-center gap-1">
          <span class="w-3 h-3 rounded-full inline-block" :style="{ background: color }"></span>
          {{ type }}
        </span>
      </div>
    </div>
  </section>
</template>
