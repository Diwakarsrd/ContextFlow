import { describe, expect, it } from "vitest";
import { ContextEngine, ContextFlowError } from "../src/index.js";
import { BASE_URL, TEST_API_KEY_ENV } from "./setup.js";

function client(): ContextEngine {
  return new ContextEngine({ baseUrl: BASE_URL, apiKey: TEST_API_KEY_ENV });
}

describe("auth", () => {
  it("rejects requests with no API key against a server with keys configured", async () => {
    const unauthed = new ContextEngine({ baseUrl: BASE_URL });
    await expect(unauthed.retrieve("anything")).rejects.toThrow(ContextFlowError);

    try {
      await unauthed.retrieve("anything");
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ContextFlowError);
      expect((err as ContextFlowError).status).toBe(401);
    }
  });

  it("rejects an invalid API key", async () => {
    const badKey = new ContextEngine({ baseUrl: BASE_URL, apiKey: "sk_totally_wrong" });
    try {
      await badKey.retrieve("anything");
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ContextFlowError);
      expect((err as ContextFlowError).status).toBe(401);
    }
  });

  it("accepts a valid API key", async () => {
    const results = await client().retrieve("anything");
    expect(Array.isArray(results)).toBe(true);
  });
});

describe("retrieve", () => {
  it("returns an array shaped like ContextObjectResponse[]", async () => {
    const results = await client().retrieve("payments", { limit: 5 });
    expect(Array.isArray(results)).toBe(true);
    // No data has been ingested into this test server (there's no REST
    // ingest endpoint — see docs/integrations), so we assert the shape
    // of the contract, not specific content. Content-level retrieval
    // correctness is covered extensively on the Python side.
  });
});

describe("contextPack", () => {
  it("returns a ContextPackResponse with the expected shape", async () => {
    const pack = await client().contextPack("prepare for the meeting", { maxTokens: 500 });
    expect(pack.task).toBe("prepare for the meeting");
    expect(Array.isArray(pack.sources)).toBe(true);
    expect(Array.isArray(pack.conflicts)).toBe(true);
    expect(typeof pack.confidence).toBe("number");
  });
});

describe("trace", () => {
  it("returns pipeline stages with real timing", async () => {
    const trace = await client().trace("payments", { limit: 5 });
    expect(trace.query).toBe("payments");
    expect(Array.isArray(trace.stages)).toBe(true);
    const stageNames = trace.stages.map((s) => s.name);
    expect(stageNames).toContain("route");
    expect(stageNames).toContain("rerank");
    expect(trace.total_duration_ms).toBeGreaterThanOrEqual(0);
  });
});

describe("memory", () => {
  it("remembers a fact and recalls it by keyword, end to end over real HTTP", async () => {
    const engine = client();
    const scopeId = `test-user-${Date.now()}`;

    const { id } = await engine.remember("user", scopeId, "Prefers annual contracts and EU billing");
    expect(typeof id).toBe("string");

    const recalled = await engine.recall("user", scopeId, { query: "annual contracts" });
    expect(recalled.length).toBe(1);
    expect(recalled[0].content).toBe("Prefers annual contracts and EU billing");
  });

  it("scopes memory by scopeId so different users don't see each other's facts", async () => {
    const engine = client();
    const suffix = Date.now();
    await engine.remember("user", `alice-${suffix}`, "alice's fact");
    await engine.remember("user", `bob-${suffix}`, "bob's fact");

    const aliceMemories = await engine.recall("user", `alice-${suffix}`);
    expect(aliceMemories.length).toBe(1);
    expect(aliceMemories[0].content).toBe("alice's fact");
  });
});

describe("error handling", () => {
  it("throws ContextFlowError with a readable message on failure", async () => {
    const unauthed = new ContextEngine({ baseUrl: BASE_URL });
    try {
      await unauthed.retrieve("x");
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(Error);
      expect((err as Error).message).toContain("ContextFlow API error");
    }
  });
});
