'use client';
import type { ArchitectureDiagramData, ArchitectureComponent } from '@/lib/types';
import { Button } from '@/components/ui/Button';

interface ArchitectureDiagramProps {
  data: ArchitectureDiagramData | null;
  streaming?: boolean;
  onConfirm?: (choice: string) => void;
  onComponentClick?: (id: string, name: string) => void;
  compact?: boolean;
}

// Light-theme tier palette (fills strong enough to read on warm paper).
const TIER_COLORS: Record<number, { fill: string; stroke: string }> = {
  1: { fill: 'rgba(46,107,79,0.10)',  stroke: '#2e6b4f' },  // success green
  2: { fill: 'rgba(47,122,115,0.12)', stroke: '#2f7a73' },  // accent teal
  3: { fill: 'rgba(107,63,160,0.10)', stroke: '#6b3fa0' },  // violet
};

export function ArchitectureDiagram({ data, streaming, onConfirm, onComponentClick, compact }: ArchitectureDiagramProps) {
  if (!data || !data.layers) {
    return (
      <div style={{ padding: 20 }}>
        <div className="skeleton" style={{ height: compact ? 200 : 380, borderRadius: 12 }} />
      </div>
    );
  }

  const isFederated =
    (data.pattern_id ?? '').toLowerCase().includes('federated') ||
    (data.pattern ?? '').toLowerCase().includes('federated');

  return (
    <div style={{ padding: compact ? 8 : 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
      {!compact && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>Architecture — {data.pattern}</h2>
          <div style={{ display: 'flex', gap: 8 }}>
            {[1, 2, 3].map((t) => (
              <span key={t} style={{ fontSize: 11, color: TIER_COLORS[t].stroke, border: `1px solid ${TIER_COLORS[t].stroke}`, borderRadius: 4, padding: '2px 6px' }}>T{t}</span>
            ))}
          </div>
        </div>
      )}

      {isFederated
        ? <FederatedTopology data={data} compact={!!compact} />
        : <LayerDiagram data={data} compact={!!compact} />
      }

      {/* Pattern rationale */}
      {!compact && data.pattern_rationale && (
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6, padding: '10px 14px', background: 'var(--bg-elevated)', borderRadius: 8, border: '1px solid var(--border-default)' }}>
          {data.pattern_rationale}
        </div>
      )}

      {/* Component detail table */}
      {!compact && <ComponentTable data={data} onComponentClick={onComponentClick} />}

      {onConfirm && !compact && (
        <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
          <Button variant="primary" onClick={() => onConfirm('Confirm')} style={{ flex: 1 }}>
            Looks Good →
          </Button>
          <Button variant="ghost" onClick={() => onConfirm('Adjust')}>
            Adjust
          </Button>
        </div>
      )}
    </div>
  );
}

// ── Federated Topology Diagram ─────────────────────────────────────────────────
// Shows: [LOB 1 stack] [LOB 2 stack] [LOB 3 stack]  ←→  [Shared Governance Spine]

