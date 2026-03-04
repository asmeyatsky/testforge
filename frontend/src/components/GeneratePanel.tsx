import { useState } from "react";
import { apiPost } from "../api/client";
import { showToast } from "./Toast";
import type { GeneratedSuite } from "../api/types";

export function GeneratePanel() {
  const [layers, setLayers] = useState("");
  const [outputDir, setOutputDir] = useState(".testforge_output");
  const [suites, setSuites] = useState<GeneratedSuite[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiPost<{
        suites?: GeneratedSuite[];
        error?: string;
      }>("/api/generate", {
        layers: layers || undefined,
        output_dir: outputDir,
      });
      if (res.error) {
        setError(res.error);
      } else {
        setSuites(res.suites || []);
        const total = (res.suites || []).reduce((n, s) => n + s.size, 0);
        showToast(`Generated ${total} test files to ${outputDir}`, "success");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-1">Generate Tests</h2>
      <p className="text-sm text-gray-500 mb-4">
        Creates actual test files from the strategy plan. Requires a strategy to
        be generated first (via the <strong>Strategy</strong> tab or{" "}
        <strong>Load & Analyse</strong>). Files are written to the output
        directory below.
      </p>

      <div className="space-y-3 mb-6">
        <input
          className="border rounded px-3 py-2 w-full text-sm"
          placeholder="Layers (leave blank for strategy defaults)"
          value={layers}
          onChange={(e) => setLayers(e.target.value)}
        />
        <div>
          <input
            className="border rounded px-3 py-2 w-full text-sm"
            placeholder="Output directory"
            value={outputDir}
            onChange={(e) => setOutputDir(e.target.value)}
          />
          <p className="text-xs text-gray-400 mt-1">
            Generated test files will be written to this directory
          </p>
        </div>
        <button
          className="bg-green-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-green-700 disabled:opacity-50"
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? "Generating..." : "Generate Tests"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {suites.length > 0 && (
        <div className="bg-white border rounded-lg">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h3 className="font-semibold text-sm">Generated Suites</h3>
          </div>
          <div className="divide-y">
            {suites.map((s) => (
              <div
                key={s.layer}
                className="px-4 py-3 flex justify-between items-center"
              >
                <div>
                  <span className="font-medium">{s.layer.toUpperCase()}</span>
                  <span className="text-gray-500 text-sm ml-2">
                    {s.size} test{s.size !== 1 ? "s" : ""}
                  </span>
                </div>
                <span className="text-xs font-mono text-gray-400">
                  {s.output_dir}
                </span>
              </div>
            ))}
          </div>
          <div className="px-4 py-3 border-t bg-blue-50 text-sm text-blue-700">
            Tests written to <code className="font-mono">{outputDir}</code>.
            Go to <strong>Execute</strong> to run them.
          </div>
        </div>
      )}
    </div>
  );
}
