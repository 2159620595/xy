import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearJudianSession,
  ensureJudianSession,
  getJudianToken,
  verifyStoredJudianSession,
} from "./judian-auth";

type StorageState = Record<string, string>;

const createStorageMock = () => {
  let state: StorageState = {};

  return {
    clear: () => {
      state = {};
    },
    getItem: (key: string) => state[key] ?? null,
    removeItem: (key: string) => {
      delete state[key];
    },
    setItem: (key: string, value: string) => {
      state[key] = String(value);
    },
  };
};

const replaceMock = vi.fn();
const storage = createStorageMock();

const installBrowserMocks = () => {
  vi.stubGlobal("localStorage", storage);
  vi.stubGlobal("window", {
    location: {
      pathname: "/judian/accounts",
      search: "?tab=main",
      replace: replaceMock,
    },
  });
};

describe("verifyStoredJudianSession", () => {
  beforeEach(() => {
    storage.clear();
    replaceMock.mockReset();
    vi.restoreAllMocks();
    installBrowserMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns false when remote verify rejects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    await expect(verifyStoredJudianSession("token-1")).resolves.toBe(false);
  });
});

describe("ensureJudianSession", () => {
  beforeEach(() => {
    storage.clear();
    replaceMock.mockReset();
    vi.restoreAllMocks();
    installBrowserMocks();
  });

  afterEach(() => {
    clearJudianSession();
    vi.unstubAllGlobals();
  });

  it("stores token after successful bootstrap", async () => {
    localStorage.setItem(
      "user_info",
      JSON.stringify({ username: "admin", role: "admin" }),
    );
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          success: true,
          token: "fresh-token",
          username: "admin",
          is_admin: true,
        }),
      }),
    );

    await expect(ensureJudianSession()).resolves.toBe(true);
    expect(getJudianToken()).toBe("fresh-token");
  });

  it("clears main auth and redirects on bootstrap 401", async () => {
    localStorage.setItem(
      "user_info",
      JSON.stringify({ username: "admin", role: "admin" }),
    );
    localStorage.setItem("auth_token", "main-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: "expired" }),
      }),
    );

    await expect(ensureJudianSession(true)).resolves.toBe(false);
    expect(localStorage.getItem("auth_token")).toBeNull();
    expect(replaceMock).toHaveBeenCalledWith(
      "/login?redirect=%2Fjudian%2Faccounts%3Ftab%3Dmain",
    );
  });
});
