'use client';
import type { RiskCardsData, Risk } from '@/lib/types';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

export function RiskCards({ data, streaming }: { data: RiskCardsData | null; streaming: boolean }) {
  if (!data || !data.risks || !data.summary) {
    return (
      <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
        {[1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 80 }} />)}
      </div>
    );
  }

  const { summary, risks } = data;
  const sorted = [...risks].sort((a, b) => {
    const order = { blocked: 0, warning: 1, prevented: 2 };
    return order[a.status] - order[b.status];
  });

  const statusColor = { prevented: '#3FB950', warning: '#D29922', blocked: '#F85149' };
  const statusIcon = { prevented: '✅', warning: '⚠️', blocked: '🚫' };
  const severityBadge = { high: 'red', medium: 'orange', low: 'gray' } as const;

  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
      <h2 style={{ fontSize: 16, fontWeight: 600 }}>Risk Assessment</h2>

      {/* Summary bar */}
      <div
        style={{
          padding: '10px 14px',
          borderRadius: 8,
          background: summary.requires_attention === 0 ? 'rgba(63,185,80,0.1)' : 'rgba(210,153,34,0.1)',
          border: `1px solid ${summary.requires_attention === 0 ? 'rgba(63,185,80,0.3)' : 'rgba(210,153,34,0.3)'}`,
          fontSize: 13,
          color: 'var(--text-primary)',
          display: 'flex',
          gap: 16,
        }}
      >
        <span><strong style={{ color: 'var(--text-primary)' }}>{summary.total_detected}</strong> <span style={{ color: 'var(--text-muted)' }}>detected</span></span>
        <span><strong style={{ color: 'var(--accent-green)' }}>{summary.addressed}</strong> <span style={{ color: 'var(--text-muted)' }}>addressed</span></span>
        {summary.requires_attention > 0 && (
          <span><strong style={{ color: 'var(--accent-orange)' }}>{summary.requires_attention}</strong> <span style={{ color: 'var(--text-muted)' }}>requires attention</span></span>
        )}
      </div>

      {/* Risk cards */}
      {sorted.map((risk, i) => (
        <div
          key={`${risk.name}-${i}`}
          style={{
            borderRadius: 8,
            border: '1px solid var(--border-default)',
            borderLeft: `3px solid ${statusColor[risk.status]}`,
            background: 'var(--bg-card)',
            padding: '12px 14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 6 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>{statusIcon[risk.status]}</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{risk.name}</span>
            </div>
            <Badge color={severityBadge[risk.severity]} size="sm">{risk.severity}</Badge>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
            {risk.trigger_condition}
          </p>
          {risk.status === 'prevented' && risk.prevented_by && (
            <p style={{ fontSize: 12, color: 'var(--accent-green)' }}>
              Addressed by <strong>{risk.prevented_by}</strong>
            </p>
          )}
          {risk.status === 'warning' && risk.recommended_fix && (
            <p style={{ fontSize: 12, color: 'var(--accent-orange)' }}>
              Fix: {risk.recommended_fix}
            </p>
          )}
          {risk.status === 'blocked' && (
            <p style={{ fontSize: 12, color: 'var(--accent-red)', fontWeight: 600 }}>
              Action required to proceed
            </p>
          )}
        </div>
      ))}

      {risks.length === 0 && (
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>
          No risks detected for this configuration.
        </div>
      )}
    </div>
  );
}

export default RiskCards;
