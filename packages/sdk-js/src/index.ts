// 裸 JS client：M8 起接入方服务端使用。
export interface WebLingClientOptions {
  apiBase: string;
  apiKey: string;
}

export class WebLingClient {
  constructor(public readonly options: WebLingClientOptions) {}
}
