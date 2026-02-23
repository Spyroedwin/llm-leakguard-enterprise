import { useEffect, useMemo, useRef, useState } from "react";
import { apiGet } from "@/lib/api";

export type LogAction = "ALLOW" | "WARN" | "BLOCK";

export type LogItem = {
  timestamp?: string | number; // backend uses "timestamp"
  action?: string; // "ALLOWED" or maybe "ALLOW"/"BLOCK"
  type?: string; // e.g. "ALERT"
  subject?: string; // e.g. "🚨 ENTERPRISE THREAT BLOCKED"
  ip?: string;
  country?: string;
  tor?: boolean;
  risk_breakdown?: {
    phase1?: number;
    geo?: number;
    phase2_llm?: number;
    total?: number; // 0..1
  };
  phase1_threats?: string[];
  phase2_owasp?: string[];
  // ...any other fields in JSONL
};

export type RiskSummary = {
  blocks: number;
  warns: number;
  allows: number;
  total: number;
  riskScore: number; // 0..100
  avgTotalRisk?: number; // 0..1 (nice for debugging)
  lastSeenAt: number | null;
};

type Options = {
  limit?: number;
  path?: string; // default: /logs
  pollMs?: number;
  enabled?: boolean;
  isOnline?: boolean;
  weights?: Partial<Record<LogAction, number>>; // used when risk_breakdown.total missing
};

function toMs(ts: string | number | undefined): number | null {
  if (ts == null) return null;
  if (typeof ts === "number") return ts > 10_000_000_000 ? ts : ts * 1000;
  const d = Date.parse(ts);
  return Number.isFinite(d) ? d : null;
}

function normalizeAction(row: LogItem): LogAction {
  const a = (row.action ?? "").toUpperCase().trim();

  if (a === "BLOCK") return "BLOCK";
  if (a === "WARN") return "WARN";
  if (a === "ALLOW" || a === "ALLOWED") return "ALLOW";

  // If backend logs ALERT lines, treat them as BLOCK-ish for dashboard risk.
  if ((row.type ?? "").toUpperCase() === "ALERT") return "BLOCK";

  // Heuristic: blocked subject
  const subj = (row.subject ?? "").toUpperCase();
  if (subj.includes("BLOCK")) return "BLOCK";

  return "ALLOW";
}

export function useRiskSummary(opts: Options = {}) {
  const {
    limit = 200,
    path = "/logs",
    pollMs = 2500,
    enabled = true,
    isOnline = true,
    weights = { BLOCK: 1.0, WARN: 0.5, ALLOW: 0.1 },
  } = opts;

  const [logs, setLogs] = useState<LogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const acRef = useRef<AbortController | null>(null);

  async function fetchLogs() {
    if (!enabled || !isOnline) return;

    acRef.current?.abort();
    const ac = new AbortController();
    acRef.current = ac;

    setLoading(true);
    setError(null);

    try {
      const data = await apiGet<any>(
        `${path}?limit=${encodeURIComponent(limit)}`,
        ac.signal,
      );

      // Your endpoint returns a plain list.
      const arr: LogItem[] = Array.isArray(data) ? data : (data?.logs ?? []);
      setLogs(Array.isArray(arr) ? arr : []);
    } catch (e: any) {
      setError(e?.message ?? "Failed to fetch logs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!enabled || !isOnline) return;

    fetchLogs();
    const t = setInterval(fetchLogs, pollMs);
    return () => {
      clearInterval(t);
      acRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, isOnline, limit, path, pollMs]);

  const summary: RiskSummary = useMemo(() => {
    let blocks = 0,
      warns = 0,
      allows = 0;
    let lastSeenAt: number | null = null;

    let sumRisk01 = 0; // using risk_breakdown.total if present
    let sumWeighted = 0; // fallback
    let riskCount = 0;

    for (const row of logs) {
      const action = normalizeAction(row);

      if (action === "BLOCK") blocks++;
      else if (action === "WARN") warns++;
      else allows++;

      const t = toMs(row.timestamp);
      if (t != null)
        lastSeenAt = lastSeenAt == null ? t : Math.max(lastSeenAt, t);

      const total = row.risk_breakdown?.total;
      if (typeof total === "number" && Number.isFinite(total)) {
        sumRisk01 += Math.max(0, Math.min(1, total));
        riskCount++;
      } else {
        sumWeighted += weights[action] ?? 0;
        riskCount++;
      }
    }

    const totalRows = logs.length;
    const denom = riskCount || 1;

    // Prefer real combined risk if available, else fallback to action weights.
    const avg01 = logs.some((r) => typeof r.risk_breakdown?.total === "number")
      ? sumRisk01 / denom
      : sumWeighted / denom; // already 0..1-ish

    const riskScore = Math.max(0, Math.min(100, Math.round(avg01 * 100)));

    return {
      blocks,
      warns,
      allows,
      total: totalRows,
      riskScore,
      avgTotalRisk: avg01,
      lastSeenAt,
    };
  }, [logs, weights]);

  return { logs, summary, loading, error, refetch: fetchLogs };
}
