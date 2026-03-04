import { useState } from "react";
import { apiPost } from "../api/client";
import type { ValidationReport } from "../api/types";

interface Props {
  seedData?: ValidationReport | null;
}

export function ValidatePanel({ seedData }: Props) {
  const [testDir, setTestDir] = useState(".testforge_output");
  const [fetched, setFetched] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const report = fetched ?? seedData ?? null;

  async function handleValidate() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiPost<{ validation: ValidationReport }>(
        "/api/validate",
        { test_dir: testDir }
      );
      setFetched(res.validation);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-1">Validate Tests</h2>
      <p className="text-sm text-gray-500 mb-4">
        Checks generated test files for Python syntax errors without running
        them. Point this at the same directory as your generated tests.
      </p>

      <div className="flex gap-2 mb-6">
        <input
          className="border rounded px-3 py-2 flex-1 text-sm"
          placeholder="Test directory"
          value={testDir}
          onChange={(e) => setTestDir(e.target.value)}
        />
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          onClick={handleValidate}
          disabled={loading}
        >
          {loading ? "Validating..." : "Validate"}
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
              <p className="text-sm text-gray-500">Total</p>
              <p className="text-2xl font-bold">{report.total}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Passed</p>
              <p className="text-2xl font-bold text-green-600">{report.passed}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Success Rate</p>
              <p className="text-2xl font-bold">
                {(report.success_rate * 100).toFixed(0)}%
              </p>
            </div>
          </div>

          <div className="bg-white border rounded-lg">
            <div className="px-4 py-3 border-b bg-gray-50">
              <h3 className="font-semibold text-sm">
                Results ({report.results.length} files)
              </h3>
            </div>
            <div className="divide-y max-h-96 overflow-auto">
              {report.results.map((r) => (
                <div
                  key={r.file_path}
                  className={`px-4 py-3 ${r.valid ? "" : "bg-red-50"}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs">{r.file_path}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        r.valid
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {r.valid ? "PASS" : "FAIL"}
                    </span>
                  </div>
                  {r.errors.length > 0 && (
                    <div className="mt-1 text-xs text-red-600">
                      {r.errors.join("; ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
