import { useEffect, useRef, useState } from "react";

export function usePoll<T>(fn: () => Promise<T>, ms: number, enabled: boolean) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const tickRef = useRef(0);

  useEffect(() => {
    if (!enabled) return;

    let mounted = true;
    let timer: number | undefined;

    async function run() {
      const myTick = ++tickRef.current;
      setLoading(true);
      try {
        const res = await fn();
        if (!mounted) return;
        // Prevent out-of-order overwrites:
        if (myTick === tickRef.current) setData(res);
        setError(null);
      } catch (e: any) {
        if (!mounted) return;
        setError(e);
      } finally {
        if (mounted) setLoading(false);
      }
      timer = window.setTimeout(run, ms);
    }

    run();

    return () => {
      mounted = false;
      if (timer) window.clearTimeout(timer);
    };
  }, [fn, ms, enabled]);

  return { data, error, loading };
}
