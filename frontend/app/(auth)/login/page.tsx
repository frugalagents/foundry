'use client';
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { setToken, createDevToken } from '@/lib/auth';

const COGNITO_DOMAIN = process.env.NEXT_PUBLIC_COGNITO_DOMAIN ?? '';
const CLIENT_ID = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? '';
const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? 'http://localhost:3000';
const IS_DEV = process.env.NODE_ENV === 'development' || !COGNITO_DOMAIN || process.env.NEXT_PUBLIC_DEV_MODE === 'true';
const REDIRECT_URI = `${APP_URL}/api/auth/callback`;

/** Generate a random PKCE code_verifier and its SHA-256 code_challenge. */
async function generatePKCE(): Promise<{ verifier: string; challenge: string }> {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  const verifier = btoa(String.fromCharCode(...array))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');

  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  const challenge = btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');

  return { verifier, challenge };
}

async function redirectToCognito() {
  const { verifier, challenge } = await generatePKCE();
  sessionStorage.setItem('pkce_verifier', verifier);

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    scope: 'openid email profile',
    code_challenge: challenge,
    code_challenge_method: 'S256',
  });
  window.location.href = `https://${COGNITO_DOMAIN}/oauth2/authorize?${params}`;
}

export default function LoginPage() {
  const [devEmail, setDevEmail] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);

  // In production, auto-redirect to Midway immediately — no button click needed
  useEffect(() => {
    if (!IS_DEV) {
      redirectToCognito();
    }
  }, []);

  function devLogin() {
    const email = devEmail || 'dev@example.com';
    setToken(createDevToken(email, isAdmin));
    window.location.href = '/customers';
  }

  return (
    <div
      style={{
        width: 400,
        background: 'var(--bg-card)',
        border: '1px solid var(--border-default)',
        borderRadius: 'var(--radius-lg)',
        padding: '40px 32px',
        boxShadow: 'var(--shadow-elevated)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 24,
      }}
    >
      {/* Logo */}
      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            width: 56,
            height: 56,
            background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-purple))',
            borderRadius: 14,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 24,
            fontWeight: 700,
            color: '#fff',
            margin: '0 auto 16px',
          }}
        >
          P
        </div>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>
          Platform Advisor
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          Enterprise AI Agent Platform Strategy
        </p>
      </div>

      {/* Cognito SSO Button */}
      {!IS_DEV && (
        <Button
          variant="primary"
          size="lg"
          onClick={redirectToCognito}
          style={{ width: '100%' }}
        >
          Sign in with Amazon SSO
        </Button>
      )}

      {/* Dev Login */}
      {IS_DEV && (
        <div
          style={{
            width: '100%',
            borderTop: '1px solid var(--border-default)',
            paddingTop: 20,
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          <p
            style={{
              fontSize: 11,
              color: 'var(--text-muted)',
              textAlign: 'center',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
            }}
          >
            Local dev login
          </p>
          <input
            type="email"
            placeholder="dev@example.com"
            value={devEmail}
            onChange={(e) => setDevEmail(e.target.value)}
            style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-primary)',
              padding: '8px 12px',
              fontSize: 13,
              outline: 'none',
              width: '100%',
            }}
          />
          <label
            style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-secondary)', cursor: 'pointer' }}
          >
            <input type="checkbox" checked={isAdmin} onChange={(e) => setIsAdmin(e.target.checked)} />
            Sign in as admin
          </label>
          <Button variant="secondary" size="md" onClick={devLogin} style={{ width: '100%' }}>
            Continue as Dev User
          </Button>
        </div>
      )}
    </div>
  );
}
