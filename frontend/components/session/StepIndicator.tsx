'use client';
import type { SessionStatus } from '@/lib/types';
import { STEP_NAMES } from '@/lib/session-format';
import { Check } from 'lucide-react';

interface StepIndicatorProps {
  currentStep: number;
  selectedStep: number;
  /** Steps that have panel data (are navigable). */
  availableSteps: Set<number>;
  streaming?: boolean;
  sessionStatus?: SessionStatus;
  onSelect: (step: number) => void;
}

/**
 * The single step navigator. Renders all 10 steps with three states —
 * done (clickable), current (active), upcoming (locked) — and is the
 * only way to move between panels.
 */
export function StepIndicator({
  currentStep, selectedStep, availableSteps, streaming, sessionStatus, onSelect,
}: StepIndicatorProps) {
  const complete = sessionStatus === 'complete';

  return (
    <div className="stepnav" role="tablist" aria-label="Advisory steps">
      {STEP_NAMES.map((label, i) => {
        const n = i + 1;
        const has = availableSteps.has(n);
        const done = complete || (n < currentStep && has);
        const isCurrent = n === currentStep;
        const selected = n === selectedStep;
        const clickable = has;
        const streamingHere = isCurrent && streaming && !has;

        return (
          <button
            key={n}
            role="tab"
            aria-selected={selected}
            disabled={!clickable}
            onClick={() => clickable && onSelect(n)}
            className={[
              'step',
              selected ? 'step--selected' : '',
              done ? 'step--done' : '',
              isCurrent ? 'step--current' : '',
              !clickable ? 'step--locked' : '',
            ].join(' ')}
            title={label}
          >
            <span className="step-marker">
              {done ? <Check size={11} strokeWidth={3} />
                : streamingHere ? <span className="step-pulse" />
                : n}
            </span>
            <span className="step-label">{label}</span>
          </button>
        );
      })}

      <style jsx>{`
        .stepnav {
          display: flex;
          align-items: center;
          gap: 2px;
          overflow-x: auto;
          scrollbar-width: none;
        }
        .stepnav::-webkit-scrollbar { display: none; }
        .step {
          display: flex; align-items: center; gap: 6px;
          padding: 5px 10px;
          background: none; border: none; border-radius: var(--radius-sm);
          font-size: var(--text-xs); white-space: nowrap;
          color: var(--text-muted); cursor: pointer;
          transition: background 0.15s, color 0.15s;
        }
        .step:hover:not(.step--locked) { background: var(--bg-hover); color: var(--text-primary); }
        .step--locked { cursor: default; opacity: 0.5; }
        .step--done { color: var(--success); }
        .step--current { color: var(--accent); }
        .step--selected { background: var(--bg-elevated); color: var(--text-primary); font-weight: 600; }
        .step-marker {
          display: inline-flex; align-items: center; justify-content: center;
          width: 18px; height: 18px; border-radius: 50%;
          font-size: 10px; font-weight: 600; flex-shrink: 0;
          border: 1px solid currentColor;
        }
        .step--selected .step-marker { border-color: var(--accent); color: var(--accent); }
        .step-pulse {
          width: 7px; height: 7px; border-radius: 50%;
          background: var(--accent); animation: pulse-glow 1s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}

export default StepIndicator;
