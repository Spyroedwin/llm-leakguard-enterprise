// src/features/leaderboard/hooks/useLeaderboard.ts
import { useQuery } from "@tanstack/react-query";
import { fetchThreatLeaderboard } from "../api/leaderboard.api";
import type { ThreatEntry } from "../types";
import { getRuntimeMode } from "@/app/config/runtime";

export function useLeaderboard(limit = 10) {
  const mode = getRuntimeMode();

  return useQuery<ThreatEntry[]>({
    queryKey: ["leaderboard", mode, limit],
    queryFn: () => fetchThreatLeaderboard(limit),
    refetchInterval: mode === "demo" ? 2500 : 5000,
    placeholderData: (prev) => prev,
  });
}
