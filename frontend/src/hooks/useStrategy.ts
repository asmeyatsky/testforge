import { useCallback, useState } from "react";
import { apiPost, apiGet } from "../api/client";
import type { StrategyDTO } from "../api/types";

export function useStrategy() {
  const [strategy, setStrategy] = useState<StrategyDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = useCallback(
    async (path = ".", layers?: string, prd?: string) => {
      setLoading(true);
      setError(null);
      try {
        const res = await apiPost<{ strategy: StrategyDTO }>("/api/strategy", {
          path,
          layers,
          prd,
        });
        setStrategy(res.strategy);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const refresh = useCallback(async () => {
    try {
      const res = await apiGet<{ strategy?: StrategyDTO; error?: string }>(
        "/api/strategy"
      );
      if (res.strategy) setStrategy(res.strategy);
    } catch {
      /* ignore */
    }
  }, []);

  return { strategy, loading, error, generate, refresh };
}
