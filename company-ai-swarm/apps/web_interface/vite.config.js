import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Served by the API gateway at /ui (apps/api_gateway/main.py mounts dist/). The dev server
// proxies API calls to a locally running gateway so `npm run dev` works against real data.
export default defineConfig({
  base: "/ui/",
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(
      ["/activity", "/chat", "/files", "/proposals", "/objectives", "/agents", "/health"].map(
        (p) => [p, { target: "http://127.0.0.1:8000", changeOrigin: true }]
      )
    ),
  },
});
