import { defineConfig } from "astro/config";

// SITE_BASE=/<repo>/ for GitHub Pages project sites; "/" locally.
export default defineConfig({
  base: process.env.SITE_BASE ?? "/",
  site: process.env.SITE_URL,
  vite: {
    optimizeDeps: { exclude: ["@duckdb/duckdb-wasm"] },
  },
});
