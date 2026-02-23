// src/features/leaderboard/api/leaderboard.api.ts
import type { ThreatEntry } from "../types";
import { getRuntimeMode } from "@/app/config/runtime";

const DEMO_DATA: ThreatEntry[] = [
  { threat: "brute_force", count: 7 },
  { threat: "sql_injection", count: 3 },
  { threat: "LLM01_PromptInjection", count: 2 },
  { threat: "tor_c2", count: 1 },
];

export async function fetchThreatLeaderboard(
  limit = 10,
): Promise<ThreatEntry[]> {
  const mode = getRuntimeMode();

  // Demo mode: always return data, always looks alive
  if (mode === "demo") {
    // pretend it’s “live” by slightly randomizing counts
    return DEMO_DATA.slice(0, limit).map((x) => ({
      ...x,
      count: Math.max(1, x.count + Math.floor(Math.random() * 3) - 1),
    }));
  }

  // Live mode: hit backend
  const url = `http://127.0.0.1:8000/threat-leaderboard?limit=${limit}`;
  const res = await fetch(url);

  if (!res.ok) {
    throw new Error(`Backend error (${res.status})`);
  }

  // backend returns: [ [ "brute_force", 4 ], ...]
  const raw: [string, number][] = await res.json();
  return raw.map(([threat, count]) => ({ threat, count }));
}
