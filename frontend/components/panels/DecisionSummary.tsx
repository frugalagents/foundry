'use client';

import { useState } from 'react';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import type { DecisionSummaryData } from '@/lib/types';
import { Button } from '@/components/ui/Button';

export function DecisionSummary({
  data,
  onOverride,
}: {
  data: DecisionSummaryData | null;
  onOverride?: (path: string, value: string, rationale: string, engineValue: string) => void;
}) {
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [overrideValue, setOverrideValue] = useState('');
  const [rationale, setRationale] = useState('');

  if (!data) return <div style={{ padding: 20 }}><div className="skeleton" style={{ height: 320 }} /></div>;
  const coverage = Math.round(data.evidence_coverage * 100);

  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
        <div>
          <div className="eyebrow">Operating Model</div>
          <h2 className="text-display" style={{ fontSize: 'var(--text-xl)', textTransform: 'capitalize', marginTop: 3 }}>
            {data.operating_model ?? 'Provisional'}
          </h2>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 20, fontWeight: 700, color: coverage === 100 ? 'var(--success)' : 'var(--warning)' }}>{coverage}%</div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>evidence complete</div>
        </div>
      </div>

      {data.status === 'needs_information' && (
        <div style={{ display: 'flex', gap: 8, padding: 12, border: '1px solid var(--warning)', borderRadius: 6, background: 'var(--warning-subtle)' }}>
          <AlertTriangle size={16} color="var(--warning)" />
          <div style={{ fontSize: 12 }}>
            Blueprint blocked until {data.missing_evidence.length} critical evidence item{data.missing_evidence.length === 1 ? '' : 's'} are resolved.
          </div>
        </div>
      )}

      <section>
        <div className="eyebrow" style={{ marginBottom: 8 }}>Capability Ownership</div>
        <div style={{ borderTop: '1px solid var(--border-default)' }}>
          {data.ownership_matrix.map((row) => (
            <div key={row.capability} style={{ display: 'grid', gridTemplateColumns: '1fr 140px', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--border-default)', fontSize: 12 }}>
              <span style={{ color: 'var(--text-secondary)' }}>{row.capability.replaceAll('_', ' ')}</span>
              <strong style={{ color: 'var(--text-primary)', textTransform: 'capitalize' }}>{row.owner}</strong>
            </div>
          ))}
        </div>
      </section>

      {data.topology && (
        <section>
          <div className="eyebrow" style={{ marginBottom: 8 }}>Technical Topology</div>
          <div className="v2-topology-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
            {Object.entries(data.topology).filter(([key]) => key !== 'modifiers').map(([key, value]) => (
              <div key={key} style={{ border: '1px solid var(--border-default)', borderRadius: 6, padding: 10 }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{key.replaceAll('_', ' ')}</div>
                <div style={{ fontSize: 12, color: 'var(--text-primary)', marginTop: 3 }}>{String(value).replaceAll('_', ' ')}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {data.status === 'overridden' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, color: 'var(--warning)' }}>
          <CheckCircle2 size={15} /> Recorded human override applied; the engine result remains in the audit trace.
        </div>
      )}

      {onOverride && data.operating_model && data.status !== 'needs_information' && (
        <div style={{ borderTop: '1px solid var(--border-default)', paddingTop: 12 }}>
          {!overrideOpen ? (
            <Button variant="secondary" onClick={() => setOverrideOpen(true)}>Record architecture override</Button>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <select value={overrideValue} onChange={(event) => setOverrideValue(event.target.value)} style={{ minHeight: 38, border: '1px solid var(--border-default)', borderRadius: 6, padding: 8, background: 'var(--bg-card)' }}>
                <option value="">Select operating model</option>
                {['centralized', 'federated', 'decentralized'].filter((item) => item !== data.operating_model).map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
              <textarea
                value={rationale}
                onChange={(event) => setRationale(event.target.value)}
                placeholder="Required rationale and accountability change"
                rows={3}
                style={{ border: '1px solid var(--border-default)', borderRadius: 6, padding: 8, resize: 'vertical', background: 'var(--bg-card)' }}
              />
              <div style={{ display: 'flex', gap: 8 }}>
                <Button variant="primary" disabled={!overrideValue || rationale.trim().length < 10} onClick={() => onOverride('operating_model', overrideValue, rationale.trim(), data.operating_model!)}>
                  Apply and recompute
                </Button>
                <Button variant="ghost" onClick={() => setOverrideOpen(false)}>Cancel</Button>
              </div>
            </div>
          )}
        </div>
      )}
      <style jsx>{`
        @media (max-width: 700px) {
          .v2-topology-grid { grid-template-columns: minmax(0, 1fr) !important; }
        }
      `}</style>
    </div>
  );
}
