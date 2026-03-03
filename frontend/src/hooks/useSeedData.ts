import { useCallback, useState } from "react";
import { apiPost } from "../api/client";
import type {
  AnalysisDTO,
  StrategyDTO,
  ExecutionResults,
  GapsReport,
  ValidationReport,
} from "../api/types";

export interface SeedData {
  analysis: AnalysisDTO | null;
  strategy: StrategyDTO | null;
  execution: ExecutionResults | null;
  gaps: GapsReport | null;
  validation: ValidationReport | null;
}

export function useSeedData() {
  const [data, setData] = useState<SeedData>({
    analysis: null,
    strategy: null,
    execution: null,
    gaps: null,
    validation: null,
  });
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState("");

  const seed = useCallback(async () => {
    setLoading(true);
    try {
      setStep("Analysing codebase...");
      const a = await apiPost<{ analysis: AnalysisDTO }>("/api/analyse", {
        path: ".",
      });

      setStep("Generating strategy...");
      const s = await apiPost<{ strategy: StrategyDTO }>("/api/strategy", {
        path: ".",
        layers: "unit,integration",
      });

      setStep("Running tests...");
      const e = await apiPost<{ results: ExecutionResults }>("/api/execute", {
        test_dir: "tests",
      });

      setStep("Finding gaps...");
      const g = await apiPost<{ gaps: GapsReport }>("/api/gaps", {
        path: ".",
        test_dir: "tests",
      });

      setStep("Validating tests...");
      const v = await apiPost<{ validation: ValidationReport }>(
        "/api/validate",
        { test_dir: "tests" }
      );

      setData({
        analysis: a.analysis,
        strategy: s.strategy,
        execution: e.results,
        gaps: g.gaps,
        validation: v.validation,
      });
      setStep("");
    } catch {
      setStep("Error seeding data");
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, step, seed };
}
