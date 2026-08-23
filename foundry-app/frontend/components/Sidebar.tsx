'use client'

import { useCallback, useMemo, useState } from 'react'
import { useStore } from '@/store'
import { clearToken, navigateToLogin } from '@/lib/auth'
import { listAllSessions, deleteSession } from '@/lib/api'
import { loadSessionIntoView } from '@/lib/session-actions'
import type { ConversationRow } from '@/lib/types'

const MODULE_COLORS: Record<string, string> = {
  'coding-agent':       '#6366f1',
  'product-platform':   '#22c55e',
  'fabric':             '#f59e0b',
}

const MODULE_LABELS: Record<string, string> = {
  'coding-agent':       'Coding Agent',
  'product-platform':   'Product',
  'fabric':             'Fabric',
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60_000)
  if (m < 1)  return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return `${d}d ago`
}

function groupByCustomer(conversations: ConversationRow[]) {
  const groups = new Map<string, { name: string; sessions: ConversationRow[] }>()
  for (const row of conversations) {
    const key = row.customer.customer_id
    if (!groups.has(key)) {
      groups.set(key, { name: row.customer.name, sessions: [] })
    }
    groups.get(key)!.sessions.push(row)
  }
  return Array.from(groups.entries()).map(([customerId, group]) => ({
    customerId,
    name: group.name,
    sessions: group.sessions,
  }))
}

function formatCustomerGroupName(name: string) {
  const normalized = name.trim()
  if (!normalized) return 'Workspace'
  if (/^simulation-\d+$/i.test(normalized) || /^demo(?:\b|[-\s_])/i.test(normalized)) {
    return 'Workspace'
  }
  return normalized
}

