'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import type { RadarChartData, ScoringSignal, FollowUpQuestion, WhatIfData } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';

const WHATIF_FIELDS: { id: string; label: string; options: string[] }[] = [
  { id: 'lob_count',       label: 'LOB count',     options: ['1', '2-5', '6-10', '10+'] },
  { id: 'autonomy_model',  label: 'Autonomy',       options: ['full', 'hitl', 'supervised'] },
  { id: 'governance_model',label: 'Governance',     options: ['centralized', 'federated', 'undecided'] },
  { id: 'compliance_regime',label: 'Compliance',    options: ['none', 'soc2', 'hipaa', 'pci_dss', 'gdpr', 'fedramp'] },
  { id: 'cost_sensitivity',label: 'Cost priority',  options: ['primary', 'secondary', 'optimize_later'] },
];

interface RadarChartProps {
  data: RadarChartData | null;
  onConfirm: (choice: string) => void;
  streaming: boolean;
  onWhatIf?: (overrides: Record<string, string>) => void;
  whatIfData?: WhatIfData | null;
  whatIfLoading?: boolean;
}

export function RadarChart({ data, onConfirm, streaming, onWhatIf, whatIfData, whatIfLoading }: RadarChartProps) {
  const [whatIfExpanded, setWhatIfExpanded] = useState(false);
  const [whatIfOverrides, setWhatIfOverrides] = useState<Record<string, string>>({});
  const [answeredQuestions, setAnsweredQuestions] = useState<Record<string, string>>({});
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce what-if calls as user changes controls
  const handleOverrideChange = useCallback((fieldId: string, value: string) => {
    setWhatIfOverrides((prev) => {
      const next = { ...prev, [fieldId]: value };
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        if (onWhatIf && Object.keys(next).length > 0) onWhatIf(next);
      }, 350);
      return next;
    });
  }, [onWhatIf]);

  // Reset what-if state when base data changes (new session)
  useEffect(() => {
    setWhatIfExpanded(false);
    setWhatIfOverrides({});
  }, [data?.recommended_pattern]);
  if (!data || !data.patterns || !data.axes) {
    return (
      <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className="skeleton" style={{ height: 320, borderRadius: 12 }} />
        <div className="skeleton" style={{ height: 80 }} />
      </div>
    );
  }

  const selected = data.patterns.find((p) => p.selected);
  const confPct = Math.round(data.confidence * 100);
  const confColor = data.confidence > 0.6 ? 'var(--accent-green)' : data.confidence > 0.3 ? 'var(--accent-orange)' : 'var(--accent-red)';
  const confLabel = data.confidence > 0.6 ? 'High Confidence' : data.confidence > 0.3 ? 'Consider Hybrid' : 'Low Confidence';

  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>Pattern Scoring</h2>
        <Badge color={data.confidence > 0.6 ? 'green' : data.confidence > 0.3 ? 'orange' : 'red'}>
          {confLabel} {confPct}%
        </Badge>
      </div>

      {/* SVG Radar Chart */}
      <Card style={{ padding: 16, display: 'flex', justifyContent: 'center' }}>
        <RadarSVG data={data} />
      </Card>

      {/* Winner card + score comparison bars */}
      {selected && (
        <Card glow style={{ padding: 16, borderColor: selected.color + '44' }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Recommended Pattern</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: selected.color }}>{selected.name}</div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4, marginBottom: 12 }}>
            Total score: <strong style={{ color: selected.color }}>{selected.total.toFixed(2)}</strong>
          </div>
          {/* Score comparison bars */}
          {(() => {
            const sorted = [...data.patterns].sort((a, b) => b.total - a.total);
            const max = sorted[0]?.total || 1;
            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {sorted.map((p) => (
                  <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 11, color: p.selected ? p.color : 'var(--text-muted)', width: 140, flexShrink: 0, fontWeight: p.selected ? 600 : 400 }}>
                      {p.name}{p.selected ? ' ✓' : ''}
                    </span>
                    <div style={{ flex: 1, height: 8, background: 'var(--bg-surface)', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{
                        width: `${Math.max(0, (p.total / max) * 100)}%`,
                        height: '100%',
                        background: p.color,
                        borderRadius: 4,
                        opacity: p.selected ? 1 : 0.4,
                      }} />
                    </div>
                    <span style={{ fontSize: 11, color: p.selected ? p.color : 'var(--text-muted)', width: 32, textAlign: 'right', fontWeight: p.selected ? 600 : 400 }}>
                      {p.total.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            );
          })()}
          {data.runner_up && (
            <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-muted)', borderTop: '1px solid var(--border-default)', paddingTop: 8 }}>
              Runner-up: <strong style={{ color: 'var(--text-secondary)' }}>{data.runner_up.pattern_name}</strong> — gap of{' '}
              <strong>{(selected.total - data.runner_up.total).toFixed(2)}</strong> points
            </div>
          )}
        </Card>
      )}

      {/* How we derived this — signal derivation table */}
      {data.signals && data.signals.length > 0 && (
        <Card style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-default)', background: 'var(--bg-elevated)' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
              How we chose {data.pattern_name ?? 'this pattern'}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
              Your {data.signals.length} intake answers were scored against the knowledge graph. Top drivers:
            </div>
          </div>
          <div style={{ overflowY: 'auto', maxHeight: 360 }}>
            {data.signals.map((s, i) => (
              <SignalCard key={i} signal={s} patternName={data.pattern_name} />
            ))}
          </div>
        </Card>
      )}

      {/* P2: Follow-up validation questions */}
      {data.follow_up_questions && data.follow_up_questions.length > 0 && (
        <FollowUpSection
          questions={data.follow_up_questions}
          answered={answeredQuestions}
          onAnswer={(id, answer) => {
            setAnsweredQuestions((prev) => ({ ...prev, [id]: answer }));
            onConfirm(answer);
          }}
        />
      )}

      {/* P4: What-If scenario panel */}
      {onWhatIf && (
        <WhatIfPanel
          expanded={whatIfExpanded}
          onToggle={() => setWhatIfExpanded((v) => !v)}
          overrides={whatIfOverrides}
          onOverrideChange={handleOverrideChange}
          baseAnswers={data}
          whatIfData={whatIfData ?? null}
          loading={whatIfLoading ?? false}
        />
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 10 }}>
        <Button variant="primary" onClick={() => onConfirm('Confirm')} style={{ flex: 1 }}>
          Confirm This Pattern
        </Button>
        <Button variant="ghost" onClick={() => onConfirm('Adjust')}>
          Let Me Adjust
        </Button>
      </div>
    </div>
  );
}

