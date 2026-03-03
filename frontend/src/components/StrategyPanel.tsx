import { useStrategy } from "../hooks/useStrategy";
import { useState } from "react";
import type { StrategyDTO } from "../api/types";

interface Props {
  seedData?: StrategyDTO | null;
}

const ALL_LAYERS = [
  { value: "unit", label: "Unit", description: "Isolated function-level tests" },
  { value: "integration", label: "Integration", description: "Cross-module interaction tests" },
  { value: "uat", label: "UAT", description: "User acceptance / behaviour-driven tests" },
  { value: "soak", label: "Soak", description: "Long-running stability & resource leak tests" },
  { value: "performance", label: "Performance", description: "Latency, throughput & load tests" },
];

export function StrategyPanel({ seedData }: Props) {
  const { strategy: fetched, loading, error, generate } = useStrategy();
  const [selected, setSelected] = useState<Set<string>>(new Set(["unit"]));

  const strategy = fetched ?? seedData ?? null;

  function toggle(value: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(value)) {
        next.delete(value);
      } else {
        next.add(value);
      }
      return next;
    });
  }

  function handleGenerate() {
    const layers = Array.from(selected).join(",") || "unit";
    generate(".", layers);
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Test Strategy</h2>

      <div className="bg-white border rounded-lg p-4 mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Test Layers
        </label>
        <div className="flex flex-wrap gap-2 mb-4">
          {ALL_LAYERS.map((layer) => (
            <button
              key={layer.value}
              onClick={() => toggle(layer.value)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                selected.has(layer.value)
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-700 border-gray-300 hover:border-blue-400"
              }`}
            >
              {layer.label}
            </button>
          ))}
        </div>
        <div className="text-xs text-gray-500 space-y-1 mb-4">
          {ALL_LAYERS.filter((l) => selected.has(l.value)).map((l) => (
            <div key={l.value}>
              <span className="font-medium text-gray-700">{l.label}:</span>{" "}
              {l.description}
            </div>
          ))}
        </div>
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          onClick={handleGenerate}
          disabled={loading || selected.size === 0}
        >
          {loading
            ? "Generating..."
            : `Generate Strategy (${selected.size} layer${selected.size !== 1 ? "s" : ""})`}
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
