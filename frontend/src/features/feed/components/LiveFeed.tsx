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
    <div className="h-55 overflow-y-auto space-y-2 pr-2">
      {data.map((log) => (
        <div
          key={log.id}
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
              {log.action}
            </Badge>

            <span className="font-medium">{log.threat}</span>
            <span className="text-muted-foreground">{log.ip}</span>
          </div>

          <span className="text-muted-foreground">
            {new Date(log.timestamp).toLocaleTimeString()}
          </span>
        </div>
      ))}
    </div>
  );
}
