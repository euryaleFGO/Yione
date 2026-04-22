/**
 * Tiny typed fetch wrapper. No runtime dep on fetch polyfill — assumes the
 * global fetch API (browser, Node 20+, edge).
 */

export interface HttpClientOptions {
  /** Base URL, e.g. `http://localhost:8000`. No trailing slash. */
  baseUrl: string;
  /** Optional bearer token accessor (refreshed per request). */
  getToken?: () => string | null | Promise<string | null>;
  /** Custom fetch implementation (tests inject a mock). */
  fetch?: typeof fetch;
}

export class HttpError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(message);
    this.name = 'HttpError';
  }
}

export class HttpClient {
  private readonly baseUrl: string;
  private readonly getToken?: HttpClientOptions['getToken'];
  private readonly fetchImpl: typeof fetch;

  constructor(options: HttpClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, '');
    this.getToken = options.getToken;
    this.fetchImpl = options.fetch ?? fetch.bind(globalThis);
  }

  get<T>(path: string, init?: RequestInit): Promise<T> {
    return this.request<T>('GET', path, undefined, init);
  }

  post<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    return this.request<T>('POST', path, body, init);
  }

  put<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    return this.request<T>('PUT', path, body, init);
  }

  delete<T>(path: string, init?: RequestInit): Promise<T> {
    return this.request<T>('DELETE', path, undefined, init);
  }

  private async request<T>(
    method: string,
    path: string,
    body: unknown,
    init?: RequestInit,
  ): Promise<T> {
    const url = path.startsWith('http') ? path : `${this.baseUrl}${path}`;
    const headers = new Headers(init?.headers);
    if (body !== undefined && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
    const token = await this.getToken?.();
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    const res = await this.fetchImpl(url, {
      ...init,
      method,
      headers,
      body: body === undefined ? init?.body : JSON.stringify(body),
    });

    if (!res.ok) {
      let parsed: unknown;
      try {
        parsed = await res.json();
      } catch {
        parsed = await res.text();
      }
      throw new HttpError(`HTTP ${res.status} for ${method} ${path}`, res.status, parsed);
    }

    if (res.status === 204) return undefined as T;
    const contentType = res.headers.get('Content-Type') ?? '';
    if (contentType.includes('application/json')) {
      return (await res.json()) as T;
    }
    return (await res.text()) as unknown as T;
  }
}
