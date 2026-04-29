import { DEFAULT_REQUEST_TIMEOUT_MS, createTimeoutController } from "@/utils/http-timeout";
import { JUDIAN_API_BASE_URL, NETDISK_API_BASE_URL } from "@/utils/request";

const TOKEN_KEY = "judian_auth_token";
const USER_KEY = "judian_user_info";
const MAIN_USER_KEY = "user_info";
const SESSION_TRUST_WINDOW_MS = 2 * 60 * 1000;

const buildUrl = (base: string, path: string) =>
  `${String(base || "")
    .trim()
    .replace(/\/+$/, "")}${path.startsWith("/") ? path : `/${path}`}`;

const JUDIAN_API_BASE = JUDIAN_API_BASE_URL;
const NETDISK_API_BASE = NETDISK_API_BASE_URL;
const JUDIAN_VERIFY_URL = buildUrl(JUDIAN_API_BASE, "/verify");
const JUDIAN_SESSION_BOOTSTRAP_URL = buildUrl(
  NETDISK_API_BASE,
  "/judian/session",
);

let sessionSyncPromise: Promise<boolean> | null = null;
let trustedToken = "";
let trustedAt = 0;

const parseStoredJson = <T = Record<string, unknown>>(
  key: string,
): T | null => {
  const raw = localStorage.getItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
};

const clearExpiredMainSession = () => {
  clearJudianSession();
  localStorage.removeItem("auth_token");
  localStorage.removeItem(MAIN_USER_KEY);
};

const redirectToLogin = () => {
  if (
    typeof window === "undefined" ||
    window.location.pathname.startsWith("/login")
  )
    return;
  const redirect = `${window.location.pathname}${window.location.search || ""}`;
  window.location.replace(`/login?redirect=${encodeURIComponent(redirect)}`);
};

const canReuseTrustedToken = (token: string) =>
  Boolean(
    token &&
    token === trustedToken &&
    Date.now() - trustedAt < SESSION_TRUST_WINDOW_MS,
  );

const markTrustedToken = (token: string) => {
  trustedToken = token;
  trustedAt = Date.now();
};

export function getMainUser() {
  return parseStoredJson<{ username?: string; role?: string }>(MAIN_USER_KEY);
}

export function getJudianToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function getJudianUser() {
  return parseStoredJson(USER_KEY);
}

export function setJudianSession(payload: {
  token?: string;
  user_id?: number;
  username?: string;
  is_admin?: boolean;
}) {
  localStorage.setItem(TOKEN_KEY, payload.token || "");
  localStorage.setItem(
    USER_KEY,
    JSON.stringify({
      user_id: payload.user_id,
      username: payload.username,
      is_admin: Boolean(payload.is_admin),
    }),
  );
  markTrustedToken(payload.token || "");
}

export function clearJudianSession() {
  trustedToken = "";
  trustedAt = 0;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function verifyStoredJudianSession(token: string) {
  if (!token) return false;
  const { signal, cancel } = createTimeoutController(DEFAULT_REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(JUDIAN_VERIFY_URL, {
      method: "GET",
      cache: "no-store",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      signal,
    });
    if (!response.ok) return false;
    const data = await response.json();
    return Boolean(data?.authenticated);
  } catch {
    return false;
  } finally {
    cancel();
  }
}

export async function ensureJudianSession(force = false) {
  if (sessionSyncPromise) return sessionSyncPromise;

  sessionSyncPromise = (async () => {
    const currentToken = getJudianToken();
    if (!force && canReuseTrustedToken(currentToken)) {
      return true;
    }

    if (!force && currentToken) {
      const verified = await verifyStoredJudianSession(currentToken);
      if (verified) {
        markTrustedToken(currentToken);
        return true;
      }
    }

    clearJudianSession();
    const mainUser = getMainUser();
    if (!mainUser?.username) return false;

    const { signal, cancel } = createTimeoutController(DEFAULT_REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(JUDIAN_SESSION_BOOTSTRAP_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: mainUser.username,
          role: mainUser.role || "admin",
        }),
        signal,
      });

      const data = await response.json().catch(() => null);
      if (!response.ok || !data?.success || !data?.token) {
        if (response.status === 401) {
          clearExpiredMainSession();
          redirectToLogin();
        }
        return false;
      }

      setJudianSession(data);
      return true;
    } catch {
      return false;
    } finally {
      cancel();
    }
  })();

  try {
    return await sessionSyncPromise;
  } finally {
    sessionSyncPromise = null;
  }
}