function SignalCard({ signal, patternName }: { signal: ScoringSignal; patternName?: string }) {
  const isPositive = signal.direction === 'positive';
  const barColor = isPositive ? 'var(--accent-green)' : 'var(--accent-red)';
  const icon = isPositive ? '▲' : '▽';
  const strengthLabel = Math.abs(signal.contribution) > 0.15
    ? 'Strong'
    : Math.abs(signal.contribution) > 0.06
    ? 'Moderate'
    : 'Weak';

  return (
    <div style={{
      padding: '10px 14px',
      borderBottom: '1px solid var(--border-default)',
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
    }}>
      {/* Row 1: signal name + direction badge */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
          {signal.signal}
        </span>
        <span style={{
          fontSize: 10,
          color: barColor,
          border: `1px solid ${barColor}`,
          borderRadius: 4,
          padding: '1px 6px',
          flexShrink: 0,
          fontWeight: 600,
        }}>
          {icon} {isPositive ? 'Favors' : 'Against'} {isPositive ? (patternName ?? 'this') : (signal.steers_toward ?? 'alternative')}
        </span>
      </div>

      {/* Row 2: your answer + strength bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>Your answer:</span>
        <span style={{
          fontSize: 11,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-default)',
          borderRadius: 4,
          padding: '1px 6px',
          color: 'var(--text-secondary)',
          fontFamily: 'monospace',
        }}>
          {signal.value}
        </span>
        <div style={{ flex: 1, height: 5, background: 'var(--bg-surface)', borderRadius: 3, overflow: 'hidden', minWidth: 40 }}>
          <div style={{
            width: `${Math.min(Math.round(Math.abs(signal.contribution) * 500), 100)}%`,
            height: '100%',
            background: barColor,
            borderRadius: 3,
          }} />
        </div>
        <span style={{ fontSize: 10, color: 'var(--text-muted)', flexShrink: 0 }}>{strengthLabel}</span>
      </div>

      {/* Row 3: reason (if available) */}
      {signal.reason && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5, paddingLeft: 2 }}>
          {signal.reason}
        </div>
      )}
    </div>
  );
}

