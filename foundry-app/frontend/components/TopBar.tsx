'use client'

import { useState } from 'react'
import { useStore } from '@/store'

const MODULES = [
  { id: 'coding-agent', label: 'Coding Agent' },
  { id: 'product-platform', label: 'Product' },
  { id: 'fabric', label: 'Fabric' },
]

const EXPORT_OPTIONS = [
  { icon: '▤', label: 'Export as PDF', hint: 'One-page architecture summary' },
  { icon: '▧', label: 'Export as Doc', hint: 'Editable design document' },
  { icon: '{ }', label: 'Export as Terraform', hint: 'Infra-as-code scaffold' },
  { icon: '⇗', label: 'Copy share link', hint: 'View-only, expires in 30 days' },
]

export default function TopBar() {
  const { activeModule, setActiveModule, userName } = useStore()
  const [exportOpen, setExportOpen] = useState(false)
  const currentModule = activeModule ?? 'coding-agent'

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

      {/* Right: export + user avatar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setExportOpen((v) => !v)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '7px 12px',
              background: 'var(--bg-elevated)', border: '1px solid var(--border)',
              borderRadius: 8, color: 'var(--text)', fontSize: 12.5, fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Share &amp; Export
          </button>

          {exportOpen && (
            <div style={{
              position: 'absolute', top: 'calc(100% + 6px)', right: 0, width: 220,
              background: 'var(--bg-elevated)', border: '1px solid var(--border)',
              borderRadius: 10, boxShadow: '0 12px 32px rgba(0,0,0,0.55)', padding: 6, zIndex: 60,
            }}>
              {EXPORT_OPTIONS.map((opt) => (
                <button
                  key={opt.label}
                  onClick={() => setExportOpen(false)}
                  style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                    padding: '9px 10px', background: 'none', border: 'none', borderRadius: 7,
                    color: 'var(--text)', fontSize: 12.5, textAlign: 'left', cursor: 'pointer',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
                >
                  <span style={{
                    width: 22, height: 22, borderRadius: 6, background: 'var(--bg-hover)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 11, color: 'var(--text-muted)', flexShrink: 0,
                  }}>{opt.icon}</span>
                  <span style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <span>{opt.label}</span>
                    <span style={{ fontSize: 10.5, color: 'var(--text-faint)' }}>{opt.hint}</span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div style={{ width: 1, height: 20, background: 'var(--border)' }} />

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
