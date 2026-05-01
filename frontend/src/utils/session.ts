const MAIN_TOKEN_KEY = "auth_token";
const MAIN_USER_KEY = "user_info";
const JUDIAN_TOKEN_KEY = "judian_auth_token";
const JUDIAN_USER_KEY = "judian_user_info";

export const getMainToken = () => localStorage.getItem(MAIN_TOKEN_KEY) || "";

export const readStoredJson = <T = Record<string, unknown>>(
  key: string,
): T | null => {
  const raw = localStorage.getItem(key);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as T;
  } catch {
    localStorage.removeItem(key);
    return null;
  }
};

export const getMainUser = <T = Record<string, unknown>>() =>
  readStoredJson<T>(MAIN_USER_KEY);

export const clearJudianSessionStorage = () => {
  localStorage.removeItem(JUDIAN_TOKEN_KEY);
  localStorage.removeItem(JUDIAN_USER_KEY);
};

export const clearMainSessionStorage = () => {
  localStorage.removeItem(MAIN_TOKEN_KEY);
  localStorage.removeItem(MAIN_USER_KEY);
};

export const clearAllSessionStorage = () => {
  clearMainSessionStorage();
  clearJudianSessionStorage();
};