function RadarSVG({ data }: { data: RadarChartData }) {
  const size = 260;
  const cx = size / 2;
  const cy = size / 2;
  const r = 90;
  const n = data.axes.length;

  function axisPoint(i: number, radius: number) {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
  }

  function polygonPoints(scores: number[]): string {
    return scores
      .map((s, i) => {
        const { x, y } = axisPoint(i, (s / 10) * r);
        return `${x},${y}`;
      })
      .join(' ');
  }

  const gridLevels = [0.25, 0.5, 0.75, 1];

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {gridLevels.map((lvl) => (
        <polygon
          key={lvl}
          points={Array.from({ length: n }, (_, i) => {
            const { x, y } = axisPoint(i, r * lvl);
            return `${x},${y}`;
          }).join(' ')}
          fill="none"
          stroke="var(--border-default)"
          strokeWidth={0.5}
        />
      ))}
      {data.axes.map((_, i) => {
        const outer = axisPoint(i, r);
        return <line key={i} x1={cx} y1={cy} x2={outer.x} y2={outer.y} stroke="var(--border-default)" strokeWidth={0.5} />;
      })}
      {data.patterns.map((p) => (
        <polygon
          key={p.name}
          points={polygonPoints(p.scores)}
          fill={p.selected ? `${p.color}33` : `${p.color}15`}
          stroke={p.color}
          strokeWidth={p.selected ? 2 : 1}
          style={{ filter: p.selected ? `drop-shadow(0 0 6px ${p.color}88)` : 'none' }}
        />
      ))}
      {data.axes.map((axis, i) => {
        const { x, y } = axisPoint(i, r + 18);
        return (
          <text key={axis} x={x} y={y} textAnchor="middle" dominantBaseline="middle"
            fontSize={9} fill="var(--text-secondary)" fontFamily="inherit">
            {axis}
          </text>
        );
      })}
    </svg>
  );
}

// ── P2: Follow-up validation questions ───────────────────────────────────────

