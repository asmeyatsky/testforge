import { type ReactNode, useState } from "react";
import { Sidebar } from "./Sidebar";
import { SettingsModal } from "./SettingsModal";
import { ToastContainer } from "./Toast";

interface LayoutProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  onSeed: (target: string) => void;
  seeding: boolean;
  seedStep: string;
  children: ReactNode;
}

export function Layout({
  activeTab,
  onTabChange,
  onSeed,
  seeding,
  seedStep,
  children,
}: LayoutProps) {
  const [target, setTarget] = useState(".");
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div className="flex h-screen">
      <Sidebar activeTab={activeTab} onTabChange={onTabChange} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white border-b px-6 py-3 flex items-center gap-3 shrink-0">
          <input
            className="border rounded px-3 py-1.5 text-sm flex-1"
            placeholder="Local path or GitHub URL (e.g. https://github.com/user/repo)"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
          />
          <button
            className="bg-indigo-600 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 whitespace-nowrap"
            onClick={() => onSeed(target)}
            disabled={seeding}
          >
            {seeding ? seedStep || "Loading..." : "Load & Analyse"}
          </button>
          <button
            className="p-1.5 rounded hover:bg-gray-100 text-gray-500"
            onClick={() => setSettingsOpen(true)}
            title="Settings"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </button>
        </header>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
      <ToastContainer />
    </div>
  );
}
