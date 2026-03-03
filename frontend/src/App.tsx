import { useState } from "react";
import { Layout } from "./components/Layout";
import { AnalysisPanel } from "./components/AnalysisPanel";
import { StrategyPanel } from "./components/StrategyPanel";
import { GeneratePanel } from "./components/GeneratePanel";
import { ExecutePanel } from "./components/ExecutePanel";
import { GapsPanel } from "./components/GapsPanel";
import { ValidatePanel } from "./components/ValidatePanel";
import { RepairPanel } from "./components/RepairPanel";
import { MutationPanel } from "./components/MutationPanel";
import { ChatPanel } from "./components/ChatPanel";
import { useSeedData } from "./hooks/useSeedData";

export default function App() {
  const [tab, setTab] = useState("analysis");
  const { data, loading, step, seed } = useSeedData();

  return (
    <Layout
      activeTab={tab}
      onTabChange={setTab}
      onSeed={seed}
      seeding={loading}
      seedStep={step}
    >
      {tab === "analysis" && <AnalysisPanel seedData={data.analysis} />}
      {tab === "strategy" && <StrategyPanel seedData={data.strategy} />}
      {tab === "generate" && <GeneratePanel />}
      {tab === "execute" && <ExecutePanel seedData={data.execution} />}
      {tab === "gaps" && <GapsPanel seedData={data.gaps} />}
      {tab === "validate" && <ValidatePanel seedData={data.validation} />}
      {tab === "repair" && <RepairPanel />}
      {tab === "mutation" && <MutationPanel />}
      {tab === "chat" && <ChatPanel />}
    </Layout>
  );
}
