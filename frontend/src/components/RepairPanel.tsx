import { useState } from "react";
import { apiPost } from "../api/client";
import type { RepairReport } from "../api/types";

export function RepairPanel() {
  const [testDir, setTestDir] = useState(".testforge_output");
  const [maxAttempts, setMaxAttempts] = useState(3);
  const [report, setReport] = useState<RepairReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRepair() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiPost<{ repair?: RepairReport; error?: string }>(
        "/api/repair",
        { test_dir: testDir, max_attempts: maxAttempts }
      );
      if (res.error) {
        setError(res.error);
      } else if (res.repair) {
        setReport(res.repair);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Auto-Repair Tests</h2>

      <div className="flex gap-2 mb-6">
        <input
          className="border rounded px-3 py-2 flex-1 text-sm"
          placeholder="Test directory"
          value={testDir}
          onChange={(e) => setTestDir(e.target.value)}
        />
        <input
          className="border rounded px-3 py-2 w-24 text-sm"
          type="number"
          min={1}
          max={10}
          value={maxAttempts}
          onChange={(e) => setMaxAttempts(Number(e.target.value))}
        />
        <button
          className="bg-orange-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-orange-700 disabled:opacity-50"
          onClick={handleRepair}
          disabled={loading}
        >
          {loading ? "Repairing..." : "Repair"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {report && (
        <div>
          {report.message ? (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded text-sm">
              {report.message}
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-white border rounded-lg p-4">
                  <p className="text-sm text-gray-500">Fixed</p>
                  <p className="text-2xl font-bold text-green-600">{report.fixed}</p>
                </div>
                <div className="bg-white border rounded-lg p-4">
                  <p className="text-sm text-gray-500">Total</p>
                  <p className="text-2xl font-bold">{report.total}</p>
                </div>
              </div>

              <div className="bg-white border rounded-lg">
                <div className="px-4 py-3 border-b bg-gray-50">
                  <h3 className="font-semibold text-sm">Repair Results</h3>
                </div>
                <div className="divide-y">
                  {report.results.map((r) => (
                    <div
                      key={r.file}
                      className={`px-4 py-3 ${r.success ? "" : "bg-red-50"}`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs">{r.file}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500">
                            attempt {r.attempt}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-medium ${
                              r.success
                                ? "bg-green-100 text-green-800"
                                : "bg-red-100 text-red-800"
                            }`}
                          >
                            {r.success ? "FIXED" : "FAILED"}
                          </span>
                        </div>
                      </div>
                      {r.error && (
                        <div className="mt-1 text-xs text-red-600">{r.error}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
