import {
  ArrowRight,
  Check,
  CircleAlert,
  Lightbulb,
  RotateCcw,
} from "lucide-react";
import type { DecisionDefinition } from "./types";

interface DecisionPanelProps {
  decision?: DecisionDefinition;
  answeredCount: number;
  totalCount: number;
  onSelect: (optionId: string) => void;
  onReset: () => void;
}

export function DecisionPanel({
  decision,
  answeredCount,
  totalCount,
  onSelect,
  onReset,
}: DecisionPanelProps) {
  if (!decision) {
    return (
      <section className="decision-panel complete-panel">
        <div className="complete-icon">
          <Check size={24} />
        </div>
        <p className="eyebrow">Architecture shaped</p>
        <h2>Decision-ready reference design</h2>
        <p>
          The logical architecture now includes an implementable service bundle,
          token economics and outcome SLOs. Unresolved items remain explicit
          assumptions rather than hidden defaults.
        </p>
        <button className="secondary-button" type="button" onClick={onReset}>
          <RotateCcw size={16} />
          Restart decisions
        </button>
      </section>
    );
  }

  return (
    <section className="decision-panel">
      <div className="decision-meta">
        <span>{decision.category}</span>
        <span>
          {answeredCount + 1} / {totalCount}
        </span>
      </div>

      <div className="decision-progress" aria-hidden="true">
        <span
          style={{ width: `${((answeredCount + 1) / totalCount) * 100}%` }}
        />
      </div>

      <div className="decision-heading">
        <span className="decision-number">{decision.number}</span>
        <h2>{decision.title}</h2>
      </div>

      <div className="recommendation">
        <Lightbulb size={18} />
        <div>
          <strong>Advisor recommendation</strong>
          <p>{decision.recommendation}</p>
        </div>
      </div>

      <div className="why-now">
        <CircleAlert size={16} />
        <span>{decision.whyNow}</span>
      </div>

      <div className="option-list">
        {decision.options.map((option) => (
          <button
            className={`decision-option ${option.recommended ? "recommended-option" : ""}`}
            type="button"
            key={option.id}
            onClick={() => onSelect(option.id)}
          >
            <span className="option-main">
              <span className="option-title-row">
                <strong>{option.label}</strong>
                {option.recommended && <em>Recommended</em>}
              </span>
              <span>{option.description}</span>
              <small>{option.consequence}</small>
            </span>
            <ArrowRight size={18} />
          </button>
        ))}
      </div>
    </section>
  );
}
