'use client';

import type { RequirementsData } from '@/lib/types';

export function RequirementsPanel({ data }: { data: RequirementsData | null }) {
  if (!data) return <div style={{ padding: 20 }}><div className="skeleton" style={{ height: 280 }} /></div>;
  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <h2 className="text-panel-title">Architecture Requirements</h2>
      <div style={{ borderTop: '1px solid var(--border-default)' }}>
        {data.requirements.map((requirement) => (
          <div key={requirement.id} style={{ display: 'grid', gridTemplateColumns: '110px 1fr 54px', gap: 12, alignItems: 'start', padding: '11px 0', borderBottom: '1px solid var(--border-default)' }}>
            <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{requirement.category}</span>
            <div>
              <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>{requirement.statement}</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>{requirement.evidence.join(', ')}</div>
            </div>
            <span style={{ fontSize: 10, color: requirement.hard ? 'var(--danger)' : 'var(--text-muted)' }}>{requirement.hard ? 'HARD' : 'SOFT'}</span>
          </div>
        ))}
      </div>
      {data.assumptions.length > 0 && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 6 }}>Explicit Assumptions</div>
          {data.assumptions.map((assumption) => <div key={assumption} style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>• {assumption}</div>)}
        </div>
      )}
    </div>
  );
}
