import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { configDefaults, defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": {
        target: process.env.VITE_DEV_API_PROXY_TARGET ?? "http://backend:8000",
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    exclude: [
      ...configDefaults.exclude,
      "e2e/**",
    ],
  },
});
