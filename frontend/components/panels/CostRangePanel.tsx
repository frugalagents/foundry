'use client';

import type { CostEstimateV2 } from '@/lib/types';

const money = (value: number) => new Intl.NumberFormat('en-US', {
  style: 'currency', currency: 'USD', maximumFractionDigits: 0,
}).format(value);

export function CostRangePanel({ data }: { data: CostEstimateV2 | null }) {
  if (!data) return <div style={{ padding: 20 }}><div className="skeleton" style={{ height: 300 }} /></div>;
  const scenarios = [
    { label: 'Low', value: data.low },
    { label: 'Base', value: data.base },
    { label: 'High', value: data.high },
  ];
  return (
    <div style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h2 className="text-panel-title">Planning Cost Range</h2>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>Rate catalog dated {data.price_catalog_date}</div>
      </div>
      <div className="v2-cost-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
        {scenarios.map((scenario) => (
          <div key={scenario.label} style={{ border: '1px solid var(--border-default)', borderRadius: 6, padding: 14 }}>
            <div className="eyebrow">{scenario.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', marginTop: 4 }}>{money(scenario.value.monthly_usd)}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{money(scenario.value.annual_usd)} annually</div>
          </div>
        ))}
      </div>
      <div>
        <div className="eyebrow" style={{ marginBottom: 7 }}>Component Planning Baseline</div>
        <div style={{ borderTop: '1px solid var(--border-default)' }}>
          {data.line_items.map((item) => (
            <div key={item.id} style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--border-default)', fontSize: 12 }}>
              <div>
                <div style={{ color: 'var(--text-primary)' }}>{item.name}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: 10 }}>{item.aws_services.join(', ')}</div>
              </div>
              <strong style={{ textAlign: 'right' }}>{money(item.monthly_base_usd)}/mo</strong>
            </div>
          ))}
        </div>
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{data.assumptions.join(' • ')}</div>
      <style jsx>{`
        @media (max-width: 700px) {
          .v2-cost-grid { grid-template-columns: minmax(0, 1fr) !important; }
        }
      `}</style>
    </div>
  );
}
