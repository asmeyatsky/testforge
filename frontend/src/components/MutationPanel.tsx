import { useState } from "react";
import { apiPost } from "../api/client";
import type { MutationReport } from "../api/types";

export function MutationPanel() {
  const [source, setSource] = useState(".");
  const [testDir, setTestDir] = useState("tests");
  const [report, setReport] = useState<MutationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleMutate() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiPost<{ mutation?: MutationReport; error?: string }>(
        "/api/mutate",
        { source, test_dir: testDir }
      );
      if (res.error) {
        setError(res.error);
      } else if (res.mutation) {
        setReport(res.mutation);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Mutation Testing</h2>

      <div className="flex gap-2 mb-6">
        <input
          className="border rounded px-3 py-2 flex-1 text-sm"
          placeholder="Source directory"
          value={source}
          onChange={(e) => setSource(e.target.value)}
        />
        <input
          className="border rounded px-3 py-2 flex-1 text-sm"
          placeholder="Test directory"
          value={testDir}
          onChange={(e) => setTestDir(e.target.value)}
        />
        <button
          className="bg-purple-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
          onClick={handleMutate}
          disabled={loading}
        >
          {loading ? "Running..." : "Run Mutations"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {report && (
        <div>
          <div className="grid grid-cols-5 gap-4 mb-6">
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Score</p>
              <p className="text-2xl font-bold">{report.mutation_score.toFixed(1)}%</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Total</p>
              <p className="text-2xl font-bold">{report.total}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Killed</p>
              <p className="text-2xl font-bold text-green-600">{report.killed}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Survived</p>
              <p className="text-2xl font-bold text-red-600">{report.survived}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Timeout</p>
              <p className="text-2xl font-bold text-yellow-600">{report.timeout}</p>
            </div>
          </div>

          {report.survivors.length > 0 && (
            <div className="bg-white border rounded-lg">
              <div className="px-4 py-3 border-b bg-gray-50">
                <h3 className="font-semibold text-sm">Surviving Mutants</h3>
              </div>
              <div className="divide-y">
                {report.survivors.map((s) => (
                  <div key={s.id} className="px-4 py-3 flex items-center gap-3">
                    <span className="text-xs text-gray-400">#{s.id}</span>
                    <span className="font-mono text-xs">{s.source_file}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
