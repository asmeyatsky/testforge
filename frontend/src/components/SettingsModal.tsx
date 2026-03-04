import { useState, useEffect } from "react";
import { apiPost, apiGet } from "../api/client";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function SettingsModal({ open, onClose }: Props) {
  const [anthropicKey, setAnthropicKey] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [hasAnthropic, setHasAnthropic] = useState(false);
  const [hasGemini, setHasGemini] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      apiGet<{ anthropic: boolean; gemini: boolean }>("/api/settings/keys").then(
        (res) => {
          setHasAnthropic(res.anthropic);
          setHasGemini(res.gemini);
        }
      );
    }
  }, [open]);

  async function handleSave() {
    setSaving(true);
    const res = await apiPost<{ anthropic: boolean; gemini: boolean }>(
      "/api/settings/keys",
      {
        anthropic_key: anthropicKey || undefined,
        gemini_key: geminiKey || undefined,
      }
    );
    setHasAnthropic(res.anthropic);
    setHasGemini(res.gemini);
    setAnthropicKey("");
    setGeminiKey("");
    setSaving(false);
    onClose();
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-bold mb-4">Settings</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Anthropic API Key
              {hasAnthropic && (
                <span className="ml-2 text-green-600 text-xs font-normal">
                  configured
                </span>
              )}
            </label>
            <input
              className="border rounded px-3 py-2 w-full text-sm"
              type="password"
              placeholder={hasAnthropic ? "••••••••" : "sk-ant-..."}
              value={anthropicKey}
              onChange={(e) => setAnthropicKey(e.target.value)}
            />
            <p className="text-xs text-gray-400 mt-1">
              Used for AI strategy generation, test repair, and chat
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Google Gemini API Key
              {hasGemini && (
                <span className="ml-2 text-green-600 text-xs font-normal">
                  configured
                </span>
              )}
            </label>
            <input
              className="border rounded px-3 py-2 w-full text-sm"
              type="password"
              placeholder={hasGemini ? "••••••••" : "AIza..."}
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
            />
            <p className="text-xs text-gray-400 mt-1">
              Alternative to Anthropic for chat and repair
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
