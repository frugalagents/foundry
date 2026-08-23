'use client'

import { useMemo, useState } from 'react'
import { ApiError, approveAccessRequest, rejectAccessRequest } from '@/lib/api'
import type { AdminAccessRequest } from '@/lib/types'

export default function AdminAccessRequestsPanel({
  requests,
  onChange,
}: {
  requests: AdminAccessRequest[]
  onChange: (request: AdminAccessRequest) => void
}) {
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState('')

  const sorted = useMemo(() => {
    const statusOrder = { pending: 0, approved: 1, activated: 2, rejected: 3 }
    return [...requests].sort((a, b) => {
      const statusDiff = statusOrder[a.status] - statusOrder[b.status]
      if (statusDiff !== 0) return statusDiff
      return +new Date(b.requested_at) - +new Date(a.requested_at)
    })
  }, [requests])

  async function approve(request: AdminAccessRequest) {
    if (!window.confirm(`Approve Foundry access for ${request.email}?`)) return
    setBusyId(request.request_id)
    setError('')
    try {
      const updated = await approveAccessRequest(request.request_id)
      onChange(updated)
    } catch (err) {
      setError(err instanceof ApiError && err.detail ? err.detail : 'Could not approve the request')
    } finally {
      setBusyId(null)
    }
  }

  async function reject(request: AdminAccessRequest) {
    const note = window.prompt(
      `Why is access for ${request.email} not being approved? This note will be shown to the requester.`,
      '',
    )
    if (note === null) return
    setBusyId(request.request_id)
    setError('')
    try {
      const updated = await rejectAccessRequest(request.request_id, note)
      onChange(updated)
    } catch (err) {
      setError(err instanceof ApiError && err.detail ? err.detail : 'Could not reject the request')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div style={{ height: '100%', overflowY: 'auto' }}>
      <section style={panelStyle}>
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>Access requests</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.5 }}>
            Approving creates a native Cognito account. The requester then sets a password from their saved request page.
          </div>
        </div>

        {error ? <p style={{ margin: '0 0 12px', color: 'var(--red)', fontSize: 12.5 }}>{error}</p> : null}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {sorted.map((request) => {
            const busy = busyId === request.request_id
            return (
              <article key={request.request_id} style={requestCardStyle}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <span style={{ color: 'var(--text)', fontWeight: 650, fontSize: 13.5 }}>{request.name}</span>
                      <StatusChip status={request.status} />
                    </div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12.5, marginTop: 4 }}>{request.email}</div>
                  </div>
                  <div style={{ color: 'var(--text-faint)', fontSize: 11.5 }}>
                    {new Date(request.requested_at).toLocaleString()}
                  </div>
                </div>

                <p style={{ margin: 0, color: 'var(--text)', fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                  {request.reason}
                </p>

                {request.decision_note ? (
                  <div style={{ padding: '9px 11px', borderRadius: 9, background: 'var(--bg)', color: 'var(--text-muted)', fontSize: 12 }}>
                    <strong style={{ color: 'var(--text)' }}>Decision note:</strong> {request.decision_note}
                  </div>
                ) : null}

                {request.status === 'pending' ? (
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button type="button" disabled={busy} onClick={() => void approve(request)} style={actionButtonStyle('#166534', '#dcfce7', busy)}>
                      {busy ? 'Working…' : 'Approve'}
                    </button>
                    <button type="button" disabled={busy} onClick={() => void reject(request)} style={actionButtonStyle('#991b1b', '#fee2e2', busy)}>
                      Reject
                    </button>
                  </div>
                ) : null}
              </article>
            )
          })}
        </div>

        {sorted.length === 0 ? (
          <p style={{ margin: 0, padding: '8px 0', color: 'var(--text-faint)', fontSize: 12.5 }}>No access requests yet.</p>
        ) : null}
      </section>
    </div>
  )
}

function StatusChip({ status }: { status: AdminAccessRequest['status'] }) {
  const config = {
    pending: { label: 'Pending', color: '#a16207', background: '#fef3c7' },
    approved: { label: 'Approved', color: '#166534', background: '#dcfce7' },
    activated: { label: 'Active', color: '#166534', background: '#dcfce7' },
    rejected: { label: 'Rejected', color: '#991b1b', background: '#fee2e2' },
  }[status]
  return (
    <span style={{
      padding: '4px 8px',
      borderRadius: 999,
      color: config.color,
      background: config.background,
      fontSize: 10.5,
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.04em',
    }}>
      {config.label}
    </span>
  )
}

function actionButtonStyle(color: string, background: string, disabled: boolean): React.CSSProperties {
  return {
    padding: '7px 11px',
    border: 'none',
    borderRadius: 8,
    color,
    background,
    fontSize: 12,
    fontWeight: 650,
    cursor: disabled ? 'default' : 'pointer',
    opacity: disabled ? 0.6 : 1,
  }
}

const panelStyle: React.CSSProperties = {
  border: '1px solid var(--border)',
  borderRadius: 16,
  background: 'rgba(255,253,249,0.9)',
  padding: 16,
}

const requestCardStyle: React.CSSProperties = {
  border: '1px solid var(--border)',
  borderRadius: 12,
  background: 'var(--bg-elevated)',
  padding: 14,
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}
