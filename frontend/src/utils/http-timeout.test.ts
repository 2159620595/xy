import { afterEach, describe, expect, it, vi } from "vitest";
import {
  DEFAULT_REQUEST_TIMEOUT_MS,
  createTimeoutController,
  parseTimeoutMs,
} from "./http-timeout";

describe("parseTimeoutMs", () => {
  it("falls back for empty values", () => {
    expect(parseTimeoutMs("", 30000)).toBe(30000);
    expect(parseTimeoutMs(undefined, 30000)).toBe(30000);
  });

  it("accepts positive integers", () => {
    expect(parseTimeoutMs("15000", 30000)).toBe(15000);
    expect(parseTimeoutMs(45000, 30000)).toBe(45000);
  });

  it("rejects zero and invalid values", () => {
    expect(parseTimeoutMs("0", 30000)).toBe(30000);
    expect(parseTimeoutMs("-1", 30000)).toBe(30000);
    expect(parseTimeoutMs("abc", 30000)).toBe(30000);
  });
});

describe("createTimeoutController", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("aborts when timeout expires", () => {
    vi.useFakeTimers();
    const { signal } = createTimeoutController(25);
    expect(signal.aborted).toBe(false);
    vi.advanceTimersByTime(25);
    expect(signal.aborted).toBe(true);
  });

  it("does not arm a timer for non-positive timeout", () => {
    const { signal, cancel } = createTimeoutController(0);
    expect(signal.aborted).toBe(false);
    cancel();
  });
});

describe("DEFAULT_REQUEST_TIMEOUT_MS", () => {
  it("is a positive integer", () => {
    expect(DEFAULT_REQUEST_TIMEOUT_MS).toBeGreaterThan(0);
  });
});
