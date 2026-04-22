# 嵌入集成手册（草稿）

> 本文档占位。真正的版本会在 M8/M9/M10 写。
> 参考 `PLAN.md` §7 的三种接入形态。

## 快速集成（TODO 待 M8）

```html
<script src="https://cdn.webling.io/embed.v1.min.js"
        data-api-base="https://api.webling.io"
        data-character="ling"
        data-token-endpoint="https://your-site.com/api/webling-token"
        defer></script>
```

## 服务端换 token（TODO 待 M6）

```ts
import { WebLingClient } from '@webling/sdk';
const client = new WebLingClient({ apiBase, apiKey });
const { token, expiresAt } = await client.createEmbedToken({ character: 'ling' });
```
