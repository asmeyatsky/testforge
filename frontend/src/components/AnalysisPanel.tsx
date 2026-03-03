import { useAnalysis } from "../hooks/useAnalysis";
import { useState, useEffect } from "react";
import type { AnalysisDTO } from "../api/types";

interface Props {
  seedData?: AnalysisDTO | null;
}

export function AnalysisPanel({ seedData }: Props) {
  const { analysis: fetched, loading, error, analyse } = useAnalysis();
  const [path, setPath] = useState(".");

  const analysis = fetched ?? seedData ?? null;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Codebase Analysis</h2>

      <div className="flex gap-2 mb-6">
        <input
          className="border rounded px-3 py-2 flex-1 text-sm"
          placeholder="Project path"
          value={path}
          onChange={(e) => setPath(e.target.value)}
        />
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          onClick={() => analyse(path)}
          disabled={loading}
        >
          {loading ? "Scanning..." : "Analyse"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {analysis && (
        <div>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Modules</p>
              <p className="text-2xl font-bold">{analysis.total_modules}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Functions</p>
              <p className="text-2xl font-bold">{analysis.total_functions}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Classes</p>
              <p className="text-2xl font-bold">{analysis.total_classes}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Languages</p>
              <p className="text-2xl font-bold">{analysis.languages.join(", ")}</p>
            </div>
          </div>

          <div className="bg-white border rounded-lg">
            <div className="px-4 py-3 border-b bg-gray-50">
              <h3 className="font-semibold text-sm">
                Modules ({analysis.modules.length})
              </h3>
            </div>
            <div className="overflow-auto max-h-96">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50 text-left">
                    <th className="px-4 py-2">File</th>
                    <th className="px-4 py-2 text-right">Functions</th>
                    <th className="px-4 py-2 text-right">Classes</th>
                    <th className="px-4 py-2 text-right">Endpoints</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.modules.map((mod) => (
                    <tr key={mod.file_path} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-xs">{mod.file_path}</td>
                      <td className="px-4 py-2 text-right">{mod.function_count}</td>
                      <td className="px-4 py-2 text-right">{mod.class_count}</td>
                      <td className="px-4 py-2 text-right">{mod.endpoint_count}</td>
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
