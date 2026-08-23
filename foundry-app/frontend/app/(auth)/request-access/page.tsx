'use client'

import { FormEvent, useCallback, useEffect, useState } from 'react'
import {
  activateAccessRequest,
  ApiError,
  getAccessRequestStatus,
  requestAccess,
} from '@/lib/api'
import type { AccessRequestStatusView } from '@/lib/types'

const STORAGE_KEY = 'foundry_access_request'

type SavedRequest = {
  requestId: string
  requestSecret: string
}

function readSavedRequest(): SavedRequest | null {
  if (typeof window === 'undefined') return null
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '') as Partial<SavedRequest>
    if (parsed.requestId && parsed.requestSecret) {
      return { requestId: parsed.requestId, requestSecret: parsed.requestSecret }
    }
  } catch {
    // Ignore invalid or absent saved request state.
  }
  return null
}

export default function RequestAccessPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [reason, setReason] = useState('')
  const [website, setWebsite] = useState('')
  const [saved, setSaved] = useState<SavedRequest | null>(null)
  const [requestStatus, setRequestStatus] = useState<AccessRequestStatusView | null>(null)
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState('')

  const refreshStatus = useCallback(async (current: SavedRequest) => {
    setChecking(true)
    try {
      const nextStatus = await getAccessRequestStatus(current.requestId, current.requestSecret)
      setRequestStatus(nextStatus)
      setEmail(nextStatus.email)
      setError('')
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        localStorage.removeItem(STORAGE_KEY)
        setSaved(null)
        setRequestStatus(null)
        setError('This saved request is no longer available. Submit a new request.')
      } else {
        setError(err instanceof ApiError && err.detail ? err.detail : 'Could not check request status')
      }
    } finally {
      setChecking(false)
    }
  }, [])

  useEffect(() => {
    const existing = readSavedRequest()
    if (!existing) return
    setSaved(existing)
    void refreshStatus(existing)
  }, [refreshStatus])

  useEffect(() => {
    if (!saved || requestStatus?.status !== 'pending') return
    const timer = window.setInterval(() => void refreshStatus(saved), 10_000)
    return () => window.clearInterval(timer)
  }, [refreshStatus, requestStatus?.status, saved])

  async function handleRequest(event: FormEvent) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const created = await requestAccess({ name, email, reason, website })
      const nextSaved = {
        requestId: created.request_id,
        requestSecret: created.request_secret,
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(nextSaved))
      setSaved(nextSaved)
      await refreshStatus(nextSaved)
    } catch (err) {
      setError(err instanceof ApiError && err.detail ? err.detail : 'Could not submit access request')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleActivate(event: FormEvent) {
    event.preventDefault()
    if (!saved) return
    setError('')
    if (password !== confirmPassword) {
      setError('The passwords do not match')
      return
    }
    setSubmitting(true)
    try {
      const nextStatus = await activateAccessRequest(saved.requestId, saved.requestSecret, password)
      setRequestStatus(nextStatus)
      setPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(err instanceof ApiError && err.detail ? err.detail : 'Could not activate the account')
    } finally {
      setSubmitting(false)
    }
  }

  function startOver() {
    localStorage.removeItem(STORAGE_KEY)
    setSaved(null)
    setRequestStatus(null)
    setName('')
    setEmail('')
    setReason('')
    setPassword('')
    setConfirmPassword('')
    setError('')
  }

  return (
    <main style={pageStyle}>
      <div style={shellStyle}>
        <div style={{ textAlign: 'center' }}>
          <div style={logoStyle}>⚡</div>
          <h1 style={{ fontSize: 22, margin: '0 0 6px', color: 'var(--text)' }}>Request Foundry access</h1>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: 13, lineHeight: 1.55 }}>
            Send a short request to the Foundry administrators. Keep this browser available to see the decision.
          </p>
        </div>

        <section style={cardStyle}>
          {!saved ? (
            <form onSubmit={handleRequest} style={formStyle}>
              <Field label="Name">
                <input value={name} onChange={(event) => setName(event.target.value)} required minLength={2} maxLength={120} style={inputStyle} />
              </Field>
              <Field label="Email">
                <input value={email} onChange={(event) => setEmail(event.target.value)} required type="email" maxLength={320} style={inputStyle} />
              </Field>
              <Field label="Why do you need access?">
                <textarea value={reason} onChange={(event) => setReason(event.target.value)} required minLength={5} maxLength={2000} rows={5} style={{ ...inputStyle, resize: 'vertical' }} />
              </Field>
              <div aria-hidden="true" style={{ position: 'absolute', left: '-10000px' }}>
                <label>
                  Website
                  <input value={website} onChange={(event) => setWebsite(event.target.value)} tabIndex={-1} autoComplete="off" />
                </label>
              </div>
              <button type="submit" disabled={submitting} style={primaryButtonStyle(submitting)}>
                {submitting ? 'Sending request…' : 'Request access'}
              </button>
            </form>
          ) : requestStatus?.status === 'approved' ? (
            <form onSubmit={handleActivate} style={formStyle}>
              <StatusBadge status="approved" />
              <div>
                <h2 style={sectionTitleStyle}>Your request was approved</h2>
                <p style={bodyStyle}>Choose a password for {requestStatus.email}. No temporary password or email code is required.</p>
              </div>
              <Field label="New password" hint="At least 12 characters with uppercase, lowercase, and a number.">
                <input value={password} onChange={(event) => setPassword(event.target.value)} required type="password" minLength={12} maxLength={128} autoComplete="new-password" style={inputStyle} />
              </Field>
              <Field label="Confirm password">
                <input value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required type="password" minLength={12} maxLength={128} autoComplete="new-password" style={inputStyle} />
              </Field>
              <button type="submit" disabled={submitting} style={primaryButtonStyle(submitting)}>
                {submitting ? 'Activating account…' : 'Set password and activate'}
              </button>
            </form>
          ) : requestStatus?.status === 'activated' ? (
            <div style={formStyle}>
              <StatusBadge status="activated" />
              <div>
                <h2 style={sectionTitleStyle}>Your account is ready</h2>
                <p style={bodyStyle}>Sign in with {requestStatus.email} and the password you just created.</p>
              </div>
              <a href="/login/" style={linkButtonStyle}>Continue to sign in</a>
            </div>
          ) : requestStatus?.status === 'rejected' ? (
            <div style={formStyle}>
              <StatusBadge status="rejected" />
              <div>
                <h2 style={sectionTitleStyle}>Access was not approved</h2>
                <p style={bodyStyle}>{requestStatus.decision_note || 'Contact a Foundry administrator if you need more information.'}</p>
              </div>
              <button type="button" onClick={startOver} style={secondaryButtonStyle}>Submit another request</button>
            </div>
          ) : (
            <div style={formStyle}>
              <StatusBadge status="pending" />
              <div>
                <h2 style={sectionTitleStyle}>Your request is with an administrator</h2>
                <p style={bodyStyle}>
                  This page checks automatically. You can also return in this browser later; the private request token is stored only on this device.
                </p>
              </div>
              <button type="button" onClick={() => saved && void refreshStatus(saved)} disabled={checking} style={secondaryButtonStyle}>
                {checking ? 'Checking…' : 'Check status'}
              </button>
            </div>
          )}

          {error ? <p role="alert" style={{ margin: 0, color: 'var(--red)', fontSize: 12.5, lineHeight: 1.5 }}>{error}</p> : null}
        </section>

        <a href="/login/" style={{ color: 'var(--text-muted)', fontSize: 12.5, textAlign: 'center', textDecoration: 'none' }}>
          Back to sign in
        </a>
      </div>
    </main>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
      <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)' }}>{label}</span>
      {children}
      {hint ? <span style={{ fontSize: 11.5, color: 'var(--text-faint)', lineHeight: 1.45 }}>{hint}</span> : null}
    </label>
  )
}

