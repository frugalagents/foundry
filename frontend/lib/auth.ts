'use client';
import type { UserTokenPayload } from './types';

export function getToken(): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(/(?:^|; )id_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function decodeToken(token: string): UserTokenPayload | null {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as UserTokenPayload;
  } catch {
    return null;
  }
}

export function getUser(): UserTokenPayload | null {
  const token = getToken();
  return token ? decodeToken(token) : null;
}

export function isAdmin(): boolean {
  const user = getUser();
  return user?.['custom:role'] === 'admin';
}

export function logout(): void {
  document.cookie = 'id_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
  const domain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN;
  const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID;
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? window.location.origin;
  if (domain && clientId) {
    const params = new URLSearchParams({ client_id: clientId, logout_uri: `${appUrl}/login` });
    window.location.href = `https://${domain}/logout?${params}`;
  } else {
    window.location.href = '/login';
  }
}

export function setToken(token: string): void {
  const expires = new Date(Date.now() + 3600 * 1000).toUTCString();
  document.cookie = `id_token=${encodeURIComponent(token)}; expires=${expires}; path=/; SameSite=Strict`;
}

export function getAccessToken(): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(/(?:^|; )access_token=([^;]*)/);
  if (match) return decodeURIComponent(match[1]);
  return process.env.NODE_ENV === 'development' ? getToken() : null;
}

export function setAccessToken(token: string): void {
  const expires = new Date(Date.now() + 3600 * 1000).toUTCString();
  document.cookie = `access_token=${encodeURIComponent(token)}; expires=${expires}; path=/; SameSite=Strict`;
}

export function getRefreshToken(): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(/(?:^|; )refresh_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function setRefreshToken(token: string): void {
  // Refresh tokens are long-lived; store for 30 days
  const expires = new Date(Date.now() + 30 * 24 * 3600 * 1000).toUTCString();
  document.cookie = `refresh_token=${encodeURIComponent(token)}; expires=${expires}; path=/; SameSite=Strict`;
}

/**
 * Exchange the stored refresh_token for a fresh id_token.
 * Returns the new id_token on success, or null if refresh failed.
 */
export async function refreshIdToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  const domain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN ?? '';
  const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? '';
  if (!domain || !clientId) return null;

  try {
    const body = new URLSearchParams({
      grant_type: 'refresh_token',
      client_id: clientId,
      refresh_token: refreshToken,
    });
    const res = await fetch(`https://${domain}/oauth2/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });
    if (!res.ok) return null;
    const data = await res.json() as { id_token?: string; access_token?: string };
    if (!data.access_token) return null;
    if (data.id_token) setToken(data.id_token);
    setAccessToken(data.access_token);
    return data.access_token;
  } catch {
    return null;
  }
}

/** Build a mock JWT for local dev (no real signature). */
export function createDevToken(email: string, isAdminUser = false): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const payload = btoa(
    JSON.stringify({
      sub: 'dev-user-001',
      email,
      'cognito:groups': isAdminUser ? ['admin', 'user'] : ['user'],
      'custom:role': isAdminUser ? 'admin' : 'user',
      'custom:display_name': email.split('@')[0],
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 3600,
    })
  );
  return `${header}.${payload}.dev-signature`;
}
