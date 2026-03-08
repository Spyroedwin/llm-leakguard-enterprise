import { Badge } from "@/components/ui/badge";
import { getRuntimeMode } from "@/app/config/runtime";
import { useLeaderboard } from "../hooks/useLeaderboard"; // Assumes this uses usePoll internally
import type { ThreatEntry } from "../types";

interface ThreatLeaderboardProps {
  live?: boolean;
}

export default function ThreatLeaderboard({
  live = false,
}: ThreatLeaderboardProps) {
  const mode = getRuntimeMode();

  // Using the more robust hook from your second snippet
  // If useLeaderboard doesn't accept 'live', you might need to update
  // that hook's definition to handle the polling toggle.
  const { data, isLoading, isError, error } = useLeaderboard(10);

  const rows: ThreatEntry[] = data ?? [];

  // 1. Loading State
  if (isLoading && rows.length === 0) {
    return (
      <div className="text-sm text-muted-foreground animate-pulse">
        Loading threats...
      </div>
    );
  }

  // 2. Error State (Enhanced with the "Tip" from your original)
  if (isError) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4">
        <div className="text-sm font-medium text-destructive">
          {mode === "live" || live
            ? "Backend offline (LIVE mode)."
            : "Demo error."}
        </div>
        <div className="mt-1 text-xs text-muted-foreground">
          {String((error as Error)?.message ?? "Unknown error")}
        </div>
        <div className="mt-3 text-xs text-muted-foreground">
          Tip: switch to{" "}
          <span className="font-medium text-foreground">DEMO</span> to keep the
          dashboard alive.
        </div>
      </div>
    );
  }

  // 3. Empty State (Combined the "Poke /chat" wit and the cleaner UI)
  if (rows.length === 0) {
    return (
      <div className="text-sm text-muted-foreground italic">
        No detections yet. Poke /chat 😼
      </div>
    );
  }

  // 4. Main Render (Table Layout)
  return (
    <div className="w-full space-y-1">
      <div className="grid grid-cols-2 border-b pb-2 text-sm font-medium text-muted-foreground">
        <div>Threat</div>
        <div className="text-right">Count</div>
      </div>

      <div className="divide-y">
        {rows.map((row) => (
          <div
            key={row.threat}
            className="grid grid-cols-2 items-center py-3 text-sm transition-colors hover:bg-muted/50"
          >
            <div>
              <Badge
                variant="outline"
                className="rounded-full px-3 font-normal"
              >
                {row.threat}
              </Badge>
            </div>
            <div className="text-right font-semibold tabular-nums">
              {row.count.toLocaleString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
