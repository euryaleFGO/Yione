#!/usr/bin/env node
/**
 * 构建后拷贝脚本：把 apps/web/public 里 Live2D / viseme / favicon 依赖拷到 apps/embed/dist。
 *
 * 为什么不用 Vite 的 publicDir 统一包办？
 * - library 模式产物（embed.js / web-component.js）禁用了 publicDir，避免重复拷贝 5MB+ 的 avatars；
 * - app 模式产物用了自己的 public 只放 demo.html；
 * - avatars / live2dcubismcore.min.js 维护在 apps/web/public 作为单一来源（web 和 embed 共享），
 *   embed 构建完再拷一份到 dist 就不会让 web 的 public 被 embed 的 build 步骤触碰。
 *
 * 跨平台：用 fs.cpSync（Node 16.7+ 支持 recursive），不依赖 shell cp。
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const embedRoot = path.resolve(__dirname, '..');
const webPublic = path.resolve(embedRoot, '../web/public');
const dist = path.resolve(embedRoot, 'dist');

if (!fs.existsSync(dist)) {
  console.error(`[embed/copy-web-public] ${dist} 不存在，跳过。请先跑 build:app。`);
  process.exit(0);
}

/** 要从 web/public 拷到 embed/dist 的条目（目录和文件都支持） */
const entries = [
  'avatars',
  'live2dcubismcore.min.js',
  'favicon.svg',
];

for (const name of entries) {
  const src = path.join(webPublic, name);
  const dest = path.join(dist, name);
  if (!fs.existsSync(src)) {
    console.warn(`[embed/copy-web-public] 源不存在，跳过：${src}`);
    continue;
  }
  // 已存在时先清理，避免旧内容残留
  if (fs.existsSync(dest)) {
    fs.rmSync(dest, { recursive: true, force: true });
  }
  fs.cpSync(src, dest, { recursive: true });
  console.log(`[embed/copy-web-public] copied ${name}`);
}

console.log('[embed/copy-web-public] done');
