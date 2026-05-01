import axios, {
  type AxiosError,
  type AxiosRequestConfig,
  type AxiosResponse,
} from "axios";
import { useAuthStore } from "@/stores/auth";
import { DEFAULT_REQUEST_TIMEOUT_MS } from "@/utils/http-timeout";
import { clearAllSessionStorage, getMainToken } from "@/utils/session";

const normalizeBase = (value: string | undefined) =>
  String(value || "")
    .trim()
    .replace(/\/+$/, "");

const isVercelHosted = () => {
  if (typeof window === "undefined") return false;
  return window.location.hostname.toLowerCase().endsWith(".vercel.app");
};

const resolveApiBaseUrl = () => {
  const configuredBase = normalizeBase(import.meta.env.VITE_API_BASE_URL);
  if (configuredBase) return configuredBase;
  return isVercelHosted() ? "/_proxy" : "";
};

const resolveStaticBaseUrl = () => {
  const configuredStaticBase = normalizeBase(
    import.meta.env.VITE_STATIC_BASE_URL,
  );
  if (configuredStaticBase) return configuredStaticBase;

  const configuredApiBase = normalizeBase(import.meta.env.VITE_API_BASE_URL);
  return configuredApiBase || "";
};

export const API_BASE_URL = resolveApiBaseUrl();
export const STATIC_BASE_URL = resolveStaticBaseUrl();
export const NETDISK_API_BASE_URL =
  normalizeBase(import.meta.env.VITE_NETDISK_API_BASE) ||
  (API_BASE_URL ? `${API_BASE_URL}/netdisk_api/api` : "/netdisk_api/api");
export const JUDIAN_API_BASE_URL =
  normalizeBase(import.meta.env.VITE_JUDIAN_API_BASE) ||
  (API_BASE_URL
    ? `${API_BASE_URL}/netdisk_api/judian_api`
    : "/netdisk_api/judian_api");

export const buildApiUrl = (path: string) => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return API_BASE_URL ? `${API_BASE_URL}${normalizedPath}` : normalizedPath;
};

export const buildStaticUrl = (path: string) => {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return STATIC_BASE_URL
    ? `${STATIC_BASE_URL}${normalizedPath}`
    : normalizedPath;
};

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: DEFAULT_REQUEST_TIMEOUT_MS,
  headers: {
    "Content-Type": "application/json",
  },
});

request.interceptors.request.use(
  (config) => {
    const token = getMainToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

request.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      try {
        useAuthStore().clearAuth();
      } catch {
        clearAllSessionStorage();
      }
    }
    return Promise.reject(error);
  },
);

export const get = async <T = unknown>(
  url: string,
  config?: AxiosRequestConfig,
): Promise<T> => {
  const response = await request.get<T>(url, config);
  return response.data;
};

export const post = async <T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> => {
  const response = await request.post<T>(url, data, config);
  return response.data;
};

export const put = async <T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> => {
  const response = await request.put<T>(url, data, config);
  return response.data;
};

export const del = async <T = unknown>(
  url: string,
  config?: AxiosRequestConfig,
): Promise<T> => {
  const response = await request.delete<T>(url, config);
  return response.data;
};

export default request;
