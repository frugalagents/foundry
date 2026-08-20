'use client'

import { useMemo } from 'react'
import { useStore } from '@/store'
import { normalizeWorkspace } from '@/lib/message-analysis'

export default function DecisionLogPanel() {
  const workspace = useStore((s) => s.workspace)
  const view = useMemo(() => normalizeWorkspace(workspace), [workspace])

  return (
    <div style={panelStyle}>
      <div style={headerStyle}>
        <span style={titleStyle}>Decision Log</span>
        <span style={countStyle}>{view.decisions.length}</span>
      </div>

      {view.decisions.length === 0 ? (
        <p style={emptyStyle}>
          Architecture decisions will appear here once the advisor starts locking in choices.
        </p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {view.decisions.map((decision, index) => (
            <div key={decision} style={itemStyle}>
              <span style={indexBadgeStyle}>{index + 1}</span>
              <p style={bodyStyle}>{decision}</p>
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

const countStyle: React.CSSProperties = {
  minWidth: 22,
  height: 22,
  padding: '0 7px',
  borderRadius: 999,
  background: 'var(--bg-hover)',
  border: '1px solid var(--border)',
  color: 'var(--text-faint)',
  fontSize: 11,
  fontWeight: 700,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
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
  border: '1px solid var(--border)',
  background: 'var(--bg-elevated)',
}

const indexBadgeStyle: React.CSSProperties = {
  width: 18,
  height: 18,
  borderRadius: 6,
  background: 'var(--accent-dim)',
  color: 'var(--accent)',
  fontSize: 10,
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
