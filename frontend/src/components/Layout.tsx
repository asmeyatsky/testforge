import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";

interface LayoutProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  children: ReactNode;
}

export function Layout({ activeTab, onTabChange, children }: LayoutProps) {
  return (
    <div className="flex h-screen">
      <Sidebar activeTab={activeTab} onTabChange={onTabChange} />
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
