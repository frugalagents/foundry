'use client';
import type { CostEstimateData, CostLineItem } from '@/lib/types';

const COMPLEXITY_COLOR: Record<string, string> = {
  low: 'var(--success)',
  medium: 'var(--warning)',
  high: 'var(--danger)',
};

const COMPLEXITY_TINT: Record<string, string> = {
  low: 'var(--success-subtle)',
  medium: 'var(--warning-subtle)',
  high: 'var(--danger-subtle)',
};

const TIER_LABEL: Record<number, string> = { 1: 'T1', 2: 'T2', 3: 'T3' };

function SavingsBar({ label, without, with: withVal }: { label: string; without: number; with: number }) {
  const max = without;
  const savePct = max > 0 ? Math.round(((max - withVal) / max) * 100) : 0;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ flex: 1, height: 8, borderRadius: 4, background: 'var(--bg-elevated)', overflow: 'hidden', display: 'flex' }}>
          <div style={{ width: `${Math.round((withVal / max) * 100)}%`, background: 'var(--accent-green)', borderRadius: 4 }} />
        </div>
        <span style={{ fontSize: 12, color: 'var(--accent-green)', fontWeight: 600, minWidth: 40 }}>-{savePct}%</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
        <span>Optimized: <strong style={{ color: 'var(--text-primary)' }}>${withVal.toLocaleString()}/mo</strong></span>
        <span>Without: <strong style={{ color: 'var(--accent-red)' }}>${without.toLocaleString()}/mo</strong></span>
      </div>
    </div>
  );
}

function ComponentRow({ item }: { item: CostLineItem }) {
  const implWeeks = item.weeks_min === item.weeks_max
    ? `${item.weeks_min}w`
    : `${item.weeks_min}-${item.weeks_max}w`;

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 80px 60px 80px 100px',
      alignItems: 'center',
      padding: '10px 14px',
      borderBottom: '1px solid var(--border-default)',
      gap: 8,
    }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', marginBottom: 1 }}>
          {item.name}
          <span style={{
            marginLeft: 6, fontSize: 10, fontWeight: 600,
            color: 'var(--text-muted)', padding: '1px 5px',
            border: '1px solid var(--border-default)', borderRadius: 4,
          }}>{TIER_LABEL[item.tier] ?? 'T1'}</span>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.3 }}>
          {item.aws_service}
        </div>
      </div>
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', textAlign: 'right' }}>
        {item.monthly_fmt}
      </div>
      <div style={{ textAlign: 'right' }}>
        <span style={{
          fontSize: 10, fontWeight: 600,
          color: COMPLEXITY_COLOR[item.complexity] ?? 'var(--text-muted)',
          padding: '2px 5px', borderRadius: 3,
          background: COMPLEXITY_TINT[item.complexity] ?? 'var(--bg-hover)',
        }}>{item.complexity}</span>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', textAlign: 'center' }}>
        {implWeeks} · {item.team_size} {item.team_size === 1 ? 'eng' : 'engs'}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'right', lineHeight: 1.3, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {item.workshop_hint ? (
          <span title={item.workshop_hint} style={{ cursor: 'help', textDecoration: 'underline dotted' }}>
            workshop
          </span>
        ) : null}
      </div>
    </div>
  );
}

