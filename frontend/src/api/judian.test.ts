import { describe, expect, it } from "vitest";
import { JUDIAN_API_TIMEOUT_MS, judianApi, judianPublicClient } from "./judian";

describe("judian clients", () => {
  it("keeps authenticated client timeout aligned", () => {
    expect(judianApi.client.defaults.timeout).toBe(JUDIAN_API_TIMEOUT_MS);
  });

  it("uses the same timeout for public client", () => {
    expect(judianPublicClient.defaults.timeout).toBe(JUDIAN_API_TIMEOUT_MS);
  });
});
