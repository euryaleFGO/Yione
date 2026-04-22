# @webling/sdk

面向接入方的裸 JS/TS SDK，用于服务端换 embed token、调用管理接口等。

```ts
import { WebLingClient } from '@webling/sdk';

const client = new WebLingClient({
  apiBase: 'https://api.webling.io',
  apiKey: process.env.WEBLING_API_KEY!,
});
```
