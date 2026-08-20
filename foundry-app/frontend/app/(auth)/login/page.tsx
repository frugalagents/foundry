'use client'

import { useState, useEffect } from 'react'
import { isAuthenticated, setToken, createDevToken, navigateToHome } from '@/lib/auth'

const COGNITO_DOMAIN = process.env.NEXT_PUBLIC_COGNITO_DOMAIN ?? ''
const CLIENT_ID      = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? ''
const APP_URL        = process.env.NEXT_PUBLIC_APP_URL ?? ''
const IS_DEV = !COGNITO_DOMAIN || process.env.NODE_ENV === 'development'

const REDIRECT_URI = APP_URL ? `${APP_URL}/callback` : (
  typeof window !== 'undefined' ? `${window.location.origin}/callback` : ''
)

async function generatePKCE(): Promise<{ verifier: string; challenge: string }> {
  const array = new Uint8Array(32)
  crypto.getRandomValues(array)
  const verifier = btoa(String.fromCharCode(...array))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')

  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))
  const challenge = btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')

  return { verifier, challenge }
}

async function redirectToCognito() {
  const { verifier, challenge } = await generatePKCE()
  sessionStorage.setItem('pkce_verifier', verifier)

  const params = new URLSearchParams({
    response_type: 'code',
    client_id:     CLIENT_ID,
    redirect_uri:  REDIRECT_URI,
    scope:         'openid email profile',
    code_challenge: challenge,
    code_challenge_method: 'S256',
  })
  window.location.href = `https://${COGNITO_DOMAIN}/oauth2/authorize?${params}`
}

export default function LoginPage() {
  const [devId,    setDevId]    = useState('dev-user-01')
  const [devName,  setDevName]  = useState('Developer')
  const [devAdmin, setDevAdmin] = useState(false)

  useEffect(() => {
    if (isAuthenticated()) { navigateToHome(); return }
    // In production, auto-redirect to Cognito (→ Midway) — no button click needed
    if (!IS_DEV) {
      redirectToCognito()
    }
  }, [])

  function handleDevLogin() {
    const token = createDevToken(devId.trim() || 'dev-user', devName.trim() || 'Developer', devAdmin)
    setToken(token)
    navigateToHome()
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg)',
      padding: '24px',
    }}>
      <div style={{
        width: '100%',
        maxWidth: '400px',
        display: 'flex',
        flexDirection: 'column',
        gap: '32px',
      }}>
        {/* Logo + title */}
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: 48, height: 48,
            borderRadius: 12,
            background: 'var(--accent)',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 16,
            fontSize: 22,
          }}>⚡</div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)', marginBottom: 6 }}>
            Enterprise AI Foundry
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Sign in to access your AI platform advisor
          </p>
        </div>

        <div style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
        }}>
          {!IS_DEV ? (
            <button
              onClick={redirectToCognito}
              style={btnStyle}
              onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
              onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
            >
              Sign in with Amazon SSO
            </button>
          ) : (
            <>
              <p style={{
                fontSize: 11, fontWeight: 600, letterSpacing: '0.08em',
                textTransform: 'uppercase', color: 'var(--text-muted)',
              }}>Dev mode</p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <input value={devId} onChange={(e) => setDevId(e.target.value)}
                  placeholder="User ID" style={inputStyle} />
                <input value={devName} onChange={(e) => setDevName(e.target.value)}
                  placeholder="Display name" style={inputStyle} />
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-muted)', cursor: 'pointer' }}>
                  <input type="checkbox" checked={devAdmin} onChange={(e) => setDevAdmin(e.target.checked)}
                    style={{ accentColor: 'var(--accent)', width: 14, height: 14 }} />
                  Admin access
                </label>
              </div>

              <button onClick={handleDevLogin} style={btnStyle}
                onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
                onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}>
                Sign in
              </button>
            </>
          )}
        </div>

        <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-faint)' }}>
          Enterprise AI Foundry · Internal tool
        </p>
      </div>
    </div>
  )
}

const btnStyle: React.CSSProperties = {
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

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '9px 12px',
  background: 'var(--bg)',
  border: '1px solid var(--border)',
  borderRadius: 'var(--radius-sm)',
  color: 'var(--text)',
  fontSize: 13,
  outline: 'none',
}
