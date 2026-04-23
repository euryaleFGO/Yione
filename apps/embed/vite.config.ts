import { resolve } from 'node:path';

import { defineConfig } from 'vite';

const entry = process.env.ENTRY || 'index';

export default defineConfig({
  publicDir: entry === 'index' ? 'public' : false,
  build: {
    lib: {
      entry: resolve(__dirname, `src/${entry}.ts`),
      name: entry === 'index' ? 'WeblingEmbed' : 'WeblingComponent',
      formats: ['iife'],
      fileName: () => entry === 'index' ? 'embed.js' : 'web-component.js',
    },
    outDir: 'dist',
    emptyOutDir: entry === 'index',
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
  },
});
