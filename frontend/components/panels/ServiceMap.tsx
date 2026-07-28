'use client';
import { useState } from 'react';
import type { ServiceMapData } from '@/lib/types';
import { Badge } from '@/components/ui/Badge';

export function ServiceMap({ data, streaming }: { data: ServiceMapData | null; streaming: boolean }) {
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');

  if (!data || !data.components) {
    return (
      <div style={{ padding: 20 }}>
        <div className="skeleton" style={{ height: 300 }} />
      </div>
    );
  }

  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 className="text-panel-title">AWS Service Mapping</h2>
        <div style={{ display: 'flex', gap: 4, background: 'var(--bg-elevated)', borderRadius: 6, padding: 2 }}>
          {(['table', 'cards'] as const).map((v) => (
            <button key={v} onClick={() => setViewMode(v)}
              style={{
                padding: '3px 10px', borderRadius: 4, fontSize: 11, border: 'none',
                background: viewMode === v ? 'var(--accent)' : 'transparent',
                color: viewMode === v ? 'var(--accent-fg)' : 'var(--text-secondary)',
                cursor: 'pointer', textTransform: 'capitalize',
              }}>
              {v}
            </button>
          ))}
        </div>
      </div>

      {viewMode === 'table' ? (
        <div style={{ border: '1px solid var(--border-default)', borderRadius: 8, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: 'var(--bg-elevated)' }}>
                {['Component', 'Tier', 'AWS Services', 'Workshops'].map((h) => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.components.map((comp, i) => (
                <tr key={comp.name} style={{ borderTop: i > 0 ? '1px solid var(--border-default)' : 'none' }}>
                  <td style={{ padding: '8px 12px', color: 'var(--text-primary)', fontWeight: 500 }}>{comp.name}</td>
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{ color: `var(--tier-${comp.tier})`, fontSize: 11, border: `1px solid var(--tier-${comp.tier})`, borderRadius: 3, padding: '1px 5px' }}>
                      T{comp.tier}
                    </span>
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {comp.aws_services.map((svc) => (
                        <Badge key={svc.name} color="blue" size="sm">{svc.name}</Badge>
                      ))}
                    </div>
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {comp.workshops.slice(0, 2).map((w) => (
                        <a key={w.title} href={w.url} target="_blank" rel="noreferrer"
                          style={{ fontSize: 'var(--text-xs)', color: 'var(--accent-deep)', background: 'var(--accent-soft)', padding: '1px 6px', borderRadius: 10, border: '1px solid var(--border-accent)' }}>
                          {w.title.slice(0, 20)}…
                        </a>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {data.components.map((comp) => (
            <div key={comp.name} style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', borderRadius: 8, padding: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{comp.name}</span>
                <span style={{ fontSize: 'var(--text-xs)', color: `var(--tier-${comp.tier})`, border: `1px solid var(--tier-${comp.tier})`, borderRadius: 3, padding: '1px 5px' }}>T{comp.tier}</span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {comp.aws_services.map((svc) => (
                  <Badge key={svc.name} color="blue" size="sm">{svc.name}</Badge>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ServiceMap;
