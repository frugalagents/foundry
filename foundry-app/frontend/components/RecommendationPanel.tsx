'use client'

import { useMemo } from 'react'
import { useStore } from '@/store'
import { normalizeWorkspace } from '@/lib/message-analysis'

export default function RecommendationPanel() {
  const workspace = useStore((s) => s.workspace)
  const view = useMemo(() => normalizeWorkspace(workspace), [workspace])
  const hasWorkspace =
    !!view.recommendation ||
    view.facts.length > 0

  return (
    <div style={{
      padding: '14px 16px',
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color: 'var(--text-muted)',
        }}>
          Recommendation
        </span>
        {view.stage && (
          <span style={{
            padding: '3px 8px',
            borderRadius: 999,
            border: '1px solid var(--border)',
            background: 'var(--bg-elevated)',
            fontSize: 10.5,
            color: 'var(--text-faint)',
            textTransform: 'capitalize',
          }}>
            {view.stage}
          </span>
        )}
      </div>

      {!hasWorkspace ? (
        <p style={{ fontSize: 12.5, color: 'var(--text-faint)', lineHeight: 1.6 }}>
          The advisor has not committed a recommendation yet. As decisions solidify, the working brief will appear here.
        </p>
      ) : (
        <>
          {view.recommendation && (
            <div style={sectionStyle}>
              <div style={sectionLabel}>Current Direction</div>
              <p style={bodyStyle}>{view.recommendation}</p>
            </div>
          )}

          {view.facts.length > 0 && (
            <div style={sectionStyle}>
              <div style={sectionLabel}>Observed Facts</div>
              <ul style={listStyle}>
                {view.facts.slice(0, 4).map((fact) => <li key={fact}>{fact}</li>)}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  )
}

const sectionStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
}

const sectionLabel: React.CSSProperties = {
  fontSize: 10.5,
  fontWeight: 700,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
  color: 'var(--text-faint)',
}

const bodyStyle: React.CSSProperties = {
  fontSize: 12.5,
  color: 'var(--text)',
  lineHeight: 1.6,
}

const listStyle: React.CSSProperties = {
  margin: 0,
  paddingLeft: 18,
  fontSize: 12.5,
  color: 'var(--text)',
  lineHeight: 1.55,
}
