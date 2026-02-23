import { useQuery } from "@tanstack/react-query";

export interface LogEntry {
  id: string;
  threat: string;
  action: "ALLOW" | "BLOCK" | "HONEY_POT_HIT";
  severity: number;
  timestamp: string;
  ip: string;
}

export function useLogs(limit = 50) {
  return useQuery<LogEntry[]>({
    queryKey: ["logs", limit],
    queryFn: async () => {
      const res = await fetch(`http://127.0.0.1:8000/logs?limit=${limit}`);
      if (!res.ok) throw new Error("Logs endpoint unreachable");
      return res.json();
    },
    refetchInterval: 3000,
    retry: 1,
  });
}
