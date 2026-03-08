import { api } from "@/lib/api";
import { usePoll } from "@/hooks/usePoll";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type Props = {
  live: boolean;
  setLive: (v: boolean) => void;
};

export function TopBar({ live, setLive }: Props) {
  const summaryPoll = usePoll(api.summary, 1500, live);
  const healthPoll = usePoll(api.health, 5000, live);

  const status = summaryPoll.error
    ? "OFFLINE"
    : (summaryPoll.data?.status ?? "OFFLINE");

  const risk = summaryPoll.data?.risk ?? 0;
  const blocks = summaryPoll.data?.blocks ?? 0;

  const statusVariant = status === "ONLINE" ? "default" : "destructive";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Badge variant="outline" className="rounded-full px-3 py-1">
        Port <span className="ml-2 font-semibold">8000</span>
      </Badge>

      <Badge variant={statusVariant} className="rounded-full px-3 py-1">
        Status <span className="ml-2 font-semibold">{status}</span>
      </Badge>

      <Badge variant="outline" className="rounded-full px-3 py-1">
        Risk <span className="ml-2 font-semibold">{risk.toFixed(2)}</span>
      </Badge>

      <Badge variant="outline" className="rounded-full px-3 py-1">
        Blocks <span className="ml-2 font-semibold">{blocks}</span>
      </Badge>

      <Button
        variant={live ? "default" : "outline"}
        className="rounded-full"
        onClick={() => setLive(!live)}
      >
        {live ? "Live" : "Paused"}
      </Button>

      <div className="ml-auto text-xs text-muted-foreground">
        {healthPoll.data?.engine_version
          ? `engine ${healthPoll.data.engine_version}`
          : ""}
        {healthPoll.data?.policy_mode
          ? ` • ${healthPoll.data.policy_mode}`
          : ""}
      </div>
    </div>
  );
}
