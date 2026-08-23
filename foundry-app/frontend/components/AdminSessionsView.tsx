'use client'

import { useEffect, useMemo, useState } from 'react'
import { useStore } from '@/store'
import { ApiError, getAdminAnalytics, listAdminFeedback, listAdminSessions } from '@/lib/api'
import { loadSessionIntoView } from '@/lib/session-actions'
import type { AdminAnalytics, AdminFeedbackRow, ConversationRow } from '@/lib/types'

type SortKey = 'customer' | 'created_by' | 'updated_at'
type AdminTab = 'overview' | 'sessions' | 'feedback'

export default function AdminSessionsView() {
  const { setShowAdminView } = useStore()
  const [sortKey, setSortKey] = useState<SortKey>('updated_at')
  const [activeTab, setActiveTab] = useState<AdminTab>('overview')
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [sessionRows, setSessionRows] = useState<ConversationRow[]>([])
  const [feedbackRows, setFeedbackRows] = useState<AdminFeedbackRow[]>([])
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    void refreshAll()
  }, [])

  async function refreshAll() {
    setLoadError(null)
    setRefreshing(true)
    try {
      const [nextAnalytics, nextSessions, nextFeedback] = await Promise.all([
        getAdminAnalytics(),
        listAdminSessions(),
        listAdminFeedback(),
      ])
      setAnalytics(nextAnalytics)
      setSessionRows(nextSessions)
      setFeedbackRows(nextFeedback)
    } catch (err) {
      console.error('[AdminSessionsView] Failed to load admin console data:', err)
      if (err instanceof ApiError && err.status === 403) {
        setLoadError('This browser session is not authorized to load the admin console.')
      } else {
        setLoadError('Could not load admin console data')
      }
    } finally {
      setRefreshing(false)
    }
  }

  const sortedSessions = useMemo(() => {
    const nextRows = [...sessionRows]
    nextRows.sort((a, b) => {
      if (sortKey === 'customer') return a.customer.name.localeCompare(b.customer.name)
      if (sortKey === 'created_by') return a.session.created_by.localeCompare(b.session.created_by)
      return +new Date(b.session.updated_at) - +new Date(a.session.updated_at)
    })
    return nextRows
  }, [sessionRows, sortKey])

  const recentFeedback = useMemo(
    () => [...feedbackRows].sort((a, b) => +new Date(b.feedback.updated_at) - +new Date(a.feedback.updated_at)),
    [feedbackRows],
  )

  async function handleOpen(row: { customer: { customer_id: string }; session: { session_id: string; module_id?: string } }) {
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
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden', background: 'var(--bg)' }}>
      <div style={{
        padding: '16px 20px 14px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 16,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)' }}>Admin Console</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>
            Cross-user visibility into usage, session inventory, and captured feedback.
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button onClick={() => void refreshAll()} disabled={refreshing} style={headerButtonStyle(refreshing)}>
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
          <button onClick={() => setShowAdminView(false)} style={headerButtonStyle(false)}>
            Close
          </button>
        </div>
      </div>

      <div style={{ padding: '12px 20px 0', flexShrink: 0 }}>
        <div style={tabBarStyle}>
          <AdminTabButton active={activeTab === 'overview'} onClick={() => setActiveTab('overview')}>Overview</AdminTabButton>
          <AdminTabButton active={activeTab === 'sessions'} onClick={() => setActiveTab('sessions')}>
            Sessions
          </AdminTabButton>
          <AdminTabButton active={activeTab === 'feedback'} onClick={() => setActiveTab('feedback')}>
            Feedback
          </AdminTabButton>
        </div>
      </div>

      {loadError ? (
        <p style={{ padding: '10px 20px 0', fontSize: 12, color: 'var(--red)' }}>{loadError}</p>
      ) : null}

      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', padding: '16px 20px 20px' }}>
        {activeTab === 'overview' ? (
          <div style={{ height: '100%', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={cardGridStyle}>
              <MetricCard label="Unique users" value={analytics?.unique_users ?? 0} />
              <MetricCard label="Sessions" value={analytics?.total_sessions ?? 0} />
              <MetricCard label="Customers" value={analytics?.total_customers ?? 0} />
              <MetricCard label="Active 7d" value={analytics?.active_sessions_7d ?? 0} />
              <MetricCard label="Workspace outputs" value={analytics?.sessions_with_workspace ?? 0} sublabel="sessions with workspace output" />
              <MetricCard label="Architecture snapshots" value={analytics?.sessions_with_architecture ?? 0} />
              <MetricCard label="Feedback" value={analytics?.feedback_submissions ?? 0} sublabel={analytics ? `avg ${analytics.average_feedback_score.toFixed(1)}/5` : undefined} />
            </div>

            <div style={splitGridStyle}>
              <SummaryListCard title="Module Mix" items={analytics?.module_breakdown ?? []} emptyLabel="No module activity yet." />
              <SummaryListCard title="Stage Mix" items={analytics?.stage_breakdown ?? []} emptyLabel="No stage data yet." />
              <SummaryListCard title="Top Customers" items={analytics?.top_customers ?? []} emptyLabel="No sessions yet." />
            </div>

            <section style={panelStyle}>
              <div style={panelHeaderStyle}>
                <div>
                  <div style={panelTitleStyle}>Recent Activity</div>
                  <div style={panelSubtitleStyle}>Open any recent session directly from the admin console.</div>
                </div>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                      <th style={thStyle}>Customer</th>
                      <th style={thStyle}>Session</th>
                      <th style={thStyle}>Stage</th>
                      <th style={thStyle}>Created by</th>
                      <th style={thStyle}>Updated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(analytics?.recent_activity ?? []).map((row) => (
                      <tr
                        key={row.session_id}
                        onClick={() => void handleOpen({ customer: { customer_id: row.customer_id }, session: { session_id: row.session_id, module_id: row.module_id } })}
                        style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
                        onMouseEnter={(event) => (event.currentTarget.style.background = 'var(--bg-hover)')}
                        onMouseLeave={(event) => (event.currentTarget.style.background = 'transparent')}
                      >
                        <td style={tdStyle}>{row.customer_name}</td>
                        <td style={tdStyle}>{loadingId === row.session_id ? 'Loading…' : row.session_title}</td>
                        <td style={tdStyle}>{row.stage || 'unknown'}</td>
                        <td style={{ ...tdStyle, color: 'var(--text-muted)', fontFamily: 'monospace', fontSize: 11.5 }}>{row.created_by}</td>
                        <td style={tdStyle}>{formatDate(row.updated_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {(analytics?.recent_activity?.length ?? 0) === 0 ? (
                  <p style={emptyStateStyle}>No recent activity found.</p>
                ) : null}
              </div>
            </section>
          </div>
        ) : activeTab === 'sessions' ? (
          <div style={{ height: '100%', overflowY: 'auto' }}>
            <section style={panelStyle}>
              <div style={panelHeaderStyle}>
                <div>
                  <div style={panelTitleStyle}>All Sessions</div>
                  <div style={panelSubtitleStyle}>
                    {sessionRows.length} session{sessionRows.length === 1 ? '' : 's'} across every customer
                  </div>
                </div>
              </div>
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
                  {sortedSessions.map((row) => (
                    <tr
                      key={row.session.session_id}
                      onClick={() => void handleOpen(row)}
                      style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
                      onMouseEnter={(event) => (event.currentTarget.style.background = 'var(--bg-hover)')}
                      onMouseLeave={(event) => (event.currentTarget.style.background = 'transparent')}
                    >
                      <td style={tdStyle}>{row.customer.name}</td>
                      <td style={tdStyle}>{row.session.title}</td>
                      <td style={{ ...tdStyle, color: 'var(--text-muted)', fontFamily: 'monospace', fontSize: 11.5 }}>
                        {row.session.created_by}
                      </td>
                      <td style={tdStyle}>{row.session.status}</td>
                      <td style={tdStyle}>
                        {loadingId === row.session.session_id ? 'Loading…' : formatDate(row.session.updated_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {sortedSessions.length === 0 ? <p style={emptyStateStyle}>No sessions found.</p> : null}
            </section>
          </div>
        ) : (
          <div style={{ height: '100%', overflowY: 'auto' }}>
            <section style={panelStyle}>
              <div style={panelHeaderStyle}>
                <div>
                  <div style={panelTitleStyle}>Session Feedback</div>
                  <div style={panelSubtitleStyle}>Captured review signals tied to specific sessions.</div>
                </div>
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                    <th style={thStyle}>Customer</th>
                    <th style={thStyle}>Session</th>
                    <th style={thStyle}>User</th>
                    <th style={thStyle}>Score</th>
                    <th style={thStyle}>Signals</th>
                    <th style={thStyle}>Comments</th>
                    <th style={thStyle}>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {recentFeedback.map((row) => (
                    <tr key={`${row.feedback.session_id}:${row.feedback.user_id}`} style={{ borderBottom: '1px solid var(--border)', verticalAlign: 'top' }}>
                      <td style={tdStyle}>{row.customer.name}</td>
                      <td style={tdStyle}>{row.session.title}</td>
                      <td style={tdStyle}>{row.feedback.user_name || row.feedback.user_id}</td>
                      <td style={tdStyle}>{row.feedback.rating}/5</td>
                      <td style={tdStyle}>
                        {formatSignal('Reuse', row.feedback.would_reuse)}
                        <br />
                        {formatSignal('Agree', row.feedback.agreed_with_recommendation)}
                        <br />
                        {formatSignal('Reused output', row.feedback.reused_in_doc_or_meeting)}
                      </td>
                      <td style={{ ...tdStyle, minWidth: 320 }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {row.feedback.most_useful ? <span><strong>Useful:</strong> {row.feedback.most_useful}</span> : null}
                          {row.feedback.missing ? <span><strong>Missing:</strong> {row.feedback.missing}</span> : null}
                          {row.feedback.additional_comments ? <span><strong>Notes:</strong> {row.feedback.additional_comments}</span> : null}
                          {!row.feedback.most_useful && !row.feedback.missing && !row.feedback.additional_comments ? (
                            <span style={{ color: 'var(--text-faint)' }}>No written comments.</span>
                          ) : null}
                        </div>
                      </td>
                      <td style={tdStyle}>{formatDate(row.feedback.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {recentFeedback.length === 0 ? <p style={emptyStateStyle}>No feedback captured yet.</p> : null}
            </section>
          </div>
        )}
      </div>
    </div>
  )
}

function AdminTabButton({ active, children, onClick }: { active: boolean; children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '8px 12px',
        borderRadius: 8,
        border: 'none',
        background: active ? 'var(--bg)' : 'transparent',
        color: active ? 'var(--text)' : 'var(--text-muted)',
        fontSize: 12.5,
        fontWeight: active ? 600 : 500,
        cursor: 'pointer',
      }}
    >
      {children}
    </button>
  )
}

function MetricCard({ label, value, sublabel }: { label: string; value: number; sublabel?: string }) {
  return (
    <div style={metricCardStyle}>
      <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-faint)' }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.03em' }}>{value}</div>
      {sublabel ? <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{sublabel}</div> : null}
    </div>
  )
}

function SummaryListCard({
  title,
  items,
  emptyLabel,
}: {
  title: string
  items: Array<{ label: string; value: number }>
  emptyLabel: string
}) {
  return (
    <section style={panelStyle}>
      <div style={panelHeaderStyle}>
        <div>
          <div style={panelTitleStyle}>{title}</div>
        </div>
      </div>
      {items.length === 0 ? (
        <p style={emptyStateStyle}>{emptyLabel}</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map((item) => (
            <div key={item.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <span style={{ fontSize: 13, color: 'var(--text)' }}>{item.label}</span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>{item.value}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function formatSignal(label: string, value: boolean | null | undefined) {
  if (value === true) return `${label}: yes`
  if (value === false) return `${label}: no`
  return `${label}: unset`
}

function formatDate(value: string) {
  return value ? new Date(value).toLocaleString() : 'Unknown'
}

function headerButtonStyle(disabled: boolean): React.CSSProperties {
  return {
    padding: '6px 12px',
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    color: 'var(--text)',
    fontSize: 12.5,
    cursor: disabled ? 'default' : 'pointer',
    opacity: disabled ? 0.6 : 1,
  }
}

const tabBarStyle: React.CSSProperties = {
  display: 'flex',
  gap: 4,
  padding: 3,
  borderRadius: 10,
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border)',
  width: 'fit-content',
}

const cardGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
  gap: 12,
}

const splitGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 12,
}

const metricCardStyle: React.CSSProperties = {
  border: '1px solid var(--border)',
  borderRadius: 16,
  background: 'rgba(255,253,249,0.9)',
  padding: '14px 16px',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

const panelStyle: React.CSSProperties = {
  border: '1px solid var(--border)',
  borderRadius: 16,
  background: 'rgba(255,253,249,0.9)',
  padding: 16,
}

const panelHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  justifyContent: 'space-between',
  gap: 12,
  marginBottom: 12,
}

const panelTitleStyle: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  color: 'var(--text)',
}

const panelSubtitleStyle: React.CSSProperties = {
  fontSize: 12,
  color: 'var(--text-muted)',
  marginTop: 4,
}

const emptyStateStyle: React.CSSProperties = {
  padding: '8px 0 0',
  fontSize: 12,
  color: 'var(--text-faint)',
}

const thStyle: React.CSSProperties = {
  padding: '8px 12px',
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
  color: 'var(--text-faint)',
  cursor: 'pointer',
}

const tdStyle: React.CSSProperties = {
  padding: '10px 12px',
  color: 'var(--text)',
  lineHeight: 1.5,
}
