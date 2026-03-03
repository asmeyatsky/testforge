const TABS = [
  { id: "analysis", label: "Analysis", icon: "🔍" },
  { id: "strategy", label: "Strategy", icon: "📋" },
  { id: "generate", label: "Generate", icon: "⚙️" },
  { id: "execute", label: "Execute", icon: "▶️" },
  { id: "gaps", label: "Gaps", icon: "📊" },
  { id: "validate", label: "Validate", icon: "✓" },
  { id: "repair", label: "Repair", icon: "🔧" },
  { id: "mutation", label: "Mutation", icon: "🧬" },
  { id: "chat", label: "Chat", icon: "💬" },
];

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  return (
    <aside className="w-56 bg-gray-900 text-gray-100 flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-lg font-bold tracking-tight">TestForge</h1>
        <p className="text-xs text-gray-400 mt-0.5">Dashboard</p>
      </div>
      <nav className="flex-1 py-2">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`w-full text-left px-4 py-2.5 text-sm flex items-center gap-3 transition-colors ${
              activeTab === tab.id
                ? "bg-gray-700 text-white"
                : "text-gray-300 hover:bg-gray-800 hover:text-white"
            }`}
          >
            <span className="text-base">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
        v0.1.0
      </div>
    </aside>
  );
}
