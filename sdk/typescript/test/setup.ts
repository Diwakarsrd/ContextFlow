// Spins up a real `contextflow serve` (Python/FastAPI) instance as a
// subprocess for the SDK tests to hit over real HTTP — the same
// "prove it against the real thing, not a mock" bar the rest of this
// project holds itself to (see the Python side's live Postgres/MCP
// tests). No mocked fetch here; if the SDK's request/response shapes
// drift from the actual API, these tests fail for real.
import { spawn, type ChildProcess } from "node:child_process";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

export const TEST_PORT = 8931;
export const BASE_URL = `http://127.0.0.1:${TEST_PORT}`;
export const TEST_API_KEY_ENV = "sk_test_typescript_sdk_0123456789abcdef";

let serverProcess: ChildProcess | undefined;

export async function startServer(): Promise<void> {
  const workDir = mkdtempSync(join(tmpdir(), "contextflow-ts-sdk-test-"));
  // Configure one API key via env so the server enforces real auth,
  // rather than testing only against open/no-auth mode.
  const env = {
    ...process.env,
    CONTEXTOS_API_KEYS: `${TEST_API_KEY_ENV}:alice`,
  };

  serverProcess = spawn(
    "python3",
    ["-m", "uvicorn", "contextflow.api.app:app", "--host", "127.0.0.1", "--port", String(TEST_PORT)],
    { cwd: workDir, env, stdio: ["ignore", "pipe", "pipe"] },
  );

  await waitForServer();
}

export function stopServer(): void {
  serverProcess?.kill();
}

async function waitForServer(retries = 40): Promise<void> {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(`${BASE_URL}/health`);
      if (res.ok) return;
    } catch {
      // not up yet
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("contextflow serve did not become healthy in time");
}