function FollowUpSection({
  questions,
  answered,
  onAnswer,
}: {
  questions: FollowUpQuestion[];
  answered: Record<string, string>;
  onAnswer: (id: string, answer: string) => void;
}) {
  return (
    <Card style={{ padding: 0, overflow: 'hidden' }}>
      <div style={{
        padding: '10px 14px',
        borderBottom: '1px solid var(--border-default)',
        background: 'var(--bg-elevated)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
          Validation Questions
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          — help us validate this recommendation before you proceed
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {questions.map((q) => (
          <div key={q.id} style={{
            padding: '12px 14px',
            borderBottom: '1px solid var(--border-default)',
          }}>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8, lineHeight: 1.5 }}>
              {q.question}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {q.options.map((opt) => {
                const isSelected = answered[q.id] === opt;
                return (
                  <button
                    key={opt}
                    onClick={() => onAnswer(q.id, opt)}
                    style={{
                      fontSize: 11, padding: '4px 10px', borderRadius: 6,
                      border: `1px solid ${isSelected ? 'var(--accent-blue)' : 'var(--border-default)'}`,
                      background: isSelected ? 'var(--accent-blue)22' : 'var(--bg-elevated)',
                      color: isSelected ? 'var(--accent-blue)' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                      fontWeight: isSelected ? 600 : 400,
                    }}
                  >
                    {opt}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── P4: What-If scenario panel ────────────────────────────────────────────────

function WhatIfPanel({
  expanded,
  onToggle,
  overrides,
  onOverrideChange,
  baseAnswers,
  whatIfData,
  loading,
}: {
  expanded: boolean;
  onToggle: () => void;
  overrides: Record<string, string>;
  onOverrideChange: (id: string, value: string) => void;
  baseAnswers: RadarChartData;
  whatIfData: WhatIfData | null;
  loading: boolean;
}) {
  return (
    <Card style={{ padding: 0, overflow: 'hidden' }}>
      {/* Toggle header */}
      <button
        onClick={onToggle}
        style={{
          width: '100%', padding: '10px 14px',
          background: 'var(--bg-elevated)',
          border: 'none', borderBottom: expanded ? '1px solid var(--border-default)' : 'none',
          cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 8,
          textAlign: 'left',
        }}
      >
        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
          What-If Scenarios
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', flex: 1 }}>
          — tweak constraints to see how the recommendation changes
        </span>
        <span style={{ fontSize: 11, color: 'var(--accent-blue)' }}>{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Controls */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {WHATIF_FIELDS.map((field) => (
              <div key={field.id}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
                  {field.label}
                </div>
                <select
                  value={overrides[field.id] ?? ''}
                  onChange={(e) => onOverrideChange(field.id, e.target.value)}
                  style={{
                    width: '100%', padding: '5px 8px',
                    background: 'var(--bg-elevated)',
                    border: overrides[field.id] ? '1px solid var(--accent-blue)' : '1px solid var(--border-default)',
                    borderRadius: 6,
                    color: 'var(--text-secondary)',
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  <option value="">— unchanged —</option>
                  {field.options.map((o) => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>

          {/* Result */}
          {loading && (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', padding: 8 }}>
              Re-scoring…
            </div>
          )}

          {!loading && whatIfData && (
            <WhatIfResult data={whatIfData} />
          )}

          {!loading && Object.keys(overrides).length > 0 && !whatIfData && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center' }}>
              Adjust a field above to see the impact.
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function WhatIfResult({ data }: { data: WhatIfData }) {
  const deltaSign = data.confidence_delta >= 0 ? '+' : '';
  const deltaPct  = `${deltaSign}${Math.round(data.confidence_delta * 100)}%`;
  const deltaColor = data.confidence_delta >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Diff summary */}
      <div style={{
        padding: '10px 14px',
        background: data.pattern_changed ? 'var(--accent-orange)11' : 'var(--accent-green)11',
        border: `1px solid ${data.pattern_changed ? 'var(--accent-orange)44' : 'var(--accent-green)44'}`,
        borderRadius: 8,
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div style={{ flex: 1 }}>
          {data.pattern_changed ? (
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              Pattern shifts to{' '}
              <strong style={{ color: 'var(--accent-orange)' }}>{data.whatif_pattern_name}</strong>
              {' '}({Math.round(data.whatif_confidence * 100)}% confidence)
            </div>
          ) : (
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              Pattern stays <strong style={{ color: 'var(--accent-green)' }}>{data.whatif_pattern_name}</strong>
            </div>
          )}
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 16, fontWeight: 800, color: deltaColor }}>{deltaPct}</div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>confidence</div>
        </div>
      </div>

      {/* What-if radar overlay */}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <WhatIfRadarOverlay original={null} whatIf={data} />
      </div>
    </div>
  );
}

function WhatIfRadarOverlay({ whatIf }: { original: null; whatIf: WhatIfData }) {
  const size = 200;
  const cx = size / 2;
  const cy = size / 2;
  const r = 70;
  const n = whatIf.axes.length;

  function axisPoint(i: number, radius: number) {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
  }

  function polygonPoints(scores: number[]) {
    return scores.map((s, i) => {
      const { x, y } = axisPoint(i, (s / 10) * r);
      return `${x},${y}`;
    }).join(' ');
  }

  const gridLevels = [0.25, 0.5, 0.75, 1];

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {gridLevels.map((lvl) => (
        <polygon key={lvl}
          points={Array.from({ length: n }, (_, i) => {
            const { x, y } = axisPoint(i, r * lvl);
            return `${x},${y}`;
          }).join(' ')}
          fill="none" stroke="var(--border-default)" strokeWidth={0.5}
        />
      ))}
      {whatIf.axes.map((_, i) => {
        const outer = axisPoint(i, r);
        return <line key={i} x1={cx} y1={cy} x2={outer.x} y2={outer.y} stroke="var(--border-default)" strokeWidth={0.5} />;
      })}
      {whatIf.patterns.map((p) => (
        <polygon key={p.name}
          points={polygonPoints(p.scores)}
          fill={p.selected ? `${p.color}44` : `${p.color}18`}
          stroke={p.color}
          strokeWidth={p.selected ? 2 : 1}
          strokeDasharray={p.selected ? '4,2' : '2,2'}
        />
      ))}
      {whatIf.axes.map((axis, i) => {
        const { x, y } = axisPoint(i, r + 16);
        return (
          <text key={axis} x={x} y={y} textAnchor="middle" dominantBaseline="middle"
            fontSize={8} fill="var(--text-muted)" fontFamily="inherit">
            {axis}
          </text>
        );
      })}
    </svg>
  );
}

export default RadarChart;
