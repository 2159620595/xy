import path from "node:path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const backendTarget = "http://localhost:8080";

const spaRouteProxy = () => ({
  target: backendTarget,
  changeOrigin: true,
  bypass: (req: {
    method?: string;
    headers: Record<string, string | string[] | undefined>;
  }) => {
    const accept = Array.isArray(req.headers.accept)
      ? req.headers.accept.join(",")
      : req.headers.accept;
    if (req.method === "GET" && accept?.includes("text/html")) {
      return "/index.html";
    }
    return undefined;
  },
});

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    // Build directly into the backend static directory so the integrated app
    // can be served by reply_server without an extra copy step.
    outDir: path.resolve(__dirname, "../static"),
    emptyOutDir: false,
  },
  server: {
    proxy: {
      "/api": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/netdisk_api": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/login": spaRouteProxy(),
      "/verify": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/logout": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/register": {
        target: backendTarget,
        changeOrigin: true,
        bypass: (req) => {
          const accept = Array.isArray(req.headers.accept)
            ? req.headers.accept.join(",")
            : req.headers.accept;
          if (req.method === "GET" && accept?.includes("text/html")) {
            return "/index.html";
          }
          return undefined;
        },
      },
      "/system-settings": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/cards": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/delivery-rules": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/generate-captcha": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/verify-captcha": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/send-verification-code": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/cookies": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/cookie": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/password-login": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/qr-login": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/ai-reply-settings": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/items": spaRouteProxy(),
      "/item-search": spaRouteProxy(),
      "/itemReplays": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/item-reply": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/keywords": spaRouteProxy(),
      "/keywords-with-item-id": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/keywords-export": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/keywords-import": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/default-reply": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/notification-channels": spaRouteProxy(),
      "/message-notifications": spaRouteProxy(),
      "/upload-image": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/change-password": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/backup": {
        target: backendTarget,
        changeOrigin: true,
      },
      "/admin": {
        target: backendTarget,
        changeOrigin: true,
        bypass: (req) => {
          const accept = Array.isArray(req.headers.accept)
            ? req.headers.accept.join(",")
            : req.headers.accept;
          if (req.method === "GET" && accept?.includes("text/html")) {
            return "/index.html";
          }
          return undefined;
        },
      },
    },
  },
});
