import {
  Activity,
  Boxes,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  Download,
  ExternalLink,
} from "lucide-react";
import { useState } from "react";
import type {
  AdvisorState,
  DerivedArchitecture,
  ServiceCandidate,
} from "./types";
import { decisions } from "./catalog";
import { getSelectedOption } from "./engine";

type TabId = "services" | "economics" | "outcomes" | "decisions";

interface InsightPanelProps {
  architecture: DerivedArchitecture;
  state: AdvisorState;
  onExport: () => void;
}

function ServiceRow({ service }: { service: ServiceCandidate }) {
  return (
    <article className="service-row">
      <div className="service-heading">
        <div>
          <strong>{service.component}</strong>
          <span>{service.purpose}</span>
        </div>
        <CheckCircle2 size={17} />
      </div>
      <div className="service-tags">
        {service.recommended.map((item) => (
          <span className="service-tag recommended-service" key={item}>
            {item}
          </span>
        ))}
        {service.alternatives.map((item) => (
          <span className="service-tag alternative-service" key={item}>
            {item}
          </span>
        ))}
      </div>
    </article>
  );
}

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export function InsightPanel({
  architecture,
  state,
  onExport,
}: InsightPanelProps) {
  const [activeTab, setActiveTab] = useState<TabId>("services");
  const tabs: { id: TabId; label: string; icon: typeof Boxes }[] = [
    { id: "services", label: "Services", icon: Boxes },
    { id: "economics", label: "Economics", icon: CircleDollarSign },
    { id: "outcomes", label: "Outcomes", icon: Activity },
    { id: "decisions", label: "Decisions", icon: Clock3 },
  ];

  return (
    <section className="insight-panel">
      <div className="insight-toolbar">
        <div className="tabs" role="tablist" aria-label="Architecture insights">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === tab.id}
                className={activeTab === tab.id ? "active-tab" : ""}
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
              >
                <Icon size={15} />
                {tab.label}
              </button>
            );
          })}
        </div>
        <button
          className="icon-button"
          type="button"
          onClick={onExport}
          title="Export decision packet"
          aria-label="Export decision packet"
        >
          <Download size={17} />
        </button>
      </div>

      <div className="insight-content">
        {activeTab === "services" && (
          <div className="service-list">
            <div className="legend-row">
              <span><i className="legend-dot recommended-dot" />Recommended</span>
              <span><i className="legend-dot alternative-dot" />Eligible alternative</span>
            </div>
            {architecture.services.map((service) => (
              <ServiceRow
                key={`${service.component}-${service.purpose}`}
                service={service}
              />
            ))}
          </div>
        )}

        {activeTab === "economics" && (
          <div className="economics-view">
            <div className="metric-grid">
              <article>
                <span>Model spend / month</span>
                <strong>{currency.format(architecture.economics.modelSpend)}</strong>
                <small>{architecture.economics.effectiveTokensBillions}B effective tokens</small>
              </article>
              <article>
                <span>Platform spend / month</span>
                <strong>{currency.format(architecture.economics.platformSpend)}</strong>
                <small>Runtime, policy and telemetry</small>
              </article>
              <article>
                <span>Cost / successful task</span>
                <strong>${architecture.economics.costPerSuccessfulTask}</strong>
                <small>{architecture.economics.monthlyTasks.toLocaleString()} tasks / month</small>
              </article>
              <article>
                <span>Context reuse</span>
                <strong>{architecture.economics.cacheHitRate}%</strong>
                <small>Estimated safe cache hit rate</small>
              </article>
            </div>
            <p className="planning-note">{architecture.economics.note}</p>
          </div>
        )}

        {activeTab === "outcomes" && (
          <div className="outcomes-view">
            {architecture.outcomes.map((metric) => (
              <article key={metric.label}>
                <div>
                  <span>{metric.label}</span>
                  <small>{metric.target}</small>
                </div>
                <strong className={`metric-${metric.tone}`}>{metric.value}</strong>
              </article>
            ))}
            <div className="outcome-callout">
              <Activity size={17} />
              <p>
                Token and latency metrics remain diagnostics. Platform success is
                measured through accepted changes, quality, rework, intervention
                and cost per successful task.
              </p>
            </div>
          </div>
        )}

        {activeTab === "decisions" && (
          <div className="decision-history">
            {decisions.map((decision) => {
              const selected = getSelectedOption(state, decision);
              return (
                <article
                  className={selected ? "history-complete" : ""}
                  key={decision.id}
                >
                  <span className="history-number">{decision.number}</span>
                  <div>
                    <strong>{decision.title}</strong>
                    <span>
                      {selected ? selected.label : "Pending architecture decision"}
                    </span>
                  </div>
                  {selected && <CheckCircle2 size={17} />}
                </article>
              );
            })}
            <button className="text-button" type="button" onClick={onExport}>
              Export decision packet
              <ExternalLink size={15} />
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
