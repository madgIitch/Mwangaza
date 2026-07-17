import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  root: "frontend",
  plugins: [react()],
  publicDir: "public",
  build: {
    outDir: "../dist/frontend",
    emptyOutDir: true
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000"
    }
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["../tests/frontend/**/*.{test,spec}.{ts,tsx}"],
    setupFiles: "../tests/frontend/setup.ts"
  }
});
