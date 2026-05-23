import path from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendPort = env.VITE_BACKEND_PORT || "8000";

  return {
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
        timeout: 0,
        proxyTimeout: 0,
        configure: (proxy) => {
          proxy.on("proxyReq", (proxyReq) => {
            // Compression can buffer the full body before the client sees chunks.
            proxyReq.setHeader("Accept-Encoding", "identity");
          });
          proxy.on("proxyRes", (proxyRes, req) => {
            const contentType = String(proxyRes.headers["content-type"] ?? "");
            if (!contentType.includes("text/event-stream")) return;

            proxyRes.headers["cache-control"] = "no-cache, no-transform";
            proxyRes.headers["x-accel-buffering"] = "no";
            delete proxyRes.headers["content-encoding"];

            proxyRes.socket?.setTimeout?.(0);
            req.socket?.setTimeout?.(0);
          });
        },
      },
    },
  },
};
});
