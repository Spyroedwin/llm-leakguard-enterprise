import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { TopBar } from "@/features/controls/TopBar";
import ThreatLeaderboard from "@/features/leaderboard/components/ThreatLeaderboard";
import { AttackMap } from "@/features/map/AttackMap";
import LiveFeed from "@/features/feed/components/LiveFeed";

export default function Ops() {
  const [live, setLive] = useState(true);

  return (
    <div className="space-y-6">
      {/* Header + chips */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">
            LeakGuard <span className="text-muted-foreground">Ops</span>
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Live posture • detections • honeypot • response controls
          </p>
        </div>

        <div className="pt-2">
          <TopBar live={live} setLive={setLive} />
        </div>
      </div>

      <div className="h-px w-full bg-border" />

      {/* Main grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Threat Leaderboard</CardTitle>
              <p className="text-sm text-muted-foreground">
                Top detections aggregated from logs
              </p>
            </div>
            <span className="text-xs text-muted-foreground">
              {live ? "refresh: live" : "refresh: paused"}
            </span>
          </CardHeader>
          <CardContent>
            <ThreatLeaderboard live={live} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Attack Map</CardTitle>
              <p className="text-sm text-muted-foreground">
                GeoIP markers + TOR exits highlight
              </p>
            </div>
            <span className="text-xs text-muted-foreground">Leaflet</span>
          </CardHeader>
          <CardContent>
            <AttackMap live={live} />
          </CardContent>
        </Card>
      </div>

      {/* Feed */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Live Attack Feed</CardTitle>
            <p className="text-sm text-muted-foreground">
              Recent alerts, blocks, and honeypot hits (auto refresh)
            </p>
          </div>
        </CardHeader>
        <CardContent>
          <LiveFeed />
        </CardContent>
      </Card>

      <p className="text-center text-xs text-muted-foreground">
        SOC vibes engaged. Next we wire real stats and make the feed scroll like
        a villain monologue 😈
      </p>
    </div>
  );
}
