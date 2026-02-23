import { useQuery } from "@tanstack/react-query";

export interface HealthResponse {
  status: string;
  risk_score: number;
}

export function useHealth() {
  return useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("http://127.0.0.1:8000/health");
      if (!res.ok) throw new Error("Health endpoint unreachable");
      return res.json();
    },
    refetchInterval: 5000,
    retry: 1,
  });
}
