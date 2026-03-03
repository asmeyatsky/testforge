import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";

interface LayoutProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  onSeed: () => void;
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
  return (
    <div className="flex h-screen">
      <Sidebar activeTab={activeTab} onTabChange={onTabChange} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white border-b px-6 py-3 flex items-center justify-between shrink-0">
          <div>
            {seeding && (
              <span className="text-sm text-blue-600 animate-pulse">
                {seedStep}
              </span>
            )}
          </div>
          <button
            className="bg-indigo-600 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            onClick={onSeed}
            disabled={seeding}
          >
            {seeding ? "Loading..." : "Load Demo Data"}
          </button>
        </header>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
