'use client'

import { useMemo } from 'react'
import { useStore } from '@/store'
import { normalizeWorkspace } from '@/lib/message-analysis'

export default function RiskRegisterPanel() {
  const workspace = useStore((s) => s.workspace)
  const view = useMemo(() => normalizeWorkspace(workspace), [workspace])

  return (
    <div style={panelStyle}>
      <div style={headerStyle}>
        <span style={titleStyle}>Risk Register</span>
        <span style={countStyle(view.risks.length > 0)}>{view.risks.length}</span>
      </div>

      {view.risks.length === 0 ? (
        <p style={emptyStyle}>
          No active risks have been recorded yet. Delivery and compliance blockers will be tracked here.
        </p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {view.risks.map((risk) => (
            <div key={risk} style={itemStyle}>
              <span style={riskBadgeStyle}>!</span>
              <p style={bodyStyle}>{risk}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const panelStyle: React.CSSProperties = {
  padding: '14px 16px',
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}

const headerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 8,
}

const titleStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
}

function countStyle(hasRisks: boolean): React.CSSProperties {
  return {
    minWidth: 22,
    height: 22,
    padding: '0 7px',
    borderRadius: 999,
    background: hasRisks ? 'rgba(245,158,11,0.14)' : 'var(--bg-hover)',
    border: `1px solid ${hasRisks ? 'rgba(245,158,11,0.3)' : 'var(--border)'}`,
    color: hasRisks ? 'var(--amber)' : 'var(--text-faint)',
    fontSize: 11,
    fontWeight: 700,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  }
}

const emptyStyle: React.CSSProperties = {
  fontSize: 12.5,
  color: 'var(--text-faint)',
  lineHeight: 1.6,
}

const itemStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 10,
  padding: '10px 12px',
  borderRadius: 10,
  border: '1px solid rgba(245,158,11,0.22)',
  background: 'rgba(245,158,11,0.05)',
}

const riskBadgeStyle: React.CSSProperties = {
  width: 18,
  height: 18,
  borderRadius: 6,
  background: 'rgba(245,158,11,0.14)',
  color: 'var(--amber)',
  fontSize: 11,
  fontWeight: 700,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
}

const bodyStyle: React.CSSProperties = {
  fontSize: 12.5,
  color: 'var(--text)',
  lineHeight: 1.55,
}
