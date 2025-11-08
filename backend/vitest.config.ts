import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    setupFiles: ["./tests/setup.ts"],
    threads: false,
    reporters: "default",
    coverage: {
      provider: "v8",
      reportsDirectory: "./coverage",
    },
    testTimeout: 30000,
  },
});
