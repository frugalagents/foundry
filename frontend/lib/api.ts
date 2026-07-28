import { getAccessToken, refreshIdToken } from './auth';
import type {
  Customer,
  Session,
  IntakeAnswers,
  AdminMetrics,
  SkillConfig,
  MCPServerStatus,
  SystemPrompt,
} from './types';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080/api/v1';

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  _retry = true,
): Promise<T> {
  const token = getAccessToken();
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (res.status === 401 && _retry) {
    // Try a silent token refresh, then retry the request once
    const newToken = await refreshIdToken();
    if (newToken) {
      return apiFetch<T>(path, options, false);
    }
    // Refresh failed — redirect to login
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    throw new Error('Session expired. Redirecting to login…');
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Customers ──────────────────────────────────────────────

export const listCustomers = () =>
  apiFetch<Customer[]>('/customers');

export const createCustomer = (data: {
  name: string;
  industry: string;
  contact_email?: string;
  notes?: string;
  metadata?: Partial<{ region: string; company_size: string; notes: string }>;
}) => apiFetch<Customer>('/customers', { method: 'POST', body: JSON.stringify(data) });

export const getCustomer = (id: string) =>
  apiFetch<Customer>(`/customers/${id}`);

export const updateCustomer = (id: string, data: Partial<Customer>) =>
  apiFetch<Customer>(`/customers/${id}`, { method: 'PATCH', body: JSON.stringify(data) });

export const deleteCustomer = (id: string) =>
  apiFetch<void>(`/customers/${id}`, { method: 'DELETE' });

// ── Sessions ───────────────────────────────────────────────

export const listSessions = (customerId: string) =>
  apiFetch<Session[]>(`/customers/${customerId}/sessions`);

export const createSession = (customerId: string, title?: string) =>
  apiFetch<Session>(`/customers/${customerId}/sessions`, {
    method: 'POST',
    body: JSON.stringify({ title: title ?? `Session ${new Date().toLocaleDateString()}` }),
  });

export const getSession = (customerId: string, sessionId: string) =>
  apiFetch<Session>(`/customers/${customerId}/sessions/${sessionId}`);

export const updateSession = (
  customerId: string,
  sessionId: string,
  data: { title?: string; status?: string; notes?: string }
) =>
  apiFetch<Session>(`/customers/${customerId}/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });

export const deleteSession = (customerId: string, sessionId: string) =>
  apiFetch<void>(`/customers/${customerId}/sessions/${sessionId}`, { method: 'DELETE' });

export const getPanelStates = (customerId: string, sessionId: string) =>
  apiFetch<{ panels: unknown[] }>(`/customers/${customerId}/sessions/${sessionId}/panels`);

export const updateIntakeAnswers = (
  customerId: string,
  sessionId: string,
  answers: Partial<IntakeAnswers>
) =>
  apiFetch<void>(`/customers/${customerId}/sessions/${sessionId}/inputs`, {
    method: 'PUT',
    body: JSON.stringify({ answers }),
  });

export const exportBlueprint = (
  customerId: string,
  sessionId: string,
  format: 'pdf' | 'pptx'
) =>
  apiFetch<{ url: string }>(`/customers/${customerId}/sessions/${sessionId}/export`, {
    method: 'POST',
    body: JSON.stringify({ format }),
  });

export const sendConfirmation = (
  customerId: string,
  sessionId: string,
  choice: string
) =>
  apiFetch<{ ok: boolean }>(`/sessions/${customerId}/${sessionId}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ choice }),
  });

export const sendMessage = (
  customerId: string,
  sessionId: string,
  content: string
) =>
  apiFetch<{ ok: boolean }>(`/sessions/${customerId}/${sessionId}/message`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });

// ── Admin ──────────────────────────────────────────────────

export const getAdminMetrics = () =>
  apiFetch<AdminMetrics>('/admin/metrics');

/** Alias used by admin dashboard page */
export const fetchAdminMetrics = getAdminMetrics;

export const fetchGraphStats = () =>
  apiFetch<{
    total_nodes: number;
    total_edges: number;
    node_types: Record<string, number>;
    edge_types: Record<string, number>;
  }>('/admin/graph/stats');

export const reloadGraph = () =>
  apiFetch<{ ok: boolean; nodes: number; edges: number }>('/admin/graph/reload', {
    method: 'POST',
  });

export const getSystemPrompts = () =>
  apiFetch<SystemPrompt[]>('/admin/config/prompts');

export const saveSystemPrompt = (content: string) =>
  apiFetch<SystemPrompt>('/admin/config/prompts', {
    method: 'POST',
    body: JSON.stringify({ content }),
  });

export const getSkills = () =>
  apiFetch<SkillConfig[]>('/admin/config/skills');

export const updateSkill = (name: string, data: Partial<SkillConfig>) =>
  apiFetch<SkillConfig>(`/admin/config/skills/${name}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });

export const getMCPStatus = () =>
  apiFetch<MCPServerStatus[]>('/admin/config/mcp-status');

/** Build the SSE URL for a session (token passed as query param) */
export const buildStreamUrl = (
  customerId: string,
  sessionId: string,
  token: string,
  answers: Record<string, unknown> = {},
  industry = '',
  painPoints: string[] = []
): string => {
  const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080/api/v1';
  const params = new URLSearchParams({
    token,
    answers: JSON.stringify(answers),
    industry,
    pain_points: painPoints.join(','),
  });
  return `${base}/sessions/${customerId}/${sessionId}/run?${params.toString()}`;
};