export default function Sidebar({ onNewChat }: { onNewChat: () => void }) {
  const {
    conversations, setConversations,
    activeSessionId,
    clearMessages, clearWorkspace, hideCanvas, streaming,
    userId, userName, isAdmin,
    showAdminView, setShowAdminView,
  } = useStore()
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  const grouped = useMemo(() => {
    const filtered = search.trim()
      ? conversations.filter((r) =>
          r.session.title.toLowerCase().includes(search.toLowerCase()) ||
          r.customer.name.toLowerCase().includes(search.toLowerCase()),
        )
      : conversations
    return groupByCustomer(filtered)
  }, [conversations, search])
  const sections = useMemo(() => {
    if (isAdmin && grouped.length > 1) {
      return grouped.map((group) => ({
        key: group.customerId,
        label: formatCustomerGroupName(group.name),
        sessions: group.sessions,
        showLabel: true,
      }))
    }

    return [{
      key: 'all-sessions',
      label: 'Sessions',
      sessions: grouped.flatMap((group) => group.sessions),
      showLabel: false,
    }]
  }, [grouped, isAdmin])

  const handleSelect = useCallback(
    async (row: ConversationRow) => {
      setLoadError(null)
      history.pushState(null, '', `/sessions/${row.session.session_id}`)
      setLoadingId(row.session.session_id)
      try {
        await loadSessionIntoView(row.customer.customer_id, row.session.session_id, row.session.module_id)
      } catch (err) {
        console.error('[Sidebar] Failed to load session history:', err)
        setLoadError('Could not load history')
      } finally {
        setLoadingId(null)
      }
    },
    [],
  )

  const handleNewChat = useCallback(() => {
    onNewChat()
  }, [onNewChat])

  const handleRefresh = useCallback(async () => {
    if (streaming || refreshing) return

    setLoadError(null)
    setRefreshing(true)
    try {
      const beforeRefresh = useStore.getState()
      const convs = await listAllSessions()
      const activeRow = beforeRefresh.activeSessionId
        ? beforeRefresh.conversations.find(
            (row) => row.session.session_id === beforeRefresh.activeSessionId,
          )
        : undefined
      const activeStillListed = activeRow
        ? convs.some((row) => row.session.session_id === activeRow.session.session_id)
        : true
      const refreshedConversations = activeRow && !activeStillListed
        ? [activeRow, ...convs]
        : convs

      setConversations(refreshedConversations)

      if (beforeRefresh.activeCustomerId && beforeRefresh.activeSessionId) {
        await loadSessionIntoView(
          beforeRefresh.activeCustomerId,
          beforeRefresh.activeSessionId,
          beforeRefresh.activeModule ?? undefined,
        )
      }
    } catch (err) {
      console.error('[Sidebar] Failed to refresh sessions:', err)
      setLoadError('Could not refresh saved sessions')
    } finally {
      setRefreshing(false)
    }
  }, [refreshing, setConversations, streaming])

  const handleDelete = useCallback(
    async (e: React.MouseEvent, row: ConversationRow) => {
      e.stopPropagation()
      if (!confirm(`Delete "${row.session.title}"?`)) return
      setDeletingId(row.session.session_id)
      try {
        await deleteSession(row.customer.customer_id, row.session.session_id)
        const updated = conversations.filter(c => c.session.session_id !== row.session.session_id)
        setConversations(updated)
        if (activeSessionId === row.session.session_id) {
          clearMessages()
          clearWorkspace()
          hideCanvas()
          useStore.getState().clearActiveSession()
          history.pushState(null, '', '/')
        }
      } catch { /* ignore */ } finally {
        setDeletingId(null)
      }
    },
    [conversations, setConversations, activeSessionId, clearMessages, clearWorkspace, hideCanvas],
  )

  function handleSignOut() {
    clearToken()
    navigateToLogin()
  }

  return (
    <aside style={{
      width: 240,
      minWidth: 240,
      height: '100%',
      background: 'var(--bg-elevated)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 14px 10px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-faint)' }}>
          Sessions
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {isAdmin && (
            <button
              onClick={() => setShowAdminView(!showAdminView)}
              title="Admin console"
              style={{ ...iconBtn, color: showAdminView ? 'var(--amber)' : 'var(--text-muted)' }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </button>
          )}
          <button
            type="button"
            onClick={handleRefresh}
            disabled={streaming || refreshing}
            title={streaming ? 'Wait for the response to finish' : 'Refresh saved sessions'}
            aria-label="Refresh saved sessions"
            style={{
              ...iconBtn,
              cursor: streaming || refreshing ? 'not-allowed' : 'pointer',
              opacity: streaming || refreshing ? 0.55 : 1,
            }}
          >
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={refreshing ? { animation: 'spin 0.7s linear infinite' } : undefined}
            >
              <polyline points="1 4 1 10 7 10" /><polyline points="23 20 23 14 17 14" />
              <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4-4.64 4.36A9 9 0 0 1 3.51 15" />
            </svg>
          </button>
        </div>
      </div>

      {/* Search */}
      <div style={{ padding: '10px 10px 6px' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'var(--bg)', border: '1px solid var(--border)',
          borderRadius: 8, padding: '7px 10px',
        }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--text-faint)" strokeWidth="2">
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search sessions…"
            style={{
              background: 'none', border: 'none', outline: 'none',
              color: 'var(--text)', fontSize: 12.5, width: '100%',
            }}
          />
        </div>
      </div>

      {/* New chat button */}
      <div style={{ padding: '0 10px 6px' }}>
        <button
          onClick={handleNewChat}
          style={{
            width: '100%',
            padding: '8px 12px',
            background: 'var(--accent-dim)',
            border: '1px dashed var(--accent)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--accent)',
            fontSize: 13,
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            transition: 'background var(--transition)',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--accent-glow)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--accent-dim)')}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New chat
        </button>
      </div>

      {/* Conversation list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
        {loadError && (
          <p style={{ padding: '6px 14px', fontSize: 11, color: 'var(--red)', textAlign: 'center' }}>
            {loadError}
          </p>
        )}
        {grouped.length === 0 ? (
          <p style={{ padding: '16px 14px', fontSize: 12, color: 'var(--text-faint)', textAlign: 'center' }}>
            {search ? 'No matches' : 'No conversations yet'}
          </p>
        ) : (
          sections.map((section) => (
            <div key={section.key}>
              {section.showLabel && (
                <div style={{
                  padding: '12px 14px 4px', fontSize: 10.5, fontWeight: 600,
                  letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-faint)',
                }}>
                  {section.label}
                </div>
              )}
              {section.sessions.map((row) => {
                const isActive = row.session.session_id === activeSessionId
                const isOwned = Boolean(
                  userId
                  && row.session.created_by === userId
                  && row.customer.created_by === userId,
                )
                const mod      = row.session.module_id
                const modColor = mod ? (MODULE_COLORS[mod] ?? '#888') : '#888'
                return (
                  <div
                    key={row.session.session_id}
                    onMouseEnter={() => setHoveredId(row.session.session_id)}
                    onMouseLeave={() => setHoveredId(null)}
                    style={{ position: 'relative' }}
                  >
                    <button
                      onClick={() => handleSelect(row)}
                      style={{
                        width: '100%', padding: '8px 14px',
                        background: isActive ? 'var(--bg-hover)' : 'transparent',
                        border: 'none',
                        borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
                        cursor: 'pointer', textAlign: 'left',
                        display: 'flex', flexDirection: 'column', gap: 2,
                        transition: 'background var(--transition)',
                      }}
                      onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'var(--bg-hover)' }}
                      onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent' }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
                        <span style={{
                          fontSize: 13, fontWeight: 500, color: 'var(--text)',
                          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 130,
                        }}>
                          {row.session.title}
                        </span>
                        {mod && (
                          <span style={{
                            fontSize: 10, fontWeight: 600, color: modColor,
                            background: `${modColor}18`, padding: '1px 5px', borderRadius: 4,
                            whiteSpace: 'nowrap',
                          }}>
                            {MODULE_LABELS[mod] ?? mod}
                          </span>
                        )}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        {loadingId === row.session.session_id ? (
                          <span style={{
                            width: 10, height: 10, borderRadius: '50%', flexShrink: 0,
                            border: '1.5px solid var(--accent)', borderTopColor: 'transparent',
                            display: 'inline-block', animation: 'spin 0.7s linear infinite',
                          }} />
                        ) : (
                          <span style={{ fontSize: 10, color: 'var(--text-faint)', whiteSpace: 'nowrap', flexShrink: 0 }}>
                            {relativeTime(row.session.updated_at)}
                          </span>
                        )}
                      </div>
                    </button>
                    {isOwned && hoveredId === row.session.session_id && (
                      <button
                        onClick={(e) => handleDelete(e, row)}
                        disabled={deletingId === row.session.session_id}
                        title="Delete session"
                        style={{
                          position: 'absolute', right: 6, top: '50%', transform: 'translateY(-50%)',
                          background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                          borderRadius: 4, cursor: 'pointer', padding: '2px 4px',
                          color: 'var(--text-muted)', fontSize: 11, lineHeight: 1,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}
                      >
                        {deletingId === row.session.session_id ? '…' : '×'}
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          ))
        )}
      </div>

      {/* Footer: user info + sign out */}
      <div style={{
        padding: '10px 14px',
        borderTop: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 8,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <div style={{
            width: 26, height: 26, borderRadius: '50%',
            background: 'var(--bg-hover)',
            border: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 11, fontWeight: 600, color: 'var(--text-muted)',
            flexShrink: 0,
          }}>
            {(userName ?? 'U').charAt(0).toUpperCase()}
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {userName ?? 'User'}
            </div>
            {isAdmin && (
              <div style={{ fontSize: 10, color: 'var(--amber)', fontWeight: 600 }}>Admin</div>
            )}
          </div>
        </div>
        <button onClick={handleSignOut} title="Sign out" style={iconBtn}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </button>
      </div>
    </aside>
  )
}

const iconBtn: React.CSSProperties = {
  background: 'none',
  border: 'none',
  color: 'var(--text-muted)',
  cursor: 'pointer',
  padding: '4px',
  borderRadius: 'var(--radius-sm)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
  transition: 'color var(--transition)',
}
