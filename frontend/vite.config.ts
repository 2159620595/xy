import path from "node:path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const backendTarget = "http://localhost:8080";
const outputDir = process.env.FRONTEND_OUT_DIR?.trim() || "dist";

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

const legacyProxyTargets = [
  "/api",
  "/netdisk_api",
  "/verify",
  "/logout",
  "/system-settings",
  "/cards",
  "/delivery-rules",
  "/generate-captcha",
  "/verify-captcha",
  "/send-verification-code",
  "/cookies",
  "/cookie",
  "/password-login",
  "/qr-login",
  "/ai-reply-settings",
  "/itemReplays",
  "/item-reply",
  "/keywords-with-item-id",
  "/keywords-export",
  "/keywords-import",
  "/default-reply",
  "/upload-image",
  "/change-password",
  "/backup",
];

const legacySpaProxyTargets = [
  "/login",
  "/register",
  "/items",
  "/item-search",
  "/keywords",
  "/notification-channels",
  "/message-notifications",
  "/admin",
];

const buildProxyMap = () => {
  const proxy: Record<string, ReturnType<typeof spaRouteProxy> | {
    target: string;
    changeOrigin: boolean;
    rewrite?: (path: string) => string;
  }> = {
    "/_proxy": {
      target: backendTarget,
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/_proxy/, ""),
    },
  };

  for (const route of legacyProxyTargets) {
    proxy[route] = {
      target: backendTarget,
      changeOrigin: true,
    };
  }

  for (const route of legacySpaProxyTargets) {
    proxy[route] = spaRouteProxy();
  }

  return proxy;
};

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    // Default to a local dist directory for Vercel deployments.
    // Set FRONTEND_OUT_DIR=../backend/static when you want an integrated backend build.
    outDir: path.resolve(__dirname, outputDir),
  },
  server: {
    proxy: buildProxyMap(),
  },
});