function StatusBadge({ status }: { status: 'pending' | 'approved' | 'rejected' | 'activated' }) {
  const config = {
    pending: { label: 'Pending review', color: '#a16207', background: '#fef3c7' },
    approved: { label: 'Approved', color: '#166534', background: '#dcfce7' },
    rejected: { label: 'Not approved', color: '#991b1b', background: '#fee2e2' },
    activated: { label: 'Active', color: '#166534', background: '#dcfce7' },
  }[status]
  return (
    <span style={{
      alignSelf: 'flex-start',
      padding: '5px 9px',
      borderRadius: 999,
      color: config.color,
      background: config.background,
      fontSize: 11.5,
      fontWeight: 700,
    }}>
      {config.label}
    </span>
  )
}

const pageStyle: React.CSSProperties = {
  minHeight: '100vh',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 24,
  background: 'var(--bg)',
}

const shellStyle: React.CSSProperties = {
  width: '100%',
  maxWidth: 520,
  display: 'flex',
  flexDirection: 'column',
  gap: 24,
}

const logoStyle: React.CSSProperties = {
  width: 48,
  height: 48,
  borderRadius: 12,
  background: 'var(--accent)',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginBottom: 16,
  fontSize: 22,
}

const cardStyle: React.CSSProperties = {
  position: 'relative',
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius)',
  padding: 24,
  display: 'flex',
  flexDirection: 'column',
  gap: 18,
}

const formStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 18,
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  padding: '10px 12px',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-sm)',
  background: 'var(--bg)',
  color: 'var(--text)',
  fontSize: 13,
  fontFamily: 'inherit',
  outline: 'none',
}

const sectionTitleStyle: React.CSSProperties = {
  margin: '0 0 6px',
  fontSize: 17,
  color: 'var(--text)',
}

const bodyStyle: React.CSSProperties = {
  margin: 0,
  fontSize: 13,
  lineHeight: 1.6,
  color: 'var(--text-muted)',
}

function primaryButtonStyle(disabled: boolean): React.CSSProperties {
  return {
    width: '100%',
    padding: '11px 16px',
    background: 'var(--accent)',
    color: '#fff',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    fontSize: 14,
    fontWeight: 600,
    cursor: disabled ? 'default' : 'pointer',
    opacity: disabled ? 0.65 : 1,
  }
}

const secondaryButtonStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 16px',
  background: 'var(--bg)',
  color: 'var(--text)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-sm)',
  fontSize: 13,
  fontWeight: 600,
  cursor: 'pointer',
}

const linkButtonStyle: React.CSSProperties = {
  display: 'block',
  textAlign: 'center',
  padding: '11px 16px',
  background: 'var(--accent)',
  color: '#fff',
  borderRadius: 'var(--radius-sm)',
  fontSize: 14,
  fontWeight: 600,
  textDecoration: 'none',
}
