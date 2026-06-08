import { defineConfig } from "vitest/config";

// Kept separate from vite.config.ts so the build config stays untouched.
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
