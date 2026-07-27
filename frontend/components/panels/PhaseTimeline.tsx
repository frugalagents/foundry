'use client';
import type { PhaseTimelineData } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';

export function PhaseTimeline({ data, streaming }: { data: PhaseTimelineData | null; streaming: boolean }) {
  if (!data || !data.phases || !data.dependencies) {
    return (
      <div style={{ padding: 20 }}>
        <div className="skeleton" style={{ height: 300 }} />
      </div>
    );
  }

  const effortColors = { low: 'var(--accent-green)', medium: 'var(--accent-orange)', high: 'var(--accent-red)' };
  const phaseColors = ['var(--accent-blue)', 'var(--accent-green)', 'var(--accent-orange)', 'var(--accent-purple)'];

  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <h2 style={{ fontSize: 16, fontWeight: 600 }}>Implementation Roadmap</h2>

      {/* Gantt columns */}
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${data.phases.length}, 1fr)`, gap: 8 }}>
        {data.phases.map((phase, pi) => (
          <div key={phase.id}>
            {/* Phase header */}
            <div
              style={{
                padding: '8px 10px',
                borderRadius: '8px 8px 0 0',
                background: `${phaseColors[pi]}22`,
                border: `1px solid ${phaseColors[pi]}44`,
                borderBottom: 'none',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 700, color: phaseColors[pi] }}>{phase.id}</div>
              <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>{phase.duration}</div>
            </div>
            {/* Components */}
            <div
              style={{
                border: `1px solid ${phaseColors[pi]}44`,
                borderTop: 'none',
                borderRadius: '0 0 8px 8px',
                padding: 6,
                display: 'flex',
                flexDirection: 'column',
                gap: 5,
                minHeight: 120,
              }}
            >
              {phase.components.map((comp) => (
                <div
                  key={comp.name}
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-default)',
                    borderRadius: 5,
                    padding: '5px 7px',
                  }}
                >
                  <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 3 }}>
                    {comp.name}
                  </div>
                  <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 9, color: `var(--tier-${comp.tier})`, border: `1px solid var(--tier-${comp.tier})`, borderRadius: 3, padding: '1px 4px' }}>
                      T{comp.tier}
                    </span>
                    <span style={{ fontSize: 9, color: effortColors[comp.effort] }}>
                      {comp.effort} effort
                    </span>
                  </div>
                  {comp.aws_service && (
                    <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 2 }}>{comp.aws_service}</div>
                  )}
                </div>
              ))}
              {phase.components.length === 0 && (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', padding: 12 }}>—</div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Dependency summary */}
      {data.dependencies.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
            Key Dependencies
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {data.dependencies.map((dep, i) => (
              <div key={i} style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color: 'var(--text-primary)' }}>{dep.from}</span>
                <span>→</span>
                <span style={{ color: 'var(--text-primary)' }}>{dep.to}</span>
                {dep.reason && <span>({dep.reason})</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default PhaseTimeline;
