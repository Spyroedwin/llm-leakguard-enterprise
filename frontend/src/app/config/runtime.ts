// src/app/config/runtime.ts

export type RuntimeMode = "demo" | "live";

const MODE_KEY = "leakguard:mode";
const DEFAULT_MODE: RuntimeMode = "demo";

// change if your backend host changes
const LIVE_BASE_URL = "http://127.0.0.1:8000";

export function getRuntimeMode(): RuntimeMode {
  const v = localStorage.getItem(MODE_KEY);
  return v === "live" || v === "demo" ? v : DEFAULT_MODE;
}

export function setRuntimeMode(mode: RuntimeMode) {
  localStorage.setItem(MODE_KEY, mode);
  // let anyone listening refresh without prop-drilling
  window.dispatchEvent(new Event("leakguard:mode"));
}

export function toggleRuntimeMode(): RuntimeMode {
  const next: RuntimeMode = getRuntimeMode() === "live" ? "demo" : "live";
  setRuntimeMode(next);
  return next;
}

export function getApiBaseUrl(mode: RuntimeMode = getRuntimeMode()) {
  return mode === "live" ? LIVE_BASE_URL : "demo://local";
}
