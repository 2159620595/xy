const DEFAULT_FALLBACK_TIMEOUT_MS = 30000;

export const parseTimeoutMs = (
  value: string | number | undefined,
  fallback: number,
) => {
  const numeric = Number(value);
  return Number.isInteger(numeric) && numeric > 0 ? numeric : fallback;
};

export const DEFAULT_REQUEST_TIMEOUT_MS = parseTimeoutMs(
  import.meta.env.VITE_API_TIMEOUT_MS,
  DEFAULT_FALLBACK_TIMEOUT_MS,
);

export const createTimeoutController = (timeoutMs: number) => {
  const controller = new AbortController();
  if (!(timeoutMs > 0)) {
    return {
      signal: controller.signal,
      cancel: () => {},
    };
  }

  const timer = globalThis.setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  return {
    signal: controller.signal,
    cancel: () => globalThis.clearTimeout(timer),
  };
};
