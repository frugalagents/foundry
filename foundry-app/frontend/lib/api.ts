import { authHeaders, getUserId, refreshIdToken } from './auth'
import type { Customer, Session, SessionCreate, SessionHistory, Module } from './types'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  path: string
  detail?: string

  constructor(status: number, path: string, body: string) {
    let detail: string | undefined
    try {
      const parsed = JSON.parse(body) as { detail?: unknown; message?: unknown }
      if (typeof parsed.detail === 'string') detail = parsed.detail
      else if (typeof parsed.message === 'string') detail = parsed.message
    } catch {
      if (body.trim()) detail = body.trim()
    }

    super(`${status} ${path}${detail ? `: ${detail}` : ''}`)
    this.name = 'ApiError'
    this.status = status
    this.path = path
    this.detail = detail
  }
}

async function fetchWithAuthRetry(path: string, init?: RequestInit) {
  const request = () => fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...init?.headers,
    },
  })

  let response = await request()
  if (response.status === 401 && await refreshIdToken()) {
    response = await request()
  }
  return response
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetchWithAuthRetry(path, init)
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new ApiError(res.status, path, body)
  }

  if (res.status === 204) {
    return undefined as T
  }

  const body = await res.text()
  if (!body.trim()) {
    return undefined as T
  }

  const contentType = res.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) {
    return JSON.parse(body) as T
  }

  return body as T
}

export async function streamSession(
  customerId: string,
  sessionId: string,
  message: string,
  signal?: AbortSignal,
): Promise<ReadableStream<Uint8Array>> {
  const path = `/api/v1/customers/${customerId}/sessions/${sessionId}/stream`
  const res = await fetchWithAuthRetry(path, {
    method: 'POST',
    body: JSON.stringify({ message }),
    signal,
  })

  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new ApiError(res.status, path, body)
  }

  if (!res.body) {
    throw new Error('Streaming response body was empty')
  }

  return res.body
}

// ── Customers ─────────────────────────────────────────────────────────────────

export const listCustomers = () =>
  call<Customer[]>('/api/v1/customers')

export const createCustomer = (name: string) =>
  call<Customer>('/api/v1/customers', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })

export const getCustomer = (customerId: string) =>
  call<Customer>(`/api/v1/customers/${customerId}`)

export const deleteCustomer = (customerId: string) =>
  call<void>(`/api/v1/customers/${customerId}`, { method: 'DELETE' })

// ── Sessions ──────────────────────────────────────────────────────────────────

export const listSessions = (customerId: string) =>
  call<Session[]>(`/api/v1/customers/${customerId}/sessions`)

export const createSession = (customerId: string, body: SessionCreate) =>
  call<Session>(`/api/v1/customers/${customerId}/sessions`, {
    method: 'POST',
    body: JSON.stringify(body),
  })

export const getSession = (customerId: string, sessionId: string) =>
  call<Session>(`/api/v1/customers/${customerId}/sessions/${sessionId}`)

export const updateSession = (customerId: string, sessionId: string, body: Partial<Session>) =>
  call<Session>(`/api/v1/customers/${customerId}/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })

export const deleteSession = (customerId: string, sessionId: string) =>
  call<void>(`/api/v1/customers/${customerId}/sessions/${sessionId}`, { method: 'DELETE' })

export const getSessionHistory = (customerId: string, sessionId: string) =>
  call<SessionHistory>(`/api/v1/customers/${customerId}/sessions/${sessionId}/history`)

// ── Modules ───────────────────────────────────────────────────────────────────

export const listModules = () =>
  call<Module[]>('/api/v1/modules')

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Load every session across all of the user's customers, sorted by updated_at desc. */
export async function listAllSessions() {
  const customers = await listCustomers()
  const rows = await Promise.all(
    customers.map(async (c) => {
      try {
        const sessions = await listSessions(c.customer_id)
        return sessions.map((s) => ({ session: s, customer: c }))
      } catch {
        return []
      }
    }),
  )
  return rows
    .flat()
    .sort((a, b) => +new Date(b.session.updated_at) - +new Date(a.session.updated_at))
}

function looksLikeSyntheticCustomer(customer: Customer) {
  const name = customer.name.trim().toLowerCase()
  return (
    customer.demo_data === true ||
    /^simulation-\d+$/.test(name) ||
    /^demo(?:\b|[-\s_])/.test(name)
  )
}

/** Get or create a default workspace customer for the current user. */
export async function getOrCreateDefaultCustomer(): Promise<Customer> {
  const actorId = getUserId()
  const customers = (await listCustomers()).sort(
    (a, b) => +new Date(b.updated_at) - +new Date(a.updated_at),
  )
  const ownedCustomers = actorId
    ? customers.filter((customer) => customer.created_by === actorId)
    : []
  const preferred = ownedCustomers.find((customer) => !looksLikeSyntheticCustomer(customer))
    ?? ownedCustomers[0]
  if (preferred) return preferred
  return createCustomer('My Workspace')
}