export function CostEstimatePanel({ data, streaming }: { data: CostEstimateData | null; streaming: boolean }) {
  if (!data || !data.line_items) {
    return (
      <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className="skeleton" style={{ height: 100 }} />
        <div className="skeleton" style={{ height: 300 }} />
      </div>
    );
  }

  const sortedItems = [...data.line_items].sort((a, b) => b.monthly_usd - a.monthly_usd);
  const maxCost = sortedItems[0]?.monthly_usd ?? 1;

  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header summary */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border-default)',
          borderRadius: 10, padding: '14px 16px',
        }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>
            Platform / Month
          </div>
          <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)' }}>
            {data.total_monthly_fmt}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
            ~{data.agent_count_assumed} agents assumed
          </div>
        </div>

        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border-default)',
          borderRadius: 10, padding: '14px 16px',
        }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>
            Annual Run Rate
          </div>
          <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-primary)' }}>
            {data.total_annual_fmt}
          </div>
          {data.compliance_uplift_pct > 0 && (
            <div style={{ fontSize: 11, color: 'var(--accent-orange)', marginTop: 2 }}>
              incl. {data.compliance_uplift_pct}% compliance uplift
            </div>
          )}
        </div>

        <div style={{
          background: data.has_cost_engine ? 'var(--accent-green)11' : 'var(--bg-card)',
          border: `1px solid ${data.has_cost_engine ? 'var(--accent-green)44' : 'var(--border-default)'}`,
          borderRadius: 10, padding: '14px 16px',
        }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>
            LLM Savings / Year
          </div>
          {data.has_cost_engine && data.llm_savings_annual > 0 ? (
            <>
              <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--accent-green)' }}>
                ${(data.llm_savings_annual / 1000).toFixed(0)}K
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                via intelligent routing + semantic cache
              </div>
            </>
          ) : (
            <>
              <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-muted)' }}>—</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                add Cost Engine to unlock savings
              </div>
            </>
          )}
        </div>
      </div>

      {/* LLM routing savings visualization */}
      {data.has_cost_engine && data.llm_cost_unoptimized_monthly > 0 && (
        <div style={{
          background: 'var(--bg-card)', border: '1px solid var(--border-default)',
          borderRadius: 10, padding: 16,
        }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
            Bedrock LLM Cost Optimization
          </div>
          <SavingsBar
            label="Monthly LLM spend with vs. without intelligent routing"
            without={data.llm_cost_unoptimized_monthly}
            with={data.llm_cost_optimized_monthly}
          />
        </div>
      )}

      {/* Component cost breakdown */}
      <div style={{
        background: 'var(--bg-card)', border: '1px solid var(--border-default)',
        borderRadius: 10, overflow: 'hidden',
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 80px 60px 80px 100px',
          padding: '8px 14px',
          borderBottom: '1px solid var(--border-default)',
          background: 'var(--bg-elevated)',
        }}>
          {['Component', 'Monthly', 'Effort', 'Impl.', 'Resources'].map((h) => (
            <div key={h} style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', textAlign: h === 'Component' ? 'left' : 'right' }}>
              {h}
            </div>
          ))}
        </div>

        {sortedItems.map((item) => (
          <ComponentRow key={item.id} item={item} />
        ))}

        {/* Total row */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 80px 60px 80px 100px',
          alignItems: 'center',
          padding: '12px 14px',
          borderTop: '2px solid var(--border-default)',
          background: 'var(--bg-elevated)',
          gap: 8,
        }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
            Total
            {data.compliance_uplift_usd > 0 && (
              <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 6 }}>
                (incl. ${Math.round(data.compliance_uplift_usd)} compliance uplift)
              </span>
            )}
          </div>
          <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--accent-blue)', textAlign: 'right' }}>
            {data.total_monthly_fmt}
          </div>
          <div />
          <div style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
            {data.total_team_weeks} eng-weeks
          </div>
          <div />
        </div>
      </div>

      {/* Horizontal cost bar chart */}
      <div style={{
        background: 'var(--bg-card)', border: '1px solid var(--border-default)',
        borderRadius: 10, padding: 16,
      }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
          Cost Distribution by Component
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {sortedItems.map((item) => {
            const pct = maxCost > 0 ? (item.monthly_usd / maxCost) * 100 : 0;
            return (
              <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 90, fontSize: 12, color: 'var(--text-secondary)', textAlign: 'right', flexShrink: 0 }}>
                  {item.name}
                </div>
                <div style={{ flex: 1, height: 18, background: 'var(--bg-elevated)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{
                    width: `${pct}%`, height: '100%',
                    background: 'var(--accent-blue)',
                    borderRadius: 3, minWidth: 2,
                    opacity: 0.7 + (pct / 100) * 0.3,
                  }} />
                </div>
                <div style={{ width: 55, fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', textAlign: 'right', flexShrink: 0 }}>
                  {item.monthly_fmt}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Implementation summary */}
      <div style={{
        background: 'var(--bg-card)', border: '1px solid var(--border-default)',
        borderRadius: 10, padding: 16,
      }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 10 }}>
          Implementation Summary
        </div>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
          {data.phase_timeline_weeks.map((pt) => (
            <div key={pt.phase_id} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                {pt.phase_id}
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
                {pt.duration_label}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                {pt.components.length} component{pt.components.length !== 1 ? 's' : ''}
              </div>
            </div>
          ))}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginLeft: 'auto' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Total Effort
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
              {data.total_team_weeks} eng-weeks
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              across all phases
            </div>
          </div>
        </div>
      </div>

      {data.compliance_note && (
        <div style={{
          padding: '10px 14px',
          background: 'var(--accent-orange)11',
          border: '1px solid var(--accent-orange)33',
          borderRadius: 8,
          fontSize: 12,
          color: 'var(--text-secondary)',
        }}>
          <strong>Compliance note:</strong> {data.compliance_note}
        </div>
      )}
    </div>
  );
}
