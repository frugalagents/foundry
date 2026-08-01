import "@xyflow/react/dist/style.css";
import {
  Download,
  Network,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { useMemo, useState } from "react";
import { ArchitectureCanvas } from "./ArchitectureCanvas";
import { DecisionPanel } from "./DecisionPanel";
import { InsightPanel } from "./InsightPanel";
import { decisions, scenarioFacts } from "./catalog";
import {
  applyDecision,
  deriveArchitecture,
  getLatestComponentIds,
  getNextDecision,
} from "./engine";
import type { AdvisorState } from "./types";
import "./styles.css";

const initialState: AdvisorState = { answers: {} };

function App() {
  const [state, setState] = useState<AdvisorState>(initialState);
  const architecture = useMemo(() => deriveArchitecture(state), [state]);
  const nextDecision = getNextDecision(state);
  const latestIds = useMemo(() => getLatestComponentIds(state), [state]);
  const answeredCount = Object.keys(state.answers).length;

  const handleDecision = (optionId: string) => {
    if (!nextDecision) return;
    setState((current) =>
      applyDecision(current, nextDecision.id, optionId),
    );
  };

  const exportPacket = () => {
    const packet = {
      generatedAt: new Date().toISOString(),
      scenario: "Enterprise coding-agent platform",
      facts: scenarioFacts,
      decisions: state.answers,
      architecture,
    };
    const blob = new Blob([JSON.stringify(packet, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "coding-agent-platform-decision-packet.json";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">
            <Network size={20} />
          </span>
          <div>
            <strong>Platform Architecture Studio</strong>
            <span>Architecture-first coding-agent advisor</span>
          </div>
        </div>

        <div className="topbar-actions">
          <span className="scenario-name">
            <Sparkles size={15} />
            Enterprise coding fleet
          </span>
          <button
            className="icon-button"
            type="button"
            onClick={() => setState(initialState)}
            title="Reset architecture"
            aria-label="Reset architecture"
          >
            <RotateCcw size={17} />
          </button>
          <button
            className="primary-button"
            type="button"
            onClick={exportPacket}
          >
            <Download size={16} />
            Export
          </button>
        </div>
      </header>

      <section className="context-strip" aria-label="Scenario context">
        <span className="context-label">Confirmed context</span>
        <div className="fact-list">
          {scenarioFacts.map((fact) => (
            <span key={fact}>{fact}</span>
          ))}
        </div>
        <span className="architecture-count">
          {architecture.components.length} components
        </span>
      </section>

      <div className="workspace">
        <section className="architecture-workspace">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Live reference architecture</p>
              <h1>Enterprise coding-agent platform</h1>
            </div>
            <div className="status-legend">
              <span><i className="status-dot confirmed-dot" />Confirmed</span>
              <span><i className="status-dot proposed-dot" />Proposed</span>
              <span><i className="status-dot unresolved-dot" />Unresolved</span>
            </div>
          </div>
          <ArchitectureCanvas
            components={architecture.components}
            edges={architecture.edges}
            latestIds={latestIds}
          />
        </section>

        <aside className="advisor-workspace">
          <DecisionPanel
            decision={nextDecision}
            answeredCount={answeredCount}
            totalCount={decisions.length}
            onSelect={handleDecision}
            onReset={() => setState(initialState)}
          />
          <InsightPanel
            architecture={architecture}
            state={state}
            onExport={exportPacket}
          />
        </aside>
      </div>
    </main>
  );
}

export default App;
