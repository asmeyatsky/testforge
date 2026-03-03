import { useState } from "react";
import { apiPost } from "../api/client";
import type { ExecutionResults } from "../api/types";

interface Props {
  seedData?: ExecutionResults | null;
}

export function ExecutePanel({ seedData }: Props) {
  const [testDir, setTestDir] = useState("tests");
  const [fetched, setFetched] = useState<ExecutionResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const results = fetched ?? seedData ?? null;

  async function handleExecute() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiPost<{ results: ExecutionResults }>("/api/execute", {
        test_dir: testDir,
      });
      setFetched(res.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  const badge = (outcome: string) => {
    const colors: Record<string, string> = {
      passed: "bg-green-100 text-green-800",
      failed: "bg-red-100 text-red-800",
      error: "bg-red-100 text-red-800",
      skipped: "bg-yellow-100 text-yellow-800",
    };
    return (
      <span
        className={`px-2 py-0.5 rounded text-xs font-medium ${colors[outcome] || "bg-gray-100 text-gray-800"}`}
      >
        {outcome.toUpperCase()}
      </span>
    );
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Execute Tests</h2>

      <div className="flex gap-2 mb-6">
        <input
          className="border rounded px-3 py-2 flex-1 text-sm"
          placeholder="Test directory"
          value={testDir}
          onChange={(e) => setTestDir(e.target.value)}
        />
        <button
          className="bg-green-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-green-700 disabled:opacity-50"
          onClick={handleExecute}
          disabled={loading}
        >
          {loading ? "Running..." : "Run Tests"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {results && (
        <div>
          <div className="grid grid-cols-5 gap-4 mb-6">
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Total</p>
              <p className="text-2xl font-bold">{results.total}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Passed</p>
              <p className="text-2xl font-bold text-green-600">{results.passed}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Failed</p>
              <p className="text-2xl font-bold text-red-600">{results.failed}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Errors</p>
              <p className="text-2xl font-bold text-red-600">{results.errors}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Success Rate</p>
              <p className="text-2xl font-bold">
                {(results.success_rate * 100).toFixed(0)}%
              </p>
            </div>
          </div>

          <div className="bg-white border rounded-lg">
            <div className="px-4 py-3 border-b bg-gray-50">
              <h3 className="font-semibold text-sm">
                Test Results ({results.tests.length})
              </h3>
            </div>
            <div className="overflow-auto max-h-96">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50 text-left">
                    <th className="px-4 py-2">Test</th>
                    <th className="px-4 py-2">Status</th>
                    <th className="px-4 py-2 text-right">Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {results.tests.map((t) => (
                    <tr key={t.name} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-xs">{t.name}</td>
                      <td className="px-4 py-2">{badge(t.outcome)}</td>
                      <td className="px-4 py-2 text-right text-xs">
                        {t.duration != null ? `${t.duration.toFixed(2)}s` : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
