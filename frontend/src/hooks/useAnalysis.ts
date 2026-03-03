import { useCallback, useState } from "react";
import { apiPost, apiGet } from "../api/client";
import type { AnalysisDTO } from "../api/types";

export function useAnalysis() {
  const [analysis, setAnalysis] = useState<AnalysisDTO | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyse = useCallback(async (path = ".") => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiPost<{ analysis: AnalysisDTO }>("/api/analyse", {
        path,
      });
      setAnalysis(res.analysis);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const res = await apiGet<{ analysis?: AnalysisDTO; error?: string }>(
        "/api/analysis"
      );
      if (res.analysis) setAnalysis(res.analysis);
    } catch {
      /* ignore */
    }
  }, []);

  return { analysis, loading, error, analyse, refresh };
}
