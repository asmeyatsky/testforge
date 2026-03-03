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

const PANELS: Record<string, () => JSX.Element> = {
  analysis: AnalysisPanel,
  strategy: StrategyPanel,
  generate: GeneratePanel,
  execute: ExecutePanel,
  gaps: GapsPanel,
  validate: ValidatePanel,
  repair: RepairPanel,
  mutation: MutationPanel,
  chat: ChatPanel,
};

export default function App() {
  const [tab, setTab] = useState("analysis");
  const Panel = PANELS[tab] || AnalysisPanel;

  return (
    <Layout activeTab={tab} onTabChange={setTab}>
      <Panel />
    </Layout>
  );
}
