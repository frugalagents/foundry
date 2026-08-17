'use client'

import type { NodeComment } from '@/lib/types'

export interface DrawerNode {
  id: string
  label: string
  sublabel: string
  icon: string
  color: string
  cost: string
  size: string
  comments: NodeComment[]
}

export default function NodeDetailDrawer({
  node, onClose,
}: {
  node: DrawerNode
  onClose: () => void
}) {
  return (
    <div style={{
      position: 'absolute', top: 0, right: 0, bottom: 0, width: 340,
      background: 'var(--bg-elevated)', borderLeft: '1px solid var(--border)',
      boxShadow: '-16px 0 40px rgba(0,0,0,0.5)', display: 'flex', flexDirection: 'column',
      zIndex: 50, animation: 'drawerIn 180ms ease both',
    }}>
      {/* Header */}
      <div style={{
        padding: 16, borderBottom: '1px solid var(--border)', display: 'flex',
        alignItems: 'flex-start', justifyContent: 'space-between', gap: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          <span style={{
            width: 32, height: 32, borderRadius: 8, background: `${node.color}22`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 14, color: node.color, flexShrink: 0,
          }}>{node.icon}</span>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>{node.label}</div>
            <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{node.sublabel}</div>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            width: 24, height: 24, borderRadius: 6, background: 'none', border: 'none',
            color: 'var(--text-muted)', cursor: 'pointer', flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* Cost / sizing */}
      <div style={{ padding: 16, borderBottom: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
          <span style={{ color: 'var(--text-muted)' }}>Monthly cost</span>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--text)', fontWeight: 500 }}>
            {node.cost}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
          <span style={{ color: 'var(--text-muted)' }}>Sizing</span>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--text)', fontWeight: 500 }}>
            {node.size}
          </span>
        </div>
      </div>

      {/* Comments */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <span style={{
          fontSize: 11, fontWeight: 600, letterSpacing: '0.05em',
          textTransform: 'uppercase', color: 'var(--text-faint)',
        }}>
          Comments
        </span>
        {node.comments.length === 0 && (
          <p style={{ fontSize: 12, color: 'var(--text-faint)' }}>No comments yet on this component.</p>
        )}
        {node.comments.map((c, i) => (
          <div key={i} style={{
            background: 'var(--bg-elevated-2)', border: '1px solid var(--border)',
            borderRadius: 9, padding: '10px 12px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 5 }}>
              <span style={{
                width: 18, height: 18, borderRadius: '50%', background: 'var(--bg-hover)',
                border: '1px solid var(--border-focus)', fontSize: 9, fontWeight: 600,
                color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>{c.initials}</span>
              <span style={{ fontSize: 11.5, fontWeight: 500, color: 'var(--text)' }}>{c.author}</span>
            </div>
            <p style={{ fontSize: 12.5, lineHeight: 1.55, color: 'var(--text-2)' }}>{c.text}</p>
          </div>
        ))}
      </div>

      {/* Add comment footer */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border)' }}>
        <div style={{
          background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 9,
          padding: '8px 10px', fontSize: 12, color: 'var(--text-faint)',
        }}>
          Add a comment…
        </div>
      </div>
    </div>
  )
}
