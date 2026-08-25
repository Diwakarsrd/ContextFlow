import { ContextFlowError } from "./errors.js";
import type {
  ContextObjectResponse,
  ContextPackOptions,
  ContextPackResponse,
  ContextTraceResponse,
  MemoryEntryResponse,
  MemoryScope,
  RecallOptions,
  SearchOptions,
  TraceOptions,
} from "./types.js";

export interface ContextEngineOptions {
  /** Base URL of a running `contextflow serve` instance, e.g. "http://localhost:8000". */
  baseUrl: string;
  /** API key from `contextflow auth create-key`. Omit only if the server
   * is running in open/local-dev mode (see SECURITY.md) — every request
   * will fail with 401 against a server that has keys configured. */
  apiKey?: string;
  /** Override fetch, e.g. for testing or non-browser/non-Node runtimes
   * that need a polyfill. Defaults to the global `fetch`. */
  fetchFn?: typeof fetch;
}

/**
 * TypeScript client for the ContextFlow REST API.
 *
 * ```ts
 * const engine = new ContextEngine({ baseUrl: "http://localhost:8000", apiKey: "sk_..." });
 * const results = await engine.retrieve("payment decisions");
 * const pack = await engine.contextPack("prepare architecture review", { entity: "payments" });
 * ```
 *
 * Every method throws {@link ContextFlowError} on a non-2xx response —
 * check `error.status` to distinguish auth failures (401), rate limits
 * (429), etc.
 */
export class ContextEngine {
  private readonly baseUrl: string;
  private readonly apiKey: string | undefined;
  private readonly fetchFn: typeof fetch;

  constructor(options: ContextEngineOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.apiKey = options.apiKey;
    this.fetchFn = options.fetchFn ?? fetch;
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    const res = await this.fetchFn(`${this.baseUrl}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      let parsedBody: unknown = null;
      try {
        parsedBody = await res.json();
      } catch {
        // Response wasn't JSON (e.g. a proxy's plain-text 502) — that's
        // fine, ContextFlowError falls back to statusText below.
      }
      throw new ContextFlowError(res.status, res.statusText, parsedBody);
    }

    return res.json() as Promise<T>;
  }

  /** Search across all connected sources. */
  async retrieve(query: string, options: SearchOptions = {}): Promise<ContextObjectResponse[]> {
    return this.post<ContextObjectResponse[]>("/v1/search", {
      query,
      limit: options.limit ?? 10,
    });
  }

  /** Build a compiled, agent-ready Context Pack for a task. */
  async contextPack(task: string, options: ContextPackOptions = {}): Promise<ContextPackResponse> {
    return this.post<ContextPackResponse>("/v1/context-pack", {
      task,
      entity: options.entity ?? null,
      max_tokens: options.maxTokens ?? 3000,
    });
  }

  /** Run a search with full pipeline tracing (candidate counts and
   * timing at each stage) — see docs/concepts/tracing.md. */
  async trace(query: string, options: TraceOptions = {}): Promise<ContextTraceResponse> {
    return this.post<ContextTraceResponse>("/v1/trace", {
      query,
      limit: options.limit ?? 10,
    });
  }

  /** Store a fact in session/user/agent/org memory. */
  async remember(
    scope: MemoryScope,
    scopeId: string,
    fact: string,
    metadata?: Record<string, unknown>,
  ): Promise<{ id: string }> {
    return this.post<{ id: string }>("/v1/memory/remember", {
      scope,
      scope_id: scopeId,
      fact,
      metadata: metadata ?? null,
    });
  }

  /** Recall facts from session/user/agent/org memory, ranked by keyword
   * relevance if `options.query` is given, else most-recent-first. */
  async recall(
    scope: MemoryScope,
    scopeId: string,
    options: RecallOptions = {},
  ): Promise<MemoryEntryResponse[]> {
    return this.post<MemoryEntryResponse[]>("/v1/memory/recall", {
      scope,
      scope_id: scopeId,
      query: options.query ?? null,
      limit: options.limit ?? 10,
    });
  }
}
