// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - tanstackStart, viteReact, tailwindcss, tsConfigPaths, nitro (build-only using cloudflare as a default target),
//     componentTagger (dev-only), VITE_* env injection, @ path alias, React/TanStack dedupe,
//     error logger plugins, and sandbox detection (port/host/strictPort).
// You can pass additional config via defineConfig({ vite: { ... }, etc... }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

export default defineConfig({
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
    // nitro/vite builds from this
    server: { entry: "server" },
  },
  // Outside a Lovable build the nitro deploy plugin is skipped by default, which leaves
  // only dist/client + dist/server — no server bundle a host can run. Pinning the preset
  // force-enables nitro and emits .vercel/output (Build Output API v3) for Vercel.
  // Inside Lovable this override is ignored: that build forces the Cloudflare preset.
  nitro: { preset: "vercel" },
});
