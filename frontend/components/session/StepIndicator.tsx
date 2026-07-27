'use client';
import type { SessionStatus } from '@/lib/types';

const STEPS = [
  { n: 1, label: 'Intake' },
  { n: 2, label: 'Score' },
  { n: 3, label: 'Architecture' },
  { n: 4, label: 'Innovations' },
  { n: 5, label: 'Compliance' },
  { n: 6, label: 'Services' },
  { n: 7, label: 'Risks' },
  { n: 8, label: 'Phasing' },
  { n: 9, label: 'Costs' },
  { n: 10, label: 'Blueprint' },
];

interface StepIndicatorProps {
  currentStep: number;
  sessionStatus?: SessionStatus;
}

export function StepIndicator({ currentStep, sessionStatus }: StepIndicatorProps) {
  const isComplete = sessionStatus === 'complete';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
      {STEPS.map((s, i) => {
        const done = isComplete || s.n < currentStep;
        const active = s.n === currentStep && !isComplete;
        return (
          <div key={s.n} style={{ display: 'flex', alignItems: 'center' }}>
            <div
              title={s.label}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 4,
                cursor: 'default',
              }}
            >
              <div
                style={{
                  width: active ? 10 : 8,
                  height: active ? 10 : 8,
                  borderRadius: '50%',
                  background: done
                    ? 'var(--accent-green)'
                    : active
                    ? 'var(--accent-blue)'
                    : 'var(--border-default)',
                  boxShadow: active
                    ? '0 0 8px rgba(88,166,255,0.6)'
                    : 'none',
                  transition: 'all 0.2s',
                }}
              />
              <span
                style={{
                  fontSize: 9,
                  color: active
                    ? 'var(--accent-blue)'
                    : done
                    ? 'var(--accent-green)'
                    : 'var(--text-muted)',
                  whiteSpace: 'nowrap',
                  fontWeight: active ? 600 : 400,
                }}
              >
                {s.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                style={{
                  width: 20,
                  height: 1,
                  marginBottom: 14,
                  background: done
                    ? 'var(--accent-green)'
                    : 'var(--border-default)',
                  transition: 'background 0.2s',
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
