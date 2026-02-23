import { useEffect, useRef, useState } from "react";
import { apiGet } from "@/lib/api";

export type HealthState = {
  ok: boolean;
  status: "HEALTHY" | "OFFLINE" | "DEGRADED";
  lastOkAt: number | null;
  lastError?: string;
  retryInMs?: number;
};

type Options = {
  path?: string; // default: /health
  baseIntervalMs?: number; // default: 1000
  maxIntervalMs?: number; // default: 8000
  timeoutMs?: number; // default: 2500
  enabled?: boolean; // default: true
};

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export function useHealth(options: Options = {}) {
  const {
    path = "/health",
    baseIntervalMs = 1000,
    maxIntervalMs = 8000,
    timeoutMs = 2500,
    enabled = true,
  } = options;

  const [state, setState] = useState<HealthState>({
    ok: false,
    status: "OFFLINE",
    lastOkAt: null,
  });

  const stopRef = useRef(false);
  const backoffRef = useRef(baseIntervalMs);

  useEffect(() => {
    if (!enabled) return;

    stopRef.current = false;
    backoffRef.current = baseIntervalMs;

    async function loop() {
      while (!stopRef.current) {
        const ac = new AbortController();
        const timeout = setTimeout(() => ac.abort(), timeoutMs);

        try {
          // Your backend may return { ok: true } or any JSON.
          // We treat "fetch + 2xx" as healthy.
          await apiGet<any>(path, ac.signal);

          clearTimeout(timeout);
          backoffRef.current = baseIntervalMs;

          setState((prev) => ({
            ok: true,
            status: "HEALTHY",
            lastOkAt: Date.now(),
            lastError: undefined,
            retryInMs: undefined,
          }));

          // Healthy polling: keep it snappy (base interval)
          await sleep(baseIntervalMs);
        } catch (err: any) {
          clearTimeout(timeout);

          const wait = Math.min(backoffRef.current, maxIntervalMs);
          backoffRef.current = Math.min(backoffRef.current * 2, maxIntervalMs);

          setState((prev) => ({
            ok: false,
            status: prev.lastOkAt ? "DEGRADED" : "OFFLINE",
            lastOkAt: prev.lastOkAt,
            lastError: err?.message ?? "Health check failed",
            retryInMs: wait,
          }));

          await sleep(wait);
        }
      }
    }

    loop();

    return () => {
      stopRef.current = true;
    };
  }, [enabled, path, baseIntervalMs, maxIntervalMs, timeoutMs]);

  return state;
}