function FederatedTopology({ data, compact }: { data: ArchitectureDiagramData; compact: boolean }) {
  // Partition components into per-LOB vs shared spine
  const allComponents = data.layers.flatMap((l) =>
    l.components.map((c) => ({ ...c, layer: l.name }))
  );

  const perLob    = allComponents.filter((c) => c.scope === 'per_lob');
  const spineComps = allComponents.filter((c) => c.scope !== 'per_lob');

  const NUM_LOBS = 3;
  const W = compact ? 400 : 700;
  const H = compact ? 220 : 340;

  // Layout constants
  const spineW  = compact ? 130 : 180;
  const spineX  = W - spineW - 4;
  const lobAreaW = spineX - 8;
  const lobW    = Math.floor(lobAreaW / NUM_LOBS) - 4;
  const boxH    = compact ? 20 : 26;
  const lobTop  = compact ? 32 : 44;
  const compGap = compact ? 4 : 6;

  // How tall each LOB column needs to be
  const lobItems = perLob.length > 0 ? perLob : [];
  const lobColH  = lobTop + lobItems.length * (boxH + compGap) + boxH;

  // spine items
  const spineItems = spineComps;

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${W} ${H}`}
      style={{ border: '1px solid var(--border-default)', borderRadius: 8, background: 'var(--bg-elevated)', display: 'block' }}
    >
      {/* LOB columns */}
      {Array.from({ length: NUM_LOBS }, (_, li) => {
        const x = li * (lobW + 4) + 2;
        const lobLabel = `BU ${li + 1}`;

        return (
          <g key={li}>
            {/* Column background */}
            <rect
              x={x} y={2} width={lobW} height={H - 4}
              rx={6} fill="rgba(47,122,115,0.05)" stroke="#2f7a7344" strokeWidth={1}
            />
            {/* BU label */}
            <text x={x + lobW / 2} y={compact ? 14 : 18}
              textAnchor="middle" dominantBaseline="middle"
              fontSize={compact ? 8 : 10} fill="#2f7a73" fontFamily="inherit" fontWeight="700">
              {lobLabel}
            </text>
            <text x={x + lobW / 2} y={compact ? 24 : 30}
              textAnchor="middle" dominantBaseline="middle"
              fontSize={compact ? 6 : 7} fill="var(--text-muted)" fontFamily="inherit">
              Agent Stack
            </text>

            {/* Per-LOB components */}
            {lobItems.map((comp, ci) => {
              const cy = lobTop + ci * (boxH + compGap);
              const tc = TIER_COLORS[comp.final_tier] ?? TIER_COLORS[1];
              const label = comp.name.length > (compact ? 9 : 13)
                ? comp.name.slice(0, compact ? 9 : 13) + '…'
                : comp.name;
              return (
                <g key={comp.name}>
                  <rect x={x + 4} y={cy} width={lobW - 8} height={boxH}
                    rx={3} fill={tc.fill} stroke={tc.stroke} strokeWidth={1} />
                  <text x={x + lobW / 2} y={cy + boxH / 2}
                    textAnchor="middle" dominantBaseline="middle"
                    fontSize={compact ? 6 : 8} fill="var(--text-primary)" fontFamily="inherit">
                    {label}
                  </text>
                  {/* T badge */}
                  <text x={x + lobW - 6} y={cy + 3}
                    textAnchor="end" dominantBaseline="hanging"
                    fontSize={5} fill={tc.stroke} fontFamily="inherit" fontWeight="bold">
                    T{comp.final_tier}
                  </text>
                </g>
              );
            })}

            {/* Arrow pointing right toward spine */}
            <line
              x1={x + lobW} y1={H / 2}
              x2={spineX - 2} y2={H / 2}
              stroke="#2f7a7355" strokeWidth={1} strokeDasharray="3,2"
            />
            <polygon
              points={`${spineX - 2},${H / 2 - 3} ${spineX + 4},${H / 2} ${spineX - 2},${H / 2 + 3}`}
              fill="#2f7a7355"
            />
          </g>
        );
      })}

      {/* Shared Governance Spine */}
      <rect
        x={spineX} y={2} width={spineW} height={H - 4}
        rx={6} fill="rgba(107,63,160,0.06)" stroke="#6b3fa0" strokeWidth={1.5}
      />
      <text x={spineX + spineW / 2} y={compact ? 14 : 18}
        textAnchor="middle" dominantBaseline="middle"
        fontSize={compact ? 8 : 10} fill="#6b3fa0" fontFamily="inherit" fontWeight="700">
        Shared Spine
      </text>
      <text x={spineX + spineW / 2} y={compact ? 24 : 30}
        textAnchor="middle" dominantBaseline="middle"
        fontSize={compact ? 6 : 7} fill="var(--text-muted)" fontFamily="inherit">
        Governance &amp; Platform
      </text>

      {spineItems.map((comp, ci) => {
        const cy = (compact ? 32 : 44) + ci * ((compact ? 18 : 24) + (compact ? 3 : 4));
        const tc = TIER_COLORS[comp.final_tier] ?? TIER_COLORS[1];
        const label = comp.name.length > (compact ? 12 : 16)
          ? comp.name.slice(0, compact ? 12 : 16) + '…'
          : comp.name;
        return (
          <g key={comp.name}>
            <rect x={spineX + 4} y={cy} width={spineW - 8} height={compact ? 18 : 24}
              rx={3} fill={tc.fill} stroke={tc.stroke} strokeWidth={1} />
            <text x={spineX + spineW / 2} y={cy + (compact ? 9 : 12)}
              textAnchor="middle" dominantBaseline="middle"
              fontSize={compact ? 6 : 8} fill="var(--text-primary)" fontFamily="inherit">
              {label}
            </text>
            <text x={spineX + spineW - 6} y={cy + 3}
              textAnchor="end" dominantBaseline="hanging"
              fontSize={5} fill={tc.stroke} fontFamily="inherit" fontWeight="bold">
              T{comp.final_tier}
            </text>
          </g>
        );
      })}

      {/* Legend labels */}
      <text x={lobAreaW / 2} y={H - 6}
        textAnchor="middle" dominantBaseline="auto"
        fontSize={7} fill="var(--text-muted)" fontFamily="inherit">
        Independent LOB Agent Stacks
      </text>
    </svg>
  );
}

// ── Layer Diagram (centralized / mesh / economy) ──────────────────────────────

function LayerDiagram({ data, compact }: { data: ArchitectureDiagramData; compact: boolean }) {
  const svgW = compact ? 400 : 680;
  const svgH = compact ? 220 : 380;
  const layerH = svgH / (data.layers.length || 1);
  const pad = compact ? 4 : 8;

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${svgW} ${svgH}`}
      style={{ border: '1px solid var(--border-default)', borderRadius: 8, background: 'var(--bg-elevated)', display: 'block' }}
    >
      {data.layers.map((layer, li) => {
        const y = li * layerH;
        const compW = layer.components.length > 0
          ? Math.min((svgW - 80) / layer.components.length - pad, compact ? 80 : 110)
          : 80;

        return (
          <g key={layer.name}>
            <rect x={0} y={y} width={svgW} height={layerH}
              fill={li % 2 === 0 ? 'rgba(31,30,27,0.02)' : 'transparent'} />
            <text x={6} y={y + layerH / 2} dominantBaseline="middle"
              fontSize={compact ? 7 : 9} fill="var(--text-muted)" fontFamily="inherit">
              {layer.name}
            </text>
            {layer.components.map((comp, ci) => {
              const cx = 72 + ci * (compW + pad);
              const cy2 = y + (layerH - (compact ? 28 : 36)) / 2;
              const tc = TIER_COLORS[comp.final_tier] ?? TIER_COLORS[1];
              return (
                <g key={comp.name}>
                  <rect x={cx} y={cy2} width={compW} height={compact ? 28 : 36}
                    rx={4} fill={tc.fill} stroke={tc.stroke} strokeWidth={1.5} />
                  <text x={cx + compW / 2} y={cy2 + (compact ? 14 : 18)}
                    textAnchor="middle" dominantBaseline="middle"
                    fontSize={compact ? 7 : 9} fill="var(--text-primary)" fontFamily="inherit">
                    {comp.name.length > (compact ? 10 : 14) ? comp.name.slice(0, compact ? 10 : 14) + '…' : comp.name}
                  </text>
                  <text x={cx + compW - 3} y={cy2 + 3}
                    textAnchor="end" dominantBaseline="hanging"
                    fontSize={6} fill={tc.stroke} fontFamily="inherit" fontWeight="bold">
                    T{comp.final_tier}
                  </text>
                  {comp.elevation_reason && comp.final_tier > comp.base_tier && (
                    <text x={cx + 4} y={cy2 + 4} fontSize={8} fill={tc.stroke} dominantBaseline="hanging">↑</text>
                  )}
                </g>
              );
            })}
          </g>
        );
      })}
      {data.layers.slice(1).map((_, li) => (
        <line key={li} x1={0} x2={svgW} y1={(li + 1) * layerH} y2={(li + 1) * layerH}
          stroke="var(--border-default)" strokeWidth={0.5} />
      ))}
    </svg>
  );
}

