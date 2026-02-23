import React, { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import ThreatLeaderboard from "@/features/leaderboard/components/ThreatLeaderboard";
import LiveFeed from "@/features/feed/components/LiveFeed";
import { useHealth } from "@/features/system/hooks/useHealth";
import { useLogs } from "@/features/feed/hooks/useLogs";

import ThemeToggle from "@/components/ThemeToggle";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

/**
 * Runtime mode: LIVE hits backend, DEMO can use mocked data (your hooks/components decide).
 * Stored so refresh keeps the mode.
 */
type RuntimeMode = "live" | "demo";
const MODE_KEY = "leakguard:mode";

function getRuntimeMode(): RuntimeMode {
  const raw = localStorage.getItem(MODE_KEY);
  return raw === "demo" ? "demo" : "live";
}

function setRuntimeMode(mode: RuntimeMode) {
  localStorage.setItem(MODE_KEY, mode);
  window.dispatchEvent(new Event("leakguard:mode"));
}

function StatChip({
  label,
  value,
  variant = "outline",
}: {
  label: string;
  value: string;
  variant?: "outline" | "secondary" | "destructive";
}) {
  return (
    <div className="flex items-center gap-2 rounded-full border bg-background/80 px-3 py-1 text-xs shadow-sm backdrop-blur">
      <span className="text-muted-foreground">{label}</span>
      <Badge variant={variant} className="rounded-full px-2 py-0.5">
        {value}
      </Badge>
    </div>
  );
}

export default function DashboardPage() {
  const qc = useQueryClient();

  const [mode, setMode] = useState<RuntimeMode>(() => getRuntimeMode());

  useEffect(() => {
    const onMode = () => setMode(getRuntimeMode());
    window.addEventListener("leakguard:mode", onMode);
    return () => window.removeEventListener("leakguard:mode", onMode);
  }, []);

  function toggleMode() {
    const next: RuntimeMode = mode === "live" ? "demo" : "live";
    setRuntimeMode(next);
    setMode(next);

    // refresh everything immediately (leaderboard/feed/map later)
    qc.invalidateQueries();
  }

  // ===========================
  // LIVE BACKEND DATA (Phase 1)
  // ===========================
  const isLive = mode === "live";

  // Only query backend in LIVE mode. In DEMO mode we keep stable placeholders.
  const { data: health } = useHealth();
  const { data: logs } = useLogs(100);

  // header chips
  const port = "8000";

  const status = useMemo(() => {
    if (!isLive) return "DEMO";
    return health?.status ?? "OFFLINE";
  }, [isLive, health?.status]);

  const risk = useMemo(() => {
    if (!isLive) return "0.00";
    const r = health?.risk_score;
    return typeof r === "number" ? r.toFixed(2) : "0.00";
  }, [isLive, health?.risk_score]);

  const blocks = useMemo(() => {
    if (!isLive) return "0";
    if (!logs) return "0";
    return logs.filter((l) => l.action === "BLOCK").length.toString();
  }, [isLive, logs]);

  const statusVariant: "secondary" | "destructive" | "outline" = useMemo(() => {
    if (!isLive) return "outline";
    return status.toLowerCase().includes("healthy") ||
      status.toLowerCase() === "ok"
      ? "secondary"
      : "destructive";
  }, [isLive, status]);

  return (
    <div className="min-h-screen bg-background">
      {/* subtle background vibe */}
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,hsl(var(--foreground)/0.06),transparent_45%),radial-gradient(circle_at_80%_0%,hsl(var(--foreground)/0.05),transparent_40%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,hsl(var(--border))_1px,transparent_1px),linear-gradient(to_bottom,hsl(var(--border))_1px,transparent_1px)] bg-size-[48px_48px] opacity-[0.25]" />
      </div>

      <div className="mx-auto w-full max-w-6xl px-4 py-6 md:px-6">
        {/* Sticky Header */}
        <div className="-mx-4 sticky top-0 z-20 bg-background/80 px-4 py-4 backdrop-blur md:-mx-6 md:px-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <h1 className="text-4xl font-bold tracking-tight md:text-5xl">
                LeakGuard <span className="text-muted-foreground">Ops</span>
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Live posture • detections • honeypot • response controls
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 md:justify-end">
              <StatChip label="Port" value={port} />
              <StatChip label="Status" value={status} variant={statusVariant} />
              <StatChip label="Risk" value={risk} />
              <StatChip label="Blocks" value={blocks} variant="destructive" />

              <Button
                variant="outline"
                className="rounded-full bg-background/80 shadow-sm backdrop-blur"
                onClick={toggleMode}
                title="Toggle LIVE/DEMO"
              >
                {mode === "live" ? "🛰️ Live" : "🧪 Demo"}
              </Button>

              <ThemeToggle />
            </div>
          </div>

          <Separator className="mt-5" />
        </div>

        {/* Content */}
        <div className="pt-6">
          <div className="grid gap-6 md:grid-cols-2">
            {/* Threat Leaderboard */}
            <Card className="border shadow-sm transition hover:shadow-md">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <CardTitle className="text-base">
                      Threat Leaderboard
                    </CardTitle>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Top detections aggregated from logs
                    </p>
                  </div>

                  <Badge variant="outline" className="rounded-full">
                    refresh: live
                  </Badge>
                </div>
              </CardHeader>

              <CardContent>
                <ThreatLeaderboard />
                <p className="mt-3 text-[11px] text-muted-foreground">
                  Tip: trigger detections via{" "}
                  <span className="font-medium">/chat</span> and watch this
                  update.
                </p>
              </CardContent>
            </Card>

            {/* Attack Map */}
            <Card className="border shadow-sm transition hover:shadow-md">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <CardTitle className="text-base">Attack Map</CardTitle>
                    <p className="mt-1 text-xs text-muted-foreground">
                      GeoIP markers + TOR exits highlight
                    </p>
                  </div>

                  <Badge variant="outline" className="rounded-full">
                    Leaflet next
                  </Badge>
                </div>
              </CardHeader>

              <CardContent>
                <div className="grid h-55 place-items-center rounded-xl border border-dashed bg-muted/20">
                  <div className="text-center">
                    <div className="text-sm font-medium">Map Loading…</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      Waiting for markers + tiles
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Live Attack Feed */}
            <Card className="border shadow-sm transition hover:shadow-md md:col-span-2">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <CardTitle className="text-base">
                      Live Attack Feed
                    </CardTitle>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Recent alerts, blocks, and honeypot hits (auto refresh)
                    </p>
                  </div>

                  <Badge variant="outline" className="rounded-full">
                    /logs
                  </Badge>
                </div>
              </CardHeader>

              <CardContent>
                <LiveFeed />
              </CardContent>
            </Card>
          </div>

          {/* Footer */}
          <div className="mt-8 text-center text-xs text-muted-foreground">
            SOC vibes engaged. Next we wire real stats and make the feed scroll
            like a villain monologue 😈
          </div>
        </div>
      </div>
    </div>
  );
}
