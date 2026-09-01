import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globalSetup: ["./test/globalSetup.ts"],
    testTimeout: 15000,
    hookTimeout: 20000,
  },
});
