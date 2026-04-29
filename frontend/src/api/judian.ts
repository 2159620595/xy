import axios from "axios";
import {
  clearJudianSession,
  ensureJudianSession,
  getJudianToken,
  getMainUser,
} from "@/utils/judian-auth";
import { JUDIAN_API_BASE_URL } from "@/utils/request";

const parsePositiveInt = (
  value: string | number | undefined,
  fallback: number,
) => {
  const numeric = Number(value);
  return Number.isInteger(numeric) && numeric > 0 ? numeric : fallback;
};

export const JUDIAN_API_BASE = JUDIAN_API_BASE_URL;
export const JUDIAN_API_TIMEOUT_MS = parsePositiveInt(
  import.meta.env.VITE_JUDIAN_API_TIMEOUT_MS,
  30000,
);
export const JUDIAN_LOGIN_API_TIMEOUT_MS = parsePositiveInt(
  import.meta.env.VITE_JUDIAN_LOGIN_API_TIMEOUT_MS,
  Math.max(JUDIAN_API_TIMEOUT_MS, 60000),
);

export const buildJudianApiUrl = (path: string) =>
  `${JUDIAN_API_BASE}${String(path || "").startsWith("/") ? path : `/${path}`}`;

const judianClient = axios.create({
  baseURL: JUDIAN_API_BASE,
  timeout: JUDIAN_API_TIMEOUT_MS,
});

export const judianPublicClient = axios.create({
  baseURL: JUDIAN_API_BASE,
  timeout: JUDIAN_API_TIMEOUT_MS,
});

judianClient.interceptors.request.use(async (config) => {
  if (!getJudianToken() && getMainUser()) {
    try {
      await ensureJudianSession();
    } catch {}
  }

  config.headers = config.headers || {};
  const token = getJudianToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  } else {
    delete config.headers.Authorization;
  }
  return config;
});

judianClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalConfig = error?.config;
    const isUnauthorized = error?.response?.status === 401;

    if (isUnauthorized && originalConfig && !originalConfig.__judianRetried) {
      originalConfig.__judianRetried = true;
      clearJudianSession();
      try {
        const synced = await ensureJudianSession(true);
        if (synced) {
          const token = getJudianToken();
          if (token) {
            originalConfig.headers = originalConfig.headers || {};
            originalConfig.headers.Authorization = `Bearer ${token}`;
          }
          return judianClient(originalConfig);
        }
      } catch {}
    }

    if (isUnauthorized && !getMainUser()) {
      clearJudianSession();
      if (
        typeof window !== "undefined" &&
        window.location.pathname.startsWith("/judian")
      ) {
        const redirect = encodeURIComponent(
          window.location.pathname + window.location.search,
        );
        window.location.href = `/login?redirect=${redirect}`;
      }
    }

    return Promise.reject(error);
  },
);

export const judianApi = {
  client: judianClient,
  verify: () => judianClient.get("/verify"),
  getDashboardSummary: () => judianClient.get("/dashboard/summary"),
  listAccounts: () => judianClient.get("/accounts"),
  loginAccount: (data: Record<string, unknown>) =>
    judianClient.post("/accounts/login", data, {
      timeout: JUDIAN_LOGIN_API_TIMEOUT_MS,
    }),
  reloginAccount: (rowId: number | string) =>
    judianClient.post(`/accounts/${rowId}/relogin`, null, {
      timeout: JUDIAN_LOGIN_API_TIMEOUT_MS,
    }),
  updateAccount: (rowId: number | string, data: Record<string, unknown>) =>
    judianClient.put(`/accounts/${rowId}`, data),
  deleteAccount: (rowId: number | string) =>
    judianClient.delete(`/accounts/${rowId}`),
  listCdKeys: () => judianClient.get("/cdkeys"),
  listCards: () => judianClient.get("/cards"),
  getCard: (cardId: number | string) => judianClient.get(`/cards/${cardId}`),
  createCard: (data: Record<string, unknown>) =>
    judianClient.post("/cards", data),
  updateCard: (cardId: number | string, data: Record<string, unknown>) =>
    judianClient.put(`/cards/${cardId}`, data),
  deleteCard: (cardId: number | string) =>
    judianClient.delete(`/cards/${cardId}`),
  importCdKeys: (data: Record<string, unknown>) =>
    judianClient.post("/cdkeys/import", data),
  importCdKeysFromNetdisk: (data: Record<string, unknown>) =>
    judianClient.post("/cdkeys/import/netdisk", data),
  importCardCodesFromNetdisk: (
    cardId: number | string,
    data: Record<string, unknown>,
  ) => judianClient.post(`/cards/${cardId}/import/netdisk`, data),
  importCardCodesFromJudian: (
    cardId: number | string,
    data: Record<string, unknown>,
  ) => judianClient.post(`/cards/${cardId}/import/judian`, data),
  generateCdKeys: (data: Record<string, unknown>) =>
    judianClient.post("/cdkeys", data),
  updateCdKey: (rowId: number | string, data: Record<string, unknown>) =>
    judianClient.put(`/cdkeys/${rowId}`, data),
  cleanInactiveCdKeys: () => judianClient.delete("/cdkeys/inactive"),
  publicRedeemInfo: (code: string, sessionId?: string, forceRefresh = false) =>
    judianPublicClient.get("/cdkey/redeem", {
      params: { code, session: sessionId || "", refresh: forceRefresh ? 1 : 0 },
    }),
  publicUnlockDetail: (sessionId: string) =>
    judianPublicClient.get(`/public/unlock/${sessionId}`),
  publicUnlockBatchDetail: (sessionId: string) =>
    judianPublicClient.get(`/public/unlock/${sessionId}/batch`),
  publicUnlockBatchPreview: (
    sessionId: string,
    params: { count: number; vipId?: string; packageType?: string },
  ) =>
    judianPublicClient.get(`/public/unlock/${sessionId}/batch/preview`, {
      params: {
        count: params.count,
        vip_id: params.vipId || "",
        package_type: params.packageType || "",
      },
    }),
  publicUnlockScan: (sessionId: string, data: Record<string, unknown>) =>
    judianPublicClient.post(`/public/unlock/${sessionId}/scan`, data),
  publicUnlockBatchPurchase: (
    sessionId: string,
    data: Record<string, unknown>,
  ) => judianPublicClient.post(`/public/unlock/${sessionId}/batch`, data),
  publicUnlockBatchCancel: (sessionId: string) =>
    judianPublicClient.post(`/public/unlock/${sessionId}/batch/cancel`),
  publicUnlockConfirm: (sessionId: string) =>
    judianPublicClient.post(`/public/unlock/${sessionId}/confirm`),
  publicUnlockComplete: (sessionId: string) =>
    judianPublicClient.post(`/public/unlock/${sessionId}/complete`),
};

export default judianClient;
