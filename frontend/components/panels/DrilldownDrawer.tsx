'use client';
import { useEffect, useRef } from 'react';
import type { DrilldownData, DrilldownTierOption } from '@/lib/types';

const EFFORT_COLOR: Record<string, string> = {
  low:    'var(--accent-green)',
  medium: 'var(--accent-orange)',
  high:   'var(--accent-red)',
};

const COMPLEXITY_BG: Record<string, string> = {
  low:    'var(--accent-green)',
  medium: 'var(--accent-orange)',
  high:   'var(--accent-red)',
};

const TIER_STROKE: Record<number, string> = {
  1: 'var(--tier-1)',
  2: 'var(--tier-2)',
  3: 'var(--tier-3)',
};

interface DrilldownDrawerProps {
  data: DrilldownData | null;
  loading: boolean;
  onClose: () => void;
}

export function DrilldownDrawer({ data, loading, onClose }: DrilldownDrawerProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <>
      {/* Dim overlay */}
      <div
        ref={overlayRef}
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(31,30,27,0.35)',
          zIndex: 1000,
          animation: 'fadeIn 0.15s ease',
        }}
      />

      {/* Drawer */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0,
        width: 540,
        background: 'var(--bg-base)',
        borderLeft: '1px solid var(--border-default)',
        zIndex: 1001,
        overflowY: 'auto',
        display: 'flex', flexDirection: 'column',
        animation: 'slideInRight 0.2s ease',
      }}>
        <style>{`
          @keyframes fadeIn { from { opacity:0 } to { opacity:1 } }
          @keyframes slideInRight { from { transform:translateX(40px); opacity:0 } to { transform:translateX(0); opacity:1 } }
        `}</style>

        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-default)',
          background: 'var(--bg-card)',
          flexShrink: 0,
          display: 'flex', alignItems: 'flex-start', gap: 12,
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span className="text-display" style={{ fontSize: 'var(--text-lg)', color: 'var(--text-primary)' }}>
                {loading ? 'Loading…' : (data?.component_name ?? 'Component')}
              </span>
              {data && (
                <span style={{
                  fontSize: 'var(--text-xs)', fontWeight: 700,
                  color: TIER_STROKE[data.tier],
                  border: `1px solid ${TIER_STROKE[data.tier]}`,
                  borderRadius: 4, padding: '1px 6px',
                }}>
                  T{data.tier}
                </span>
              )}
              {data?.layer && (
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', padding: '1px 6px', border: '1px solid var(--border-default)', borderRadius: 4 }}>
                  {data.layer}
                </span>
              )}
            </div>
            {data?.aws_service && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{data.aws_service}</div>
            )}
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none',
              color: 'var(--text-muted)', cursor: 'pointer',
              fontSize: 18, lineHeight: 1, padding: 4,
              flexShrink: 0,
            }}
          >×</button>
        </div>

        {loading && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12, color: 'var(--text-muted)' }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%',
              border: '3px solid var(--border-default)',
              borderTopColor: 'var(--accent-blue)',
              animation: 'spin 0.8s linear infinite',
            }} />
            <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
            <span style={{ fontSize: 12 }}>Fetching deep-dive…</span>
          </div>
        )}

        {!loading && data && (
          <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 20 }}>

            {/* Why you need this */}
            {data.why_needed && (
              <Section title="Why you need this">
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.65, margin: 0 }}>
                  {data.why_needed}
                </p>
              </Section>
            )}

            {/* Your cost at scale */}
            <Section title="Your cost at scale">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <CostCard label="Monthly" value={data.your_cost.monthly_fmt} color="var(--accent-blue)" />
                <CostCard label="Annual" value={data.your_cost.annual_fmt} color="var(--text-primary)" />
              </div>
              {data.your_cost.at_agents > 0 && (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                  Estimated for ~{data.your_cost.at_agents} agents
                  {data.your_cost.cost_drivers ? ` · ${data.your_cost.cost_drivers}` : ''}
                </div>
              )}
            </Section>

            {/* Tier comparison */}
            <Section title="Tier options">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {data.tier_options.map((opt) => (
                  <TierRow key={opt.tier} opt={opt} />
                ))}
              </div>
            </Section>

            {/* Implementation */}
            <Section title="Implementation">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                <StatCard label="Timeline" value={data.implementation.weeks_range} />
                <StatCard label="Team" value={`${data.implementation.team_size} eng${data.implementation.team_size !== 1 ? 's' : ''}`} />
                <StatCard
                  label="Complexity"
                  value={data.implementation.complexity}
                  color={COMPLEXITY_BG[data.implementation.complexity]}
                />
              </div>
              {data.implementation.role_mix && (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8, lineHeight: 1.5 }}>
                  {data.implementation.role_mix}
                </div>
              )}
            </Section>

            {/* CDK snippet */}
            {data.cdk_snippet && (
              <Section title="CDK v2 (TypeScript)">
                <pre style={{
                  margin: 0,
                  padding: '14px 16px',
                  background: '#0d1117',
                  border: '1px solid var(--border-default)',
                  borderRadius: 8,
                  fontSize: 11,
                  lineHeight: 1.6,
                  color: '#e6edf3',
                  overflowX: 'auto',
                  whiteSpace: 'pre',
                  fontFamily: '"SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace',
                }}>
                  <code>{data.cdk_snippet}</code>
                </pre>
              </Section>
            )}

            {/* Workshop */}
            {data.workshop?.hint && (
              <Section title="AWS Workshop">
                <div style={{
                  padding: '10px 14px',
                  background: 'var(--accent-soft)',
                  border: '1px solid var(--border-accent)',
                  borderRadius: 8,
                  fontSize: 12,
                  color: 'var(--text-secondary)',
                  lineHeight: 1.5,
                }}>
                  {data.workshop.hint}
                </div>
              </Section>
            )}

            {/* Engagement pattern */}
            {data.engagement_pattern && (
              <Section title="Similar engagements">
                <div style={{
                  padding: '10px 14px',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 8,
                  fontSize: 12,
                  color: 'var(--text-secondary)',
                  lineHeight: 1.55,
                }}>
                  {data.engagement_pattern}
                </div>
              </Section>
            )}

            {/* KB context */}
            {data.kb_context && (
              <Section title="Reference material">
                <div style={{
                  padding: '10px 14px',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 8,
                  fontSize: 11,
                  color: 'var(--text-muted)',
                  lineHeight: 1.55,
                  maxHeight: 160,
                  overflowY: 'auto',
                }}>
                  {data.kb_context}
                </div>
              </Section>
            )}
          </div>
        )}
      </div>
    </>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 8 }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function CostCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border-default)',
      borderRadius: 8, padding: '10px 12px',
    }}>
      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 20, fontWeight: 800, color }}>{value}</div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border-default)',
      borderRadius: 8, padding: '8px 10px',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 3 }}>
        {label}
      </div>
      <div style={{
        fontSize: 13, fontWeight: 700,
        color: color ?? 'var(--text-primary)',
      }}>
        {value}
      </div>
    </div>
  );
}

function TierRow({ opt }: { opt: DrilldownTierOption }) {
  const stroke = TIER_STROKE[opt.tier] ?? 'var(--text-muted)';
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '40px 1fr 70px 55px',
      alignItems: 'center',
      gap: 10,
      padding: '10px 12px',
      background: opt.is_current ? 'var(--accent-soft)' : 'var(--bg-card)',
      border: `1px solid ${opt.is_current ? stroke : 'var(--border-default)'}`,
      borderRadius: 8,
    }}>
      <span style={{ fontSize: 11, fontWeight: 700, color: stroke, textAlign: 'center' }}>
        T{opt.tier}
        {opt.is_current && <span style={{ display: 'block', fontSize: 10, fontWeight: 400, color: 'var(--text-muted)' }}>current</span>}
      </span>
      <div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>{opt.description}</div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>{opt.monthly_fmt}</div>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>/mo</div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: 'var(--text-xs)', color: EFFORT_COLOR[opt.effort] ?? 'var(--text-muted)', fontWeight: 600 }}>{opt.effort}</div>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{opt.weeks_range}</div>
      </div>
    </div>
  );
}
