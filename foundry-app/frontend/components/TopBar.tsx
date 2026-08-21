'use client'

import { useStore } from '@/store'

export default function TopBar() {
  const userName = useStore((s) => s.userName)

  return (
    <div style={{
      height: 56, flexShrink: 0, display: 'flex', alignItems: 'center',
      justifyContent: 'space-between', padding: '0 16px',
      borderBottom: '1px solid var(--border)', background: 'var(--bg)', gap: 16,
    }}>
      {/* Left: logo + module switcher */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, flexShrink: 0 }}>
          <div style={{
            width: 26, height: 26, borderRadius: 7, background: 'var(--accent)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.4">
              <path d="M13 2 4 14h6l-1 8 9-12h-6z" />
            </svg>
          </div>
          <span style={{ fontSize: 14, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--text)' }}>
            Enterprise AI Foundry
          </span>
        </div>

      </div>

      {/* Right: user avatar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        <div style={{
          width: 28, height: 28, borderRadius: '50%', background: 'var(--bg-hover)',
          border: '1px solid var(--border)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)',
          flexShrink: 0,
        }}>
          {(userName ?? 'U').slice(0, 2).toUpperCase()}
        </div>
      </div>
    </div>
  )
}
