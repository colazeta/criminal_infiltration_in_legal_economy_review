"use strict";

const DEFAULT_UPSTREAM_TIMEOUT_MS = 5500;

async function fetchWithTimeout(input, init = {}, timeoutMs = DEFAULT_UPSTREAM_TIMEOUT_MS) {
  const controller = new AbortController();
  const parentSignal = init.signal;
  const abortFromParent = () => controller.abort(parentSignal?.reason || "upstream_aborted");
  if (parentSignal?.aborted) abortFromParent();
  else parentSignal?.addEventListener("abort", abortFromParent, { once: true });

  const timer = setTimeout(() => controller.abort("upstream_timeout"), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
    parentSignal?.removeEventListener("abort", abortFromParent);
  }
}

export { DEFAULT_UPSTREAM_TIMEOUT_MS, fetchWithTimeout };
