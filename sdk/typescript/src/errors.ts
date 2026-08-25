/** Thrown for any non-2xx response from the ContextFlow REST API. Carries
 * the HTTP status and the parsed error body (when the server returned
 * JSON, which FastAPI does for its own errors) so callers can
 * distinguish, e.g., 401 (bad/missing key) from 429 (rate limited) from
 * 500 (server error) instead of pattern-matching a message string. */
export class ContextFlowError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, statusText: string, body: unknown) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : statusText;
    super(`ContextFlow API error (${status}): ${detail}`);
    this.name = "ContextFlowError";
    this.status = status;
    this.body = body;
  }
}
