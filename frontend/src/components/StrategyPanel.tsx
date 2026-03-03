import { useStrategy } from "../hooks/useStrategy";
import { useState } from "react";

export function StrategyPanel() {
  const { strategy, loading, error, generate } = useStrategy();
  const [layers, setLayers] = useState("unit");

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Test Strategy</h2>

      <div className="flex gap-2 mb-6">
        <input
          className="border rounded px-3 py-2 flex-1 text-sm"
          placeholder="Layers (e.g. unit,integration)"
          value={layers}
          onChange={(e) => setLayers(e.target.value)}
        />
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          onClick={() => generate(".", layers)}
          disabled={loading}
        >
          {loading ? "Generating..." : "Generate Strategy"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {strategy && (
        <div>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Test Cases</p>
              <p className="text-2xl font-bold">{strategy.total_test_cases}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Layers</p>
              <p className="text-2xl font-bold">{strategy.layers_covered.length}</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-gray-500">Suites</p>
              <p className="text-2xl font-bold">{strategy.suites.length}</p>
            </div>
          </div>

          {strategy.suites.map((suite) => (
            <div key={suite.layer} className="bg-white border rounded-lg mb-4">
              <div className="px-4 py-3 border-b bg-gray-50 flex justify-between items-center">
                <h3 className="font-semibold text-sm">
                  {suite.layer.toUpperCase()} Layer
                </h3>
                <span className="text-xs text-gray-500">{suite.size} cases</span>
              </div>
              <div className="overflow-auto max-h-64">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50 text-left">
                      <th className="px-4 py-2">Test</th>
                      <th className="px-4 py-2">Target</th>
                      <th className="px-4 py-2">Module</th>
                      <th className="px-4 py-2 text-right">Priority</th>
                    </tr>
                  </thead>
                  <tbody>
                    {suite.test_cases.map((tc) => (
                      <tr key={tc.name} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-2">{tc.name}</td>
                        <td className="px-4 py-2 font-mono text-xs">{tc.target_function}</td>
                        <td className="px-4 py-2 font-mono text-xs">{tc.target_module}</td>
                        <td className="px-4 py-2 text-right">{tc.priority}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
