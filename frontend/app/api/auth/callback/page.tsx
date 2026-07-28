'use client';
/**
 * Cognito OAuth2 callback handler.
 *
 * Flow:
 *   1. Cognito redirects here with ?code=...
 *   2. We retrieve the PKCE code_verifier from sessionStorage
 *   3. POST to Cognito /oauth2/token to exchange code → tokens
 *   4. Store id_token in a secure cookie
 *   5. Redirect to /customers
 */
import { useEffect, useState } from 'react';
import { setToken, setAccessToken, setRefreshToken } from '@/lib/auth';

const COGNITO_DOMAIN = process.env.NEXT_PUBLIC_COGNITO_DOMAIN ?? '';
const CLIENT_ID = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? '';
const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? 'http://localhost:3000';
const REDIRECT_URI = `${APP_URL}/api/auth/callback`;

type Status = 'exchanging' | 'success' | 'error';

export default function CallbackPage() {
  const [status, setStatus] = useState<Status>('exchanging');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const error = params.get('error');
    const errorDesc = params.get('error_description');

    if (error) {
      setErrorMsg(`${error}: ${errorDesc ?? 'unknown error'}`);
      setStatus('error');
      return;
    }

    if (!code) {
      setErrorMsg('No authorization code received from Cognito.');
      setStatus('error');
      return;
    }

    const verifier = sessionStorage.getItem('pkce_verifier');
    if (!verifier) {
      setErrorMsg('PKCE verifier missing — please try logging in again.');
      setStatus('error');
      return;
    }

    async function exchangeCode() {
      const body = new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: CLIENT_ID,
        code: code!,
        redirect_uri: REDIRECT_URI,
        code_verifier: verifier!,
      });

      const res = await fetch(`https://${COGNITO_DOMAIN}/oauth2/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
      });

      if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(`Token exchange failed (${res.status}): ${text}`);
      }

      const tokens = await res.json() as {
        id_token: string;
        access_token: string;
        refresh_token: string;
        expires_in: number;
      };

      sessionStorage.removeItem('pkce_verifier');
      setToken(tokens.id_token);
      setAccessToken(tokens.access_token);
      if (tokens.refresh_token) setRefreshToken(tokens.refresh_token);
      setStatus('success');
      window.location.replace('/customers');
    }

    exchangeCode().catch((err: Error) => {
      setErrorMsg(err.message);
      setStatus('error');
    });
  }, []);

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-primary)',
        flexDirection: 'column',
        gap: 16,
      }}
    >
      {status === 'exchanging' && (
        <>
          <div
            style={{
              width: 40,
              height: 40,
              border: '3px solid var(--border-default)',
              borderTopColor: 'var(--accent-blue)',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
            }}
          />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Completing sign-in…</p>
        </>
      )}

      {status === 'error' && (
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-lg)',
            padding: '32px 40px',
            textAlign: 'center',
            maxWidth: 420,
          }}
        >
          <p style={{ color: 'var(--text-primary)', fontWeight: 600, marginBottom: 8 }}>
            Sign-in failed
          </p>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 24 }}>
            {errorMsg}
          </p>
          <a
            href="/login"
            style={{
              display: 'inline-block',
              padding: '8px 20px',
              background: 'var(--accent)',
              color: 'var(--accent-fg)',
              borderRadius: 'var(--radius-sm)',
              fontSize: 13,
              textDecoration: 'none',
            }}
          >
            Back to login
          </a>
        </div>
      )}
    </div>
  );
}
