import { Badge } from "@/components/ui/badge";
import { useLogs } from "../hooks/useLogs";

export default function LiveFeed() {
  const { data, isLoading, isError } = useLogs(50);

  if (isLoading) {
    return <div className="text-sm text-muted-foreground">Loading feed…</div>;
  }

  if (isError) {
    return (
      <div className="text-sm text-destructive">
        Feed offline. Backend not responding.
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">No activity yet.</div>
    );
  }

  return (
    <div className="max-h-70 overflow-y-auto space-y-2 pr-2">
      {data.map((log: any, idx: number) => {
        const key = `${log.timestamp ?? log.ts ?? "notime"}-${log.ip ?? "noip"}-${idx}`;

        return (
          <div
            key={key}
            className="flex items-center justify-between rounded-lg border bg-muted/20 px-3 py-2 text-xs"
          >
            <div className="flex items-center gap-3">
              <Badge
                variant={
                  log.action === "BLOCK"
                    ? "destructive"
                    : log.action === "HONEY_POT_HIT"
                      ? "secondary"
                      : "outline"
                }
                className="rounded-full px-2"
              >
                {log.action ?? "INFO"}
              </Badge>

              <span className="font-medium">{log.threat ?? "unknown"}</span>
              <span className="text-muted-foreground">
                {log.ip ?? "unknown"}
              </span>
            </div>

            <span className="text-muted-foreground">
              {log.timestamp
                ? new Date(log.timestamp).toLocaleTimeString()
                : log.ts
                  ? new Date(log.ts).toLocaleTimeString()
                  : ""}
            </span>
          </div>
        );
      })}
    </div>
  );
}
