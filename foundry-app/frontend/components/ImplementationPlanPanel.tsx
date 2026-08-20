'use client'

import { useMemo } from 'react'
import { useStore } from '@/store'
import { normalizeWorkspace } from '@/lib/message-analysis'

export default function ImplementationPlanPanel() {
  const workspace = useStore((s) => s.workspace)
  const view = useMemo(() => normalizeWorkspace(workspace), [workspace])

  return (
    <div style={panelStyle}>
      <div style={headerStyle}>
        <span style={titleStyle}>Implementation Plan</span>
        <span style={countStyle}>{view.implementation_plan.length}</span>
      </div>

      {view.implementation_plan.length === 0 ? (
        <p style={emptyStyle}>
          The rollout plan will appear here once the advisor starts translating the recommendation into execution steps.
        </p>
      ) : (
        <ol style={listStyle}>
          {view.implementation_plan.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
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

const listStyle: React.CSSProperties = {
  margin: 0,
  paddingLeft: 18,
  fontSize: 12.5,
  color: 'var(--text)',
  lineHeight: 1.6,
}
