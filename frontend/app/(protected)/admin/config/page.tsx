"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Boxes,
  CheckCircle2,
  GitBranch,
  RefreshCw,
  Route,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui";
import { fetchEngineManifest } from "@/lib/api";
import type { EngineBranch, EngineManifest } from "@/lib/types";

type ExplorerView = "branches" | "components" | "controls";

const SUMMARY_LABELS: {
  key: keyof EngineManifest["summary"];
  label: string;
}[] = [
  { key: "workloads", label: "Workload branches" },
  { key: "universal_questions", label: "Universal questions" },
  { key: "branch_questions", label: "Branch questions" },
  { key: "components", label: "Capabilities" },
  { key: "regulatory_controls", label: "Regulatory controls" },
];

function formatToken(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function AdminEnginePage() {
  const [manifest, setManifest] = useState<EngineManifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [view, setView] = useState<ExplorerView>("branches");
  const [workload, setWorkload] = useState("universal");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const next = await fetchEngineManifest();
      setManifest(next);
      setWorkload((current) => (
        current === "universal"
        || next.questionnaire.branches.some((branch) => branch.workload === current)
          ? current
          : "universal"
      ));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const questionBranches = useMemo<EngineBranch[]>(() => {
    if (!manifest) return [];
    return [
      {
        workload: "universal",
        label: "Universal baseline",
        question_count: manifest.questionnaire.universal.length,
        critical_count: manifest.questionnaire.universal.filter((question) => question.critical).length,
        questions: manifest.questionnaire.universal,
      },
      ...manifest.questionnaire.branches,
    ];
  }, [manifest]);

  const activeBranch = useMemo(
    () => questionBranches.find((branch) => branch.workload === workload) ?? null,
    [questionBranches, workload],
  );

  if (loading && !manifest) {
    return (
      <div className="engine-page">
        <div className="skeleton" style={{ height: 92 }} />
        <div className="skeleton" style={{ height: 108 }} />
        <div className="skeleton" style={{ height: 360 }} />
      </div>
    );
  }

  if (!manifest) {
    return (
      <div className="engine-page">
        <div className="engine-empty">
          <XCircle size={24} />
          <h1>Decision engine unavailable</h1>
          <p>{error || "The deployed API did not return an engine manifest."}</p>
          <Button variant="secondary" onClick={() => void load()}>
            <RefreshCw size={15} /> Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="engine-page">
      <header className="engine-header">
        <div>
          <div className="engine-title-row">
            <h1 className="text-page-title">{manifest.engine.name}</h1>
            <span className="engine-live"><span /> Loaded</span>
          </div>
          <p>
            Inspect the deployed questionnaire, deterministic decision flow, capability catalog,
            and control coverage.
          </p>
        </div>
        <Button variant="secondary" size="sm" loading={loading} onClick={() => void load()}>
          <RefreshCw size={14} /> Refresh
        </Button>
      </header>

      {error && <div className="engine-error">{error}</div>}

      <section className="engine-version-strip" aria-label="Engine versions">
        <Version label="Schema" value={manifest.engine.schema_version} />
        <Version label="Questionnaire" value={manifest.engine.questionnaire_version} />
        <Version label="Methodology" value={manifest.engine.methodology_version} />
        <Version label="Catalog" value={manifest.engine.catalog_version} />
        <Version label="Price basis" value={manifest.engine.price_catalog_date} />
        <div className="engine-authority">
          <ShieldCheck size={15} />
          <span>LLM decision authority</span>
          <strong>{manifest.engine.llm_decision_authority ? "Enabled" : "Disabled"}</strong>
        </div>
      </section>

      <dl className="engine-metrics">
        {SUMMARY_LABELS.map(({ key, label }) => (
          <div key={key}>
            <dt>{label}</dt>
            <dd>{manifest.summary[key]}</dd>
          </div>
        ))}
      </dl>

      <section className="engine-section">
        <div className="engine-section-heading">
          <div>
            <span className="engine-kicker"><Route size={14} /> Decision pipeline</span>
            <h2>Evidence to blueprint</h2>
          </div>
          <span className="engine-mode">Deterministic execution</span>
        </div>
        <ol className="engine-pipeline">
          {manifest.pipeline.map((stage, index) => (
            <li key={stage.id}>
              <div className="engine-stage-index">{String(index + 1).padStart(2, "0")}</div>
              <div>
                <strong>{stage.label}</strong>
                <p>{stage.description}</p>
                <div className="engine-output-list">
                  {stage.outputs.map((output) => <span key={output}>{output}</span>)}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="engine-section engine-explorer">
        <div className="engine-section-heading">
          <div>
            <span className="engine-kicker"><GitBranch size={14} /> Engine explorer</span>
            <h2>Decision inputs and catalogs</h2>
          </div>
        </div>

        <div className="engine-tabs" role="tablist" aria-label="Engine explorer views">
          <ExplorerTab active={view === "branches"} onClick={() => setView("branches")}>
            Question branches
          </ExplorerTab>
          <ExplorerTab active={view === "components"} onClick={() => setView("components")}>
            Capability catalog
          </ExplorerTab>
          <ExplorerTab active={view === "controls"} onClick={() => setView("controls")}>
            Control catalog
          </ExplorerTab>
        </div>

        {view === "branches" && (
          <BranchExplorer
            branches={questionBranches}
            active={activeBranch}
            workload={workload}
            onWorkload={setWorkload}
            universalCount={manifest.questionnaire.universal.length}
          />
        )}
        {view === "components" && (
          <div className="engine-table-wrap">
            <table className="engine-table">
              <thead>
                <tr>
                  <th>Capability</th>
                  <th>Layer</th>
                  <th>Activation</th>
                  <th>Dependencies</th>
                  <th>AWS mapping</th>
                  <th>Planning base</th>
                </tr>
              </thead>
              <tbody>
                {manifest.catalog.components.map((component) => (
                  <tr key={component.id}>
                    <td>
                      <strong>{component.name}</strong>
                      <code>{component.id}</code>
                    </td>
                    <td><span className="engine-layer">{component.layer}</span></td>
                    <td>{component.activation}</td>
                    <td>{component.dependencies.length ? component.dependencies.join(", ") : "None"}</td>
                    <td>{component.aws_services.join(", ")}</td>
                    <td className="engine-money">
                      ${component.monthly_planning_base_usd.toLocaleString()}
                      <span>/mo</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {view === "controls" && (
          <div className="engine-control-list">
            {manifest.catalog.controls.map((family) => (
              <section key={family.regime}>
                <header>
                  <strong>{family.regime}</strong>
                  <span>{family.control_count} controls</span>
                </header>
                <div>
                  {family.controls.map((control) => (
                    <article key={control.id}>
                      <div>
                        <strong>{control.name}</strong>
                        <code>{control.id}</code>
                      </div>
                      <p>{control.implementation}</p>
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </section>

      <section className="engine-checks">
        <div>
          <Boxes size={16} />
          <strong>Catalog integrity</strong>
        </div>
        <ul>
          {manifest.checks.map((check) => (
            <li key={check.id} className={check.ok ? "ok" : "failed"}>
              {check.ok ? <CheckCircle2 size={15} /> : <XCircle size={15} />}
              {check.label}
            </li>
          ))}
        </ul>
      </section>

      <style jsx global>{`
        .engine-page {
          width: 100%;
          max-width: 1280px;
          margin: 0 auto;
          padding: var(--space-6);
          display: flex;
          flex-direction: column;
          gap: var(--space-5);
        }
        .engine-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: var(--space-5);
        }
        .engine-header p {
          margin-top: 5px;
          color: var(--text-secondary);
          font-size: var(--text-sm);
          line-height: 1.55;
        }
        .engine-title-row {
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          gap: 10px;
        }
        .engine-live {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 3px 8px;
          border-radius: 999px;
          background: var(--success-subtle);
          color: var(--success);
          font-size: var(--text-xs);
          font-weight: 600;
        }
        .engine-live > span {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--success);
        }
        .engine-error {
          padding: 10px 12px;
          border: 1px solid var(--danger);
          border-radius: 8px;
          background: var(--danger-subtle);
          color: var(--danger);
          font-size: var(--text-sm);
        }
        .engine-version-strip {
          display: grid;
          grid-template-columns: repeat(5, minmax(105px, 1fr)) minmax(220px, 1.4fr);
          border: 1px solid var(--border-default);
          border-radius: 8px;
          background: var(--bg-card);
          overflow: hidden;
        }
        .engine-version-strip > div {
          min-width: 0;
          padding: 11px 14px;
          border-right: 1px solid var(--border-default);
        }
        .engine-version-strip > div:last-child { border-right: 0; }
        .engine-version-strip span {
          display: block;
          color: var(--text-muted);
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
        .engine-version-strip strong {
          display: block;
          margin-top: 3px;
          color: var(--text-primary);
          font-size: var(--text-sm);
          font-weight: 600;
          overflow-wrap: anywhere;
        }
        .engine-authority {
          display: grid;
          grid-template-columns: auto 1fr;
          align-items: center;
          column-gap: 8px;
          color: var(--accent);
        }
        .engine-authority span { text-transform: none; letter-spacing: 0; }
        .engine-authority strong { grid-column: 2; margin-top: 0; }
        .engine-metrics {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          border-top: 1px solid var(--border-default);
          border-bottom: 1px solid var(--border-default);
        }
        .engine-metrics > div {
          padding: 14px 18px;
          border-right: 1px solid var(--border-default);
        }
        .engine-metrics > div:last-child { border-right: 0; }
        .engine-metrics dt {
          color: var(--text-muted);
          font-size: var(--text-xs);
        }
        .engine-metrics dd {
          margin-top: 4px;
          color: var(--text-primary);
          font-family: var(--font-mono-stack);
          font-size: var(--text-xl);
          font-weight: 600;
        }
        .engine-section {
          display: flex;
          flex-direction: column;
          gap: var(--space-4);
        }
        .engine-section-heading {
          display: flex;
          align-items: flex-end;
          justify-content: space-between;
          gap: var(--space-4);
        }
        .engine-section-heading h2 {
          margin-top: 3px;
          color: var(--text-primary);
          font-size: var(--text-lg);
          font-weight: 600;
        }
        .engine-kicker {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          color: var(--text-muted);
          font-size: var(--text-xs);
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
        .engine-mode {
          color: var(--text-muted);
          font-family: var(--font-mono-stack);
          font-size: var(--text-xs);
        }
        .engine-pipeline {
          display: grid;
          grid-template-columns: repeat(7, minmax(150px, 1fr));
          border: 1px solid var(--border-default);
          border-radius: 8px;
          overflow-x: auto;
          background: var(--bg-card);
        }
        .engine-pipeline li {
          min-height: 196px;
          padding: 14px;
          border-right: 1px solid var(--border-default);
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .engine-pipeline li:last-child { border-right: 0; }
        .engine-stage-index {
          color: var(--accent);
          font-family: var(--font-mono-stack);
          font-size: var(--text-xs);
          font-weight: 700;
        }
        .engine-pipeline strong {
          color: var(--text-primary);
          font-size: var(--text-sm);
        }
        .engine-pipeline p {
          margin-top: 7px;
          color: var(--text-secondary);
          font-size: var(--text-xs);
          line-height: 1.5;
        }
        .engine-output-list {
          margin-top: 12px;
          display: flex;
          flex-wrap: wrap;
          gap: 5px;
        }
        .engine-output-list span,
        .engine-consumer {
          padding: 2px 6px;
          border-radius: 4px;
          background: var(--bg-hover);
          color: var(--text-secondary);
          font-family: var(--font-mono-stack);
          font-size: 10px;
        }
        .engine-tabs {
          display: flex;
          gap: 2px;
          width: fit-content;
          padding: 3px;
          border: 1px solid var(--border-default);
          border-radius: 8px;
          background: var(--bg-card);
        }
        .engine-tab {
          padding: 7px 12px;
          border: 0;
          border-radius: 6px;
          background: transparent;
          color: var(--text-secondary);
          cursor: pointer;
          font-family: inherit;
          font-size: var(--text-sm);
        }
        .engine-tab:hover { background: var(--bg-hover); color: var(--text-primary); }
        .engine-tab.active {
          background: var(--accent);
          color: var(--accent-fg);
          font-weight: 600;
        }
        .engine-branch-layout {
          display: grid;
          grid-template-columns: 250px minmax(0, 1fr);
          min-height: 430px;
          border: 1px solid var(--border-default);
          border-radius: 8px;
          overflow: hidden;
          background: var(--bg-card);
        }
        .engine-branch-nav {
          padding: 8px;
          border-right: 1px solid var(--border-default);
          background: var(--bg-primary);
          display: flex;
          flex-direction: column;
          gap: 3px;
        }
        .engine-branch-nav button {
          display: grid;
          grid-template-columns: 1fr auto;
          align-items: center;
          gap: 8px;
          padding: 10px;
          border: 0;
          border-radius: 6px;
          background: transparent;
          color: var(--text-secondary);
          cursor: pointer;
          font-family: inherit;
          font-size: var(--text-sm);
          text-align: left;
        }
        .engine-branch-nav button:hover { background: var(--bg-hover); }
        .engine-branch-nav button.active {
          background: var(--accent-soft);
          color: var(--accent-deep);
          font-weight: 600;
        }
        .engine-branch-nav span {
          color: var(--text-muted);
          font-family: var(--font-mono-stack);
          font-size: 10px;
        }
        .engine-branch-panel { min-width: 0; }
        .engine-branch-summary {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: var(--space-4);
          padding: 14px 16px;
          border-bottom: 1px solid var(--border-default);
        }
        .engine-branch-summary strong {
          display: block;
          color: var(--text-primary);
          font-size: var(--text-sm);
        }
        .engine-branch-summary p {
          margin-top: 3px;
          color: var(--text-muted);
          font-size: var(--text-xs);
        }
        .engine-branch-count {
          flex-shrink: 0;
          color: var(--accent-deep);
          font-family: var(--font-mono-stack);
          font-size: var(--text-xs);
        }
        .engine-table-wrap {
          width: 100%;
          overflow-x: auto;
          border: 1px solid var(--border-default);
          border-radius: 8px;
          background: var(--bg-card);
        }
        .engine-table {
          width: 100%;
          border-collapse: collapse;
          font-size: var(--text-xs);
        }
        .engine-table th {
          padding: 9px 12px;
          background: var(--bg-primary);
          color: var(--text-muted);
          font-size: 10px;
          font-weight: 600;
          text-align: left;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          white-space: nowrap;
        }
        .engine-table td {
          padding: 11px 12px;
          border-top: 1px solid var(--border-default);
          color: var(--text-secondary);
          line-height: 1.45;
          vertical-align: top;
        }
        .engine-table td strong {
          display: block;
          color: var(--text-primary);
          font-size: var(--text-sm);
          font-weight: 600;
        }
        .engine-table code {
          display: block;
          margin-top: 3px;
          color: var(--text-muted);
          font-size: 10px;
          overflow-wrap: anywhere;
        }
        .engine-question-prompt { min-width: 250px; max-width: 380px; }
        .engine-question-flags {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          margin-top: 5px;
        }
        .engine-required {
          color: var(--danger);
          font-size: 10px;
          font-weight: 600;
          text-transform: uppercase;
        }
        .engine-layer {
          display: inline-block;
          padding: 2px 6px;
          border-radius: 4px;
          background: var(--accent-soft);
          color: var(--accent-deep);
          font-weight: 600;
          white-space: nowrap;
        }
        .engine-money {
          color: var(--text-primary) !important;
          font-family: var(--font-mono-stack);
          font-weight: 600;
          white-space: nowrap;
        }
        .engine-money span {
          margin-left: 2px;
          color: var(--text-muted);
          font-size: 10px;
          font-weight: 400;
        }
        .engine-control-list {
          border: 1px solid var(--border-default);
          border-radius: 8px;
          background: var(--bg-card);
          overflow: hidden;
        }
        .engine-control-list > section {
          display: grid;
          grid-template-columns: 180px minmax(0, 1fr);
          border-top: 1px solid var(--border-default);
        }
        .engine-control-list > section:first-child { border-top: 0; }
        .engine-control-list > section > header {
          padding: 14px;
          background: var(--bg-primary);
        }
        .engine-control-list > section > header strong {
          display: block;
          color: var(--text-primary);
          font-size: var(--text-sm);
        }
        .engine-control-list > section > header span {
          display: block;
          margin-top: 4px;
          color: var(--text-muted);
          font-size: var(--text-xs);
        }
        .engine-control-list article {
          display: grid;
          grid-template-columns: minmax(180px, 0.8fr) minmax(280px, 1.2fr);
          gap: 18px;
          padding: 12px 14px;
          border-bottom: 1px solid var(--border-default);
        }
        .engine-control-list article:last-child { border-bottom: 0; }
        .engine-control-list article strong {
          display: block;
          color: var(--text-primary);
          font-size: var(--text-xs);
        }
        .engine-control-list article code {
          display: block;
          margin-top: 3px;
          color: var(--text-muted);
          font-size: 10px;
        }
        .engine-control-list article p {
          color: var(--text-secondary);
          font-size: var(--text-xs);
          line-height: 1.5;
        }
        .engine-checks {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: var(--space-4);
          padding: 13px 16px;
          border-top: 1px solid var(--border-default);
          border-bottom: 1px solid var(--border-default);
        }
        .engine-checks > div {
          display: flex;
          align-items: center;
          gap: 8px;
          color: var(--text-primary);
          font-size: var(--text-sm);
        }
        .engine-checks ul {
          display: flex;
          flex-wrap: wrap;
          justify-content: flex-end;
          gap: 8px 16px;
        }
        .engine-checks li {
          display: flex;
          align-items: center;
          gap: 5px;
          font-size: var(--text-xs);
        }
        .engine-checks li.ok { color: var(--success); }
        .engine-checks li.failed { color: var(--danger); }
        .engine-empty {
          min-height: 420px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 12px;
          color: var(--danger);
          text-align: center;
        }
        .engine-empty h1 {
          color: var(--text-primary);
          font-size: var(--text-lg);
          font-weight: 600;
        }
        .engine-empty p {
          max-width: 620px;
          color: var(--text-secondary);
          font-size: var(--text-sm);
        }
        @media (max-width: 980px) {
          .engine-version-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); }
          .engine-version-strip > div { border-bottom: 1px solid var(--border-default); }
          .engine-version-strip > div:nth-child(3n) { border-right: 0; }
          .engine-version-strip > div:nth-last-child(-n + 3) { border-bottom: 0; }
          .engine-metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); }
          .engine-metrics > div { border-bottom: 1px solid var(--border-default); }
          .engine-branch-layout { grid-template-columns: 210px minmax(0, 1fr); }
          .engine-checks { align-items: flex-start; flex-direction: column; }
          .engine-checks ul { justify-content: flex-start; }
        }
        @media (max-width: 700px) {
          .engine-page { padding: var(--space-4); }
          .engine-header { align-items: stretch; flex-direction: column; }
          .engine-header > button { align-self: flex-start; }
          .engine-version-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
          .engine-version-strip > div:nth-child(3n) { border-right: 1px solid var(--border-default); }
          .engine-version-strip > div:nth-child(2n) { border-right: 0; }
          .engine-version-strip > div:nth-last-child(-n + 3) { border-bottom: 1px solid var(--border-default); }
          .engine-version-strip > div:nth-last-child(-n + 2) { border-bottom: 0; }
          .engine-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
          .engine-tabs { width: 100%; overflow-x: auto; }
          .engine-tab { flex: 1; white-space: nowrap; }
          .engine-branch-layout { display: block; }
          .engine-branch-nav {
            overflow-x: auto;
            flex-direction: row;
            border-right: 0;
            border-bottom: 1px solid var(--border-default);
          }
          .engine-branch-nav button {
            min-width: 170px;
          }
          .engine-control-list > section { display: block; }
          .engine-control-list article {
            grid-template-columns: minmax(0, 1fr);
            gap: 6px;
          }
        }
      `}</style>
    </div>
  );
}

function Version({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ExplorerTab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      className={active ? "engine-tab active" : "engine-tab"}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function BranchExplorer({
  branches,
  active,
  workload,
  onWorkload,
  universalCount,
}: {
  branches: EngineBranch[];
  active: EngineBranch | null;
  workload: string;
  onWorkload: (workload: string) => void;
  universalCount: number;
}) {
  return (
    <div className="engine-branch-layout">
      <nav className="engine-branch-nav" aria-label="Workload question branches">
        {branches.map((branch) => (
          <button
            key={branch.workload}
            type="button"
            className={branch.workload === workload ? "active" : ""}
            onClick={() => onWorkload(branch.workload)}
          >
            {branch.label}
            <span>{branch.question_count}</span>
          </button>
        ))}
      </nav>
      <div className="engine-branch-panel">
        {active && (
          <>
            <header className="engine-branch-summary">
              <div>
                <strong>{active.label}</strong>
                <p>
                  {active.workload === "universal"
                    ? "Applied to every assessment before the workload-specific branch."
                    : `${universalCount} universal questions, then this workload-specific branch.`}
                </p>
              </div>
              <span className="engine-branch-count">
                {active.critical_count}/{active.question_count} critical
              </span>
            </header>
            <div className="engine-table-wrap" style={{ border: 0, borderRadius: 0 }}>
              <table className="engine-table">
                <thead>
                  <tr>
                    <th>Question</th>
                    <th>Evidence path</th>
                    <th>Type</th>
                    <th>Used by</th>
                  </tr>
                </thead>
                <tbody>
                  {active.questions.map((question) => (
                    <tr key={question.id}>
                      <td className="engine-question-prompt">
                        <strong>{question.prompt}</strong>
                        <div className="engine-question-flags">
                          {question.critical && <span className="engine-required">Critical</span>}
                          {question.unit && <span>{question.unit}</span>}
                        </div>
                      </td>
                      <td><code>{question.path}</code></td>
                      <td>{formatToken(question.type)}</td>
                      <td>
                        <div className="engine-question-flags">
                          {question.consumers.map((consumer) => (
                            <span className="engine-consumer" key={consumer}>{consumer}</span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
