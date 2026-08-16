'use client'

// ── Token storage (cookies, like platform-advisor) ────────────────────────────

export function getToken(): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(/(?:^|; )id_token=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : null
}

export function setToken(token: string): void {
  const expires = new Date(Date.now() + 3600 * 1000).toUTCString()
  document.cookie = `id_token=${encodeURIComponent(token)}; expires=${expires}; path=/; SameSite=Strict`
}

export function clearToken(): void {
  document.cookie = 'id_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
}

export function getAccessToken(): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(/(?:^|; )access_token=([^;]*)/)
  if (match) return decodeURIComponent(match[1])
  // In local dev with no Cognito, fall back to id_token
  return process.env.NODE_ENV === 'development' ? getToken() : null
}

export function setAccessToken(token: string): void {
  const expires = new Date(Date.now() + 3600 * 1000).toUTCString()
  document.cookie = `access_token=${encodeURIComponent(token)}; expires=${expires}; path=/; SameSite=Strict`
}

export function getRefreshToken(): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(/(?:^|; )refresh_token=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : null
}

export function setRefreshToken(token: string): void {
  // Refresh tokens are long-lived; store for 30 days
  const expires = new Date(Date.now() + 30 * 24 * 3600 * 1000).toUTCString()
  document.cookie = `refresh_token=${encodeURIComponent(token)}; expires=${expires}; path=/; SameSite=Strict`
}

// ── Token decoding ────────────────────────────────────────────────────────────

export function getClaims(): Record<string, unknown> | null {
  const token = getToken()
  if (!token) return null
  try {
    return JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
  } catch {
    return null
  }
}

export function getUserId(): string | null {
  return (getClaims()?.sub as string) ?? null
}

export function getUserName(): string | null {
  const c = getClaims()
  return (c?.name ?? c?.email ?? c?.sub) as string ?? null
}

export function isAdmin(): boolean {
  const c = getClaims()
  if (!c) return false
  const groups = Array.isArray(c['cognito:groups']) ? (c['cognito:groups'] as string[]) : []
  return c['custom:role'] === 'admin' || groups.includes('admin') || groups.includes('foundry-admins')
}

export function isAuthenticated(): boolean {
  const token = getToken()
  if (!token) return false
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return (payload.exp ?? 0) * 1000 > Date.now()
  } catch {
    return false
  }
}

// ── Auth headers for API calls ────────────────────────────────────────────────

export function authHeaders(): Record<string, string> {
  const t = getAccessToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

// ── Token refresh ─────────────────────────────────────────────────────────────

export async function refreshIdToken(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return null

  const domain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN ?? ''
  const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? ''
  if (!domain || !clientId) return null

  try {
    const body = new URLSearchParams({
      grant_type: 'refresh_token',
      client_id: clientId,
      refresh_token: refreshToken,
    })
    const res = await fetch(`https://${domain}/oauth2/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    })
    if (!res.ok) return null
    const data = await res.json() as { id_token?: string; access_token?: string }
    if (!data.access_token) return null
    if (data.id_token) setToken(data.id_token)
    setAccessToken(data.access_token)
    return data.access_token
  } catch {
    return null
  }
}

// ── Logout ────────────────────────────────────────────────────────────────────

export function logout(): void {
  clearToken()
  document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
  document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'

  const domain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN
  const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? (typeof window !== 'undefined' ? window.location.origin : '')
  if (domain && clientId) {
    const params = new URLSearchParams({ client_id: clientId, logout_uri: `${appUrl}/login` })
    window.location.href = `https://${domain}/logout?${params}`
  } else {
    window.location.href = '/login'
  }
}

// ── Dev token (local dev without Cognito) ─────────────────────────────────────

export function createDevToken(userId: string, name = 'Developer', admin = false): string {
  const header  = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = btoa(JSON.stringify({
    sub: userId,
    name,
    email: `${userId}@amazon.com`,
    'cognito:groups': admin ? ['admin', 'user'] : ['user'],
    'custom:role': admin ? 'admin' : 'user',
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 86400,
  }))
  return `${header}.${payload}.dev`
}

/** Alias kept for any callers that use the old name. */
export const makeDevToken = createDevToken
