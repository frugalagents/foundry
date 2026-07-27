'use client';
import { useState } from 'react';
import type { InnovationOverlayData } from '@/lib/types';
import { ArchitectureDiagram } from './ArchitectureDiagram';
import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';

export function InnovationOverlay({ data, streaming }: { data: InnovationOverlayData | null; streaming: boolean }) {
  const [view, setView] = useState<'after' | 'before'>('after');
  const [disabled, setDisabled] = useState<Set<string>>(new Set());

  if (!data || !data.innovations) {
    return (
      <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className="skeleton" style={{ height: 200 }} />
        <div className="skeleton" style={{ height: 100 }} />
      </div>
    );
  }

  const statusBadge = { ga: 'green', preview: 'orange', emerging: 'purple' } as const;
  const statusLabel = { ga: 'GA ✓', preview: 'Preview ⚠', emerging: 'Emerging 🔬' };

  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>Innovation Overlay</h2>
        <div style={{ display: 'flex', gap: 4, background: 'var(--bg-elevated)', borderRadius: 6, padding: 2 }}>
          {(['after', 'before'] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              style={{
                padding: '4px 12px',
                borderRadius: 4,
                fontSize: 12,
                border: 'none',
                background: view === v ? 'var(--accent-blue)' : 'transparent',
                color: view === v ? '#fff' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontWeight: view === v ? 600 : 400,
              }}
            >
              {v === 'after' ? 'With Innovations' : 'Original'}
            </button>
          ))}
        </div>
      </div>

      <ArchitectureDiagram
        data={view === 'after' ? data.after_architecture : data.before_architecture}
        compact
      />

      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
        Applied Innovations ({data.innovations.length})
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {data.innovations.map((inn) => {
          const isDisabled = disabled.has(inn.name);
          return (
            <Card
              key={inn.name}
              style={{
                padding: 14,
                opacity: isDisabled ? 0.5 : 1,
                transition: 'opacity 0.2s',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
                <div>
                  <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{inn.name}</span>
                  <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                    <Badge color={statusBadge[inn.status]} size="sm">{statusLabel[inn.status]}</Badge>
                    <Badge color="blue" size="sm">{inn.aws_implementation}</Badge>
                  </div>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 12, color: 'var(--text-muted)' }}>
                  <input
                    type="checkbox"
                    checked={!isDisabled}
                    onChange={() => {
                      const next = new Set(disabled);
                      if (isDisabled) next.delete(inn.name); else next.add(inn.name);
                      setDisabled(next);
                    }}
                  />
                  Enabled
                </label>
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', fontStyle: 'italic', marginBottom: 6 }}>
                Solves: "{inn.constraint_solved}"
              </p>
              {inn.replaces && (
                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Replaces: {inn.replaces}</p>
              )}
              {inn.enables && (
                <p style={{ fontSize: 12, color: 'var(--accent-cyan)' }}>Enables: {inn.enables}</p>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export default InnovationOverlay;
