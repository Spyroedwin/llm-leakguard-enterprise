import { Badge } from "@/components/ui/badge";
import { getRuntimeMode } from "@/app/config/runtime";
import { useLeaderboard } from "../hooks/useLeaderboard";
import type { ThreatEntry } from "../types";

export default function ThreatLeaderboard() {
  const mode = getRuntimeMode();

  const { data, isLoading, isError, error } = useLeaderboard(10);

  const rows: ThreatEntry[] = data ?? [];

  if (isLoading && rows.length === 0) {
    return <div className="text-sm text-muted-foreground">Loading…</div>;
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4">
        <div className="text-sm font-medium text-destructive">
          {mode === "live" ? "Backend offline (LIVE mode)." : "Demo error."}
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          {String((error as Error)?.message ?? "Unknown error")}
        </div>
        <div className="mt-3 text-xs text-muted-foreground">
          Tip: switch to <span className="font-medium">DEMO</span> to keep the
          dashboard alive.
        </div>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">
        No threats logged yet.
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="grid grid-cols-2 border-b pb-2 text-sm font-medium">
        <div>Threat</div>
        <div className="text-right">Count</div>
      </div>

      <div className="divide-y">
        {rows.map((row) => (
          <div
            key={row.threat}
            className="grid grid-cols-2 items-center py-3 text-sm"
          >
            <div>
              <Badge variant="outline" className="rounded-full px-3">
                {row.threat}
              </Badge>
            </div>
            <div className="text-right font-semibold tabular-nums">
              {row.count}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
