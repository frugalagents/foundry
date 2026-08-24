'use client'

const COGNITO_DOMAIN = process.env.NEXT_PUBLIC_COGNITO_DOMAIN ?? ''
const COGNITO_CLIENT_ID = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID ?? ''
const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? ''
const GUEST_GROUP_NAME = process.env.NEXT_PUBLIC_GUEST_GROUP_NAME ?? 'foundry-guests'
const GUEST_ACCESS_EXPIRES_AT = process.env.NEXT_PUBLIC_GUEST_ACCESS_EXPIRES_AT ?? ''

export type LoginMode = 'internal' | 'guest'
type IdentityProvider = 'COGNITO' | 'Midway'

function callbackUrl() {
  if (APP_URL) return `${APP_URL}/callback`
  if (typeof window !== 'undefined') return `${window.location.origin}/callback`
  return ''
}

function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split('.')[1]
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(normalized.length + ((4 - normalized.length % 4) % 4), '=')
    return JSON.parse(atob(padded)) as Record<string, unknown>
  } catch {
    return null
  }
}

function parseGuestAccessExpiry(): number | null {
  if (!GUEST_ACCESS_EXPIRES_AT.trim()) return null
  const value = Date.parse(GUEST_ACCESS_EXPIRES_AT)
  return Number.isNaN(value) ? null : value
}

function groupsFromClaims(claims: Record<string, unknown> | null): string[] {
  if (!claims) return []
  const groups = claims['cognito:groups'] ?? claims.groups
  if (Array.isArray(groups)) return groups.filter((value): value is string => typeof value === 'string')
  if (typeof groups === 'string') return [groups]
  return []
}

async function generatePKCE(): Promise<{ verifier: string; challenge: string }> {
  const array = new Uint8Array(32)
  crypto.getRandomValues(array)
  const verifier = btoa(String.fromCharCode(...array))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')

  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))
  const challenge = btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')

  return { verifier, challenge }
}

async function redirectToHostedUi(identityProvider?: IdentityProvider) {
  if (typeof window === 'undefined') return
  const { verifier, challenge } = await generatePKCE()
  sessionStorage.setItem('pkce_verifier', verifier)

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: COGNITO_CLIENT_ID,
    redirect_uri: callbackUrl(),
    scope: 'openid email profile',
    code_challenge: challenge,
    code_challenge_method: 'S256',
  })
  if (identityProvider) params.set('identity_provider', identityProvider)
  window.location.href = `https://${COGNITO_DOMAIN}/oauth2/authorize?${params}`
}

// ── Token storage ────────────────────────────────────────────────────────────

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

export function navigateToHome(): void {
  if (typeof window === 'undefined') return
  window.location.replace('/')
}

export function navigateToLogin(mode: LoginMode): void {
  if (typeof window === 'undefined') return
  const suffix = mode === 'guest' ? '/login/?mode=guest' : '/login/'
  window.location.replace(suffix)
}

export function guestAccessExpiresAt(): string {
  return GUEST_ACCESS_EXPIRES_AT
}

export function isGuestAccessOpen(): boolean {
  const cutoff = parseGuestAccessExpiry()
  return cutoff === null || Date.now() < cutoff
}

export function isGuestAccessExpired(): boolean {
  return !isGuestAccessOpen()
}

export async function startInternalLogin(): Promise<void> {
  if (!COGNITO_DOMAIN || !COGNITO_CLIENT_ID || process.env.NODE_ENV === 'development') {
    navigateToLogin('internal')
    return
  }
  await redirectToHostedUi('Midway')
}

export async function startGuestLogin(): Promise<void> {
  if (!isGuestAccessOpen()) {
    navigateToLogin('guest')
    return
  }
  if (!COGNITO_DOMAIN || !COGNITO_CLIENT_ID || process.env.NODE_ENV === 'development') {
    navigateToLogin('guest')
    return
  }
  await redirectToHostedUi('COGNITO')
}

export function getAccessToken(): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(/(?:^|; )access_token=([^;]*)/)
  if (match) return decodeURIComponent(match[1])
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
  const expires = new Date(Date.now() + 30 * 24 * 3600 * 1000).toUTCString()
  document.cookie = `refresh_token=${encodeURIComponent(token)}; expires=${expires}; path=/; SameSite=Strict`
}

// ── Token decoding ───────────────────────────────────────────────────────────

export function getClaims(): Record<string, unknown> | null {
  const token = getToken()
  if (!token) return null
  return parseJwtPayload(token)
}

export function getUserId(): string | null {
  return (getClaims()?.sub as string) ?? null
}

export function getUserName(): string | null {
  const c = getClaims()
  return (c?.name ?? c?.email ?? c?.sub) as string ?? null
}

export function isGuestUser(): boolean {
  return groupsFromClaims(getClaims()).includes(GUEST_GROUP_NAME)
}

export function isAdmin(): boolean {
  const c = getClaims()
  if (!c) return false
  const groups = groupsFromClaims(c)
  return c['custom:role'] === 'admin' || groups.includes('admin') || groups.includes('foundry-admins')
}

export function isMidwayIdentity(): boolean {
  const c = getClaims()
  if (!c) return false
  const alias = String(c['custom:amazon_alias'] ?? '').trim()
  const username = String(c['cognito:username'] ?? '')
  return alias.length > 0 || username.startsWith('Midway_')
}

export function isAuthenticated(): boolean {
  const token = getToken()
  if (!token) return false
  const payload = parseJwtPayload(token)
  if (!payload) return false
  if (((payload.exp ?? 0) as number) * 1000 <= Date.now()) return false
  if (groupsFromClaims(payload).includes(GUEST_GROUP_NAME) && isGuestAccessExpired()) return false
  return true
}

// ── Auth headers ─────────────────────────────────────────────────────────────

export function authHeaders(): Record<string, string> {
  const t = getAccessToken() ?? getToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

// ── Token refresh ────────────────────────────────────────────────────────────

export async function refreshIdToken(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return null
  if (!COGNITO_DOMAIN || !COGNITO_CLIENT_ID) return null

  try {
    const body = new URLSearchParams({
      grant_type: 'refresh_token',
      client_id: COGNITO_CLIENT_ID,
      refresh_token: refreshToken,
    })
    const res = await fetch(`https://${COGNITO_DOMAIN}/oauth2/token`, {
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

// ── Logout ───────────────────────────────────────────────────────────────────

export function logout(): void {
  const guest = isGuestUser()
  clearToken()
  document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
  document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'

  if (COGNITO_DOMAIN && COGNITO_CLIENT_ID) {
    const params = new URLSearchParams({
      client_id: COGNITO_CLIENT_ID,
      logout_uri: `${APP_URL || (typeof window !== 'undefined' ? window.location.origin : '')}/login${guest ? '/?mode=guest' : ''}`,
    })
    window.location.href = `https://${COGNITO_DOMAIN}/logout?${params}`
  } else {
    navigateToLogin(guest ? 'guest' : 'internal')
  }
}

// ── Dev token ────────────────────────────────────────────────────────────────

export function createDevToken(userId: string, name = 'Developer', admin = false): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
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

