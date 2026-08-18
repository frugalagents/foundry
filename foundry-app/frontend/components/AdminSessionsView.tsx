'use client'

import { useMemo, useState } from 'react'
import { useStore } from '@/store'
import { loadSessionIntoView } from '@/lib/session-actions'
import type { ConversationRow } from '@/lib/types'

type SortKey = 'customer' | 'created_by' | 'updated_at'

export default function AdminSessionsView() {
  const { conversations, setShowAdminView } = useStore()
  const [sortKey, setSortKey] = useState<SortKey>('updated_at')
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  const sorted = useMemo(() => {
    const rows = [...conversations]
    rows.sort((a, b) => {
      if (sortKey === 'customer') return a.customer.name.localeCompare(b.customer.name)
      if (sortKey === 'created_by') return a.session.created_by.localeCompare(b.session.created_by)
      return +new Date(b.session.updated_at) - +new Date(a.session.updated_at)
    })
    return rows
  }, [conversations, sortKey])

  const handleOpen = async (row: ConversationRow) => {
    setLoadError(null)
    setLoadingId(row.session.session_id)
    try {
      await loadSessionIntoView(row.customer.customer_id, row.session.session_id, row.session.module_id)
      history.pushState(null, '', `/sessions/${row.session.session_id}`)
      setShowAdminView(false)
    } catch (err) {
      console.error('[AdminSessionsView] Failed to load session history:', err)
      setLoadError('Could not load history')
    } finally {
      setLoadingId(null)
    }
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg)' }}>
      <div style={{
        padding: '14px 20px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>All Sessions</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {conversations.length} session{conversations.length === 1 ? '' : 's'} across every customer
          </div>
        </div>
        <button
          onClick={() => setShowAdminView(false)}
          style={{
            padding: '6px 12px', background: 'var(--bg-elevated)', border: '1px solid var(--border)',
            borderRadius: 8, color: 'var(--text)', fontSize: 12.5, cursor: 'pointer',
          }}
        >
          Close
        </button>
      </div>

      {loadError && (
        <p style={{ padding: '8px 20px', fontSize: 12, color: 'var(--red)' }}>{loadError}</p>
      )}

      <div style={{ flex: 1, overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
              <th style={thStyle} onClick={() => setSortKey('customer')}>Customer</th>
              <th style={thStyle}>Session</th>
              <th style={thStyle} onClick={() => setSortKey('created_by')}>Created by</th>
              <th style={thStyle}>Status</th>
              <th style={thStyle} onClick={() => setSortKey('updated_at')}>Updated</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <tr
                key={row.session.session_id}
                onClick={() => handleOpen(row)}
                style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={tdStyle}>{row.customer.name}</td>
                <td style={tdStyle}>{row.session.title}</td>
                <td style={{ ...tdStyle, color: 'var(--text-muted)', fontFamily: 'monospace', fontSize: 11.5 }}>
                  {row.session.created_by}
                </td>
                <td style={tdStyle}>{row.session.status}</td>
                <td style={tdStyle}>
                  {loadingId === row.session.session_id ? '…' : new Date(row.session.updated_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {sorted.length === 0 && (
          <p style={{ padding: 20, fontSize: 12, color: 'var(--text-faint)', textAlign: 'center' }}>
            No sessions found.
          </p>
        )}
      </div>
    </div>
  )
}

const thStyle: React.CSSProperties = {
  padding: '8px 16px',
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
  color: 'var(--text-faint)',
  cursor: 'pointer',
}

const tdStyle: React.CSSProperties = {
  padding: '10px 16px',
  color: 'var(--text)',
}