// ── Component detail table ────────────────────────────────────────────────────

function ComponentTable({ data, onComponentClick }: { data: ArchitectureDiagramData; onComponentClick?: (id: string, name: string) => void }) {
  const allComponents = data.layers.flatMap((l) =>
    l.components.map((c) => ({ ...c, layer: l.name }))
  );
  if (allComponents.length === 0) return null;

  const isFederated =
    (data.pattern_id ?? '').toLowerCase().includes('federated') ||
    (data.pattern ?? '').toLowerCase().includes('federated');

  return (
    <div style={{ border: '1px solid var(--border-default)', borderRadius: 8, overflow: 'hidden' }}>
      <div style={{ padding: '8px 14px', background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border-default)', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
        Components ({allComponents.length})
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: 'var(--bg-elevated)' }}>
              {['Component', 'Layer', 'Tier', 'AWS Service', isFederated ? 'Scope' : 'Elevation'].map((h) => (
                <th key={h} style={{ padding: '6px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {allComponents.map((c, i) => {
              const tc = TIER_COLORS[c.final_tier] ?? TIER_COLORS[1];
              const clickable = !!onComponentClick && !!c.id;
              return (
                <tr
                  key={c.name}
                  onClick={clickable ? () => onComponentClick!(c.id!, c.name) : undefined}
                  style={{
                    borderTop: '1px solid var(--border-default)',
                    background: i % 2 === 0 ? 'transparent' : 'rgba(31,30,27,0.02)',
                    cursor: clickable ? 'pointer' : 'default',
                    transition: clickable ? 'background 0.1s' : undefined,
                  }}
                  onMouseEnter={clickable ? (e) => { (e.currentTarget as HTMLTableRowElement).style.background = 'rgba(47,122,115,0.06)'; } : undefined}
                  onMouseLeave={clickable ? (e) => { (e.currentTarget as HTMLTableRowElement).style.background = i % 2 === 0 ? 'transparent' : 'rgba(31,30,27,0.02)'; } : undefined}
                >
                  <td style={{ padding: '7px 12px', color: 'var(--text-primary)', fontWeight: 500 }}>
                    {c.name}
                    {clickable && <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--accent-blue)', opacity: 0.7 }}>→</span>}
                  </td>
                  <td style={{ padding: '7px 12px', color: 'var(--text-muted)' }}>{c.layer}</td>
                  <td style={{ padding: '7px 12px' }}>
                    <span style={{ color: tc.stroke, fontWeight: 600, fontSize: 11, border: `1px solid ${tc.stroke}`, borderRadius: 4, padding: '1px 5px' }}>T{c.final_tier}</span>
                    {c.final_tier > c.base_tier && (
                      <span style={{ color: tc.stroke, fontSize: 10, marginLeft: 4 }}>↑ from T{c.base_tier}</span>
                    )}
                  </td>
                  <td style={{ padding: '7px 12px', color: 'var(--text-secondary)' }}>{c.aws_service || '—'}</td>
                  <td style={{ padding: '7px 12px', color: 'var(--text-muted)' }}>
                    {isFederated
                      ? (c.scope === 'per_lob'
                          ? <span style={{ color: '#2f7a73', fontSize: 11 }}>Per BU/LOB</span>
                          : <span style={{ color: '#6b3fa0', fontSize: 11 }}>Shared Spine</span>)
                      : (c.elevation_reason || '—')
                    }
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ArchitectureDiagram;
