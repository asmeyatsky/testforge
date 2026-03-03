import { useState } from "react";
import { apiPost } from "../api/client";
import type { GapsReport } from "../api/types";

export function GapsPanel() {
  const [path, setPath] = useState(".");
  const [testDir, setTestDir] = useState("");
  const [report, setReport] = useState<GapsReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyse() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiPost<{ gaps: GapsReport }>("/api/gaps", {
        path,
        test_dir: testDir || undefined,
      });
      setReport(res.gaps);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Coverage Gaps</h2>

      <div className="flex gap-2 mb-6">
        <input
          className="border rounded px-3 py-2 flex-1 text-sm"
          placeholder="Source path"
          value={path}
          onChange={(e) => setPath(e.target.value)}
        />
        <input
          className="border rounded px-3 py-2 flex-1 text-sm"
          placeholder="Test directory (optional)"
          value={testDir}
          onChange={(e) => setTestDir(e.target.value)}
        />
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          onClick={handleAnalyse}
          disabled={loading}
        >
          {loading ? "Analysing..." : "Find Gaps"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {report && (
        <div>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Coverage</p>
              <p className="text-2xl font-bold">{report.coverage_percent.toFixed(0)}%</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Tested</p>
              <p className="text-2xl font-bold text-green-600">{report.tested}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Untested</p>
              <p className="text-2xl font-bold text-red-600">{report.untested_count}</p>
            </div>
          </div>

          {report.modules.length > 0 && (
            <div className="bg-white border rounded-lg">
              <div className="px-4 py-3 border-b bg-gray-50">
                <h3 className="font-semibold text-sm">Modules with Gaps</h3>
              </div>
              <div className="overflow-auto max-h-96">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50 text-left">
                      <th className="px-4 py-2">Module</th>
                      <th className="px-4 py-2">Untested Functions</th>
                      <th className="px-4 py-2 text-right">Tested</th>
                      <th className="px-4 py-2 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.modules.map((m) => (
                      <tr key={m.file_path} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-2 font-mono text-xs">{m.file_path}</td>
                        <td className="px-4 py-2 text-xs text-red-600">
                          {m.untested.slice(0, 5).join(", ")}
                          {m.untested.length > 5 && ` +${m.untested.length - 5}`}
                        </td>
                        <td className="px-4 py-2 text-right">{m.tested_count}</td>
                        <td className="px-4 py-2 text-right">{m.total_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
