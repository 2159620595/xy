import { describe, expect, it } from "vitest";
import {
  JUDIAN_API_BASE,
  JUDIAN_API_TIMEOUT_MS,
  JUDIAN_LOGIN_API_TIMEOUT_MS,
  judianApi,
  judianPublicClient,
} from "./judian";

describe("judian clients", () => {
  it("keeps authenticated client timeout aligned", () => {
    expect(judianApi.client.defaults.timeout).toBe(JUDIAN_API_TIMEOUT_MS);
  });

  it("uses the same timeout for public client", () => {
    expect(judianPublicClient.defaults.timeout).toBe(JUDIAN_API_TIMEOUT_MS);
  });

  it("uses the shared base url for both clients", () => {
    expect(judianApi.client.defaults.baseURL).toBe(JUDIAN_API_BASE);
    expect(judianPublicClient.defaults.baseURL).toBe(JUDIAN_API_BASE);
  });

  it("keeps login and relogin on the longer timeout", () => {
    expect(judianApi.loginAccountConfig.timeout).toBe(
      JUDIAN_LOGIN_API_TIMEOUT_MS,
    );
    expect(judianApi.reloginAccountConfig.timeout).toBe(
      JUDIAN_LOGIN_API_TIMEOUT_MS,
    );
  });
});
