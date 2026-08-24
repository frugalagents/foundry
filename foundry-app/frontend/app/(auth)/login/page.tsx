'use client'

import { useEffect, useState, type CSSProperties } from 'react'
import {
  createDevToken,
  guestAccessExpiresAt,
  isAuthenticated,
  isGuestAccessOpen,
  navigateToHome,
  setToken,
  startGuestLogin,
  startInternalLogin,
  type LoginMode,
} from '@/lib/auth'

const IS_DEV = process.env.NODE_ENV === 'development'

function guestExpiryLabel() {
  const raw = guestAccessExpiresAt()
  if (!raw) return ''
  const value = Date.parse(raw)
  if (Number.isNaN(value)) return raw
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export default function LoginPage() {
  const [devId, setDevId] = useState('dev-user-01')
  const [devName, setDevName] = useState('Developer')
  const [devAdmin, setDevAdmin] = useState(false)
  const [loginMode, setLoginMode] = useState<LoginMode>('internal')

  useEffect(() => {
    if (isAuthenticated()) {
      navigateToHome()
      return
    }
    if (typeof window === 'undefined') return

    const params = new URLSearchParams(window.location.search)
    const mode = params.get('mode')
    const nextMode: LoginMode = mode === 'guest' || mode === 'external' ? 'guest' : 'internal'
    setLoginMode(nextMode)

    if (!IS_DEV && nextMode === 'internal') {
      void startInternalLogin()
    }
  }, [])

  function handleDevLogin() {
    const token = createDevToken(devId.trim() || 'dev-user', devName.trim() || 'Developer', devAdmin)
    setToken(token)
    navigateToHome()
  }

  const guestOpen = isGuestAccessOpen()
  const guestExpires = guestExpiryLabel()

  return (
    <div style={pageStyle}>
      <div style={shellStyle}>
        <div style={{ textAlign: 'center' }}>
          <div style={logoStyle}>⚡</div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)', margin: '0 0 6px' }}>
            Enterprise AI Foundry
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: 0 }}>
            {loginMode === 'guest'
              ? 'External guest access for a time-bounded event window'
              : 'Amazon users sign in with enterprise SSO by default'}
          </p>
        </div>

        <div style={cardStyle}>
          {!IS_DEV ? (
            loginMode === 'guest' ? (
              guestOpen ? (
                <>
                  <p style={bodyStyle}>
                    This entry point is for external event guests. Enter through this guest path only if you were invited to the event. {guestExpires ? `Guest access closes ${guestExpires}.` : ''}
                  </p>
                  <button
                    onClick={() => void startGuestLogin()}
                    style={primaryButtonStyle}
                    onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
                    onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
                  >
                    Continue with guest email
                  </button>
                  <a href="/request-access/" style={secondaryLinkStyle}>
                    Need guest access? Request it here
                  </a>
                  <a href="/login/" style={textLinkStyle}>
                    Amazon user? Use SSO
                  </a>
                </>
              ) : (
                <>
                  <p style={bodyStyle}>
                    Guest access for this event has ended. {guestExpires ? `The guest window closed ${guestExpires}.` : 'The guest window is no longer active.'}
                  </p>
                  <a href="/login/" style={secondaryLinkStyle}>
                    Amazon user? Use SSO
                  </a>
                </>
              )
            ) : (
              <>
                <p style={bodyStyle}>
                  Redirecting to Amazon SSO. If the redirect does not start, continue manually below. External guests should use the dedicated guest entry point instead of the default app URL.
                </p>
                <button
                  onClick={() => void startInternalLogin()}
                  style={primaryButtonStyle}
                  onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
                  onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
                >
                  Continue with Amazon SSO
                </button>
                {guestOpen ? (
                  <a href="/login/?mode=guest" style={secondaryLinkStyle}>
                    External guest access
                  </a>
                ) : null}
              </>
            )
          ) : (
            <>
              <p style={eyebrowStyle}>Dev mode</p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <input
                  value={devId}
                  onChange={(e) => setDevId(e.target.value)}
                  placeholder="User ID"
                  style={inputStyle}
                />
                <input
                  value={devName}
                  onChange={(e) => setDevName(e.target.value)}
                  placeholder="Display name"
                  style={inputStyle}
                />
                <label style={checkboxLabelStyle}>
                  <input
                    type="checkbox"
                    checked={devAdmin}
                    onChange={(e) => setDevAdmin(e.target.checked)}
                    style={{ accentColor: 'var(--accent)', width: 14, height: 14 }}
                  />
                  Admin access
                </label>
              </div>

              <button
                onClick={handleDevLogin}
                style={primaryButtonStyle}
                onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
                onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
              >
                Sign in
              </button>
            </>
          )}
        </div>

        <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-faint)', margin: 0 }}>
          Enterprise AI Foundry · Internal SSO plus bounded guest access
        </p>
      </div>
    </div>
  )
}

const pageStyle: CSSProperties = {
  minHeight: '100vh',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'var(--bg)',
  padding: '24px',
}

const shellStyle: CSSProperties = {
  width: '100%',
  maxWidth: '420px',
  display: 'flex',
  flexDirection: 'column',
  gap: '32px',
}

const logoStyle: CSSProperties = {
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

const cardStyle: CSSProperties = {
  background: 'var(--bg-elevated)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius)',
  padding: '24px',
  display: 'flex',
  flexDirection: 'column',
  gap: '16px',
}

const eyebrowStyle: CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: 'var(--text-muted)',
  margin: 0,
}

const bodyStyle: CSSProperties = {
  color: 'var(--text-muted)',
  fontSize: 13,
  lineHeight: 1.55,
  margin: 0,
}

const primaryButtonStyle: CSSProperties = {
  width: '100%',
  padding: '11px 16px',
  background: 'var(--accent)',
  color: '#fff',
  border: 'none',
  borderRadius: 'var(--radius-sm)',
  fontSize: 14,
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'opacity var(--transition)',
}

const secondaryLinkStyle: CSSProperties = {
  width: '100%',
  padding: '11px 16px',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-sm)',
  fontSize: 13,
  fontWeight: 600,
  color: 'var(--text)',
  textDecoration: 'none',
  textAlign: 'center',
  background: 'var(--bg)',
}

const textLinkStyle: CSSProperties = {
  color: 'var(--text-muted)',
  fontSize: 12.5,
  textDecoration: 'none',
  textAlign: 'center',
}

const inputStyle: CSSProperties = {
  width: '100%',
  padding: '9px 12px',
  background: 'var(--bg)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text)',
  fontSize: 13,
  outline: 'none',
}

const checkboxLabelStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  fontSize: 13,
  color: 'var(--text-muted)',
  cursor: 'pointer',
}
