import { Badge } from "@/components/ui/badge";
import { useLogs } from "../hooks/useLogs";

function pickThreat(log: any) {
  const p1 = Array.isArray(log?.phase1_threats) ? log.phase1_threats : [];
  const p2 = Array.isArray(log?.phase2_owasp) ? log.phase2_owasp : [];

  // Honeypot entries might have "path"
  if (log?.action === "HONEYPOT" && log?.path) return `honeypot:${log.path}`;

  return (p1[0] || p2[0] || log?.subject || "unknown") as string;
}

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
    <div className="max-h-72 overflow-y-auto space-y-2 pr-2">
      {data.map((log: any, idx: number) => {
        const action = (log?.action || "INFO") as string;
        const ip = (log?.ip || "unknown") as string;
        const threat = pickThreat(log);
        const ts = log?.timestamp || log?.ts || new Date().toISOString();

        return (
          <div
            key={`${ts}-${ip}-${idx}`}
            className="flex items-center justify-between rounded-lg border bg-muted/20 px-3 py-2 text-xs"
          >
            <div className="flex items-center gap-3 min-w-0">
              <Badge
                variant={
                  action === "BLOCK"
                    ? "destructive"
                    : action === "HONEYPOT"
                      ? "secondary"
                      : "outline"
                }
                className="rounded-full px-2"
              >
                {action}
              </Badge>

              <span className="font-medium truncate">{threat}</span>
              <span className="text-muted-foreground truncate">{ip}</span>
            </div>

            <span className="text-muted-foreground shrink-0">
              {new Date(ts).toLocaleTimeString()}
            </span>
          </div>
        );
      })}
    </div>
  );
}
