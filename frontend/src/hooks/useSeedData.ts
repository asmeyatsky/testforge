import { useCallback, useState } from "react";
import { apiPost } from "../api/client";
import { showToast } from "../components/Toast";
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

  const seed = useCallback(async (target: string) => {
    setLoading(true);
    try {
      // Set the target (local path or GitHub URL)
      setStep("Setting target...");
      const targetRes = await apiPost<{ path?: string; error?: string }>(
        "/api/settings/target",
        { path: target }
      );
      if (targetRes.error) {
        showToast(targetRes.error, "error");
        setLoading(false);
        setStep("");
        return;
      }

      setStep("Analysing codebase...");
      const a = await apiPost<{ analysis: AnalysisDTO }>("/api/analyse", {
        path: targetRes.path,
      });
      showToast(
        `Analysis done — ${a.analysis.total_modules} modules, ${a.analysis.total_functions} functions`,
        "success"
      );

      setStep("Generating strategy...");
      const s = await apiPost<{ strategy: StrategyDTO }>("/api/strategy", {
        path: targetRes.path,
        layers: "unit,integration",
      });
      showToast(
        `Strategy done — ${s.strategy.total_test_cases} test cases`,
        "success"
      );

      setStep("Finding gaps...");
      const g = await apiPost<{ gaps: GapsReport }>("/api/gaps", {
        path: targetRes.path,
      });

      setStep("Validating tests...");
      const v = await apiPost<{ validation: ValidationReport }>(
        "/api/validate",
        { test_dir: targetRes.path + "/tests" }
      );

      setData({
        analysis: a.analysis,
        strategy: s.strategy,
        execution: null,
        gaps: g.gaps,
        validation: v.validation,
      });
      setStep("");
      showToast("All data loaded!", "success");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      showToast(`Error: ${msg}`, "error");
      setStep("");
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, step, seed };
}
