// src/lib/api.ts
export const API_BASE =
  import.meta.env.VITE_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export type Health = {
  ok: boolean;
  engine_version?: string;
  policy_mode?: string;
};

export type ThreatRow = { threat: string; count: number };

export type FeedItem = {
  ts: string; // ISO
  type: "ALERT" | "BLOCK" | "HONEYPOT" | "INFO";
  threat?: string;
  ip?: string;
  country?: string;
  city?: string;
  risk?: number;
  message: string;
};

export type Marker = {
  lat: number;
  lng: number;
  label?: string; // ip/country
  tor?: boolean;
  threat?: string;
  risk?: number;
  ts?: string;
};

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  health: () => j<Health>("/health"),
  summary: () =>
    j<{ risk: number; blocks: number; status: "ONLINE" | "OFFLINE" }>(
      "/ops/summary",
    ),
  threats: () => j<ThreatRow[]>("/ops/threats"),
  feed: () => j<any[]>("/logs?limit=50"),
  markers: () => j<Marker[]>("/geo?limit=200"), // TEMP guess
  logs: () => j<string>("/ops/logs?tail=400"), // can be plain text too; adjust if JSON
};
