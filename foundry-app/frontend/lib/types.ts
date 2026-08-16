// ── Auth ──────────────────────────────────────────────────────────────────────

export interface TokenClaims {
  sub: string
  email?: string
  name?: string
  'custom:role'?: string
  groups?: string[]
  exp: number
}

// ── Platform modules ──────────────────────────────────────────────────────────

export interface Module {
  id: string               // "coding-agent" | "product-platform" | "fabric"
  name: string             // display name
  description: string
  icon: string             // lucide icon name
  color: string            // hex
}

// ── Backend domain ────────────────────────────────────────────────────────────

export interface Customer {
  customer_id: string
  name: string
  created_by: string
  created_at: string
  updated_at: string
  demo_data?: boolean
}

export interface Session {
  session_id: string
  customer_id: string
  module_id?: string
  title: string
  description?: string
  status: 'active' | 'complete'
  current_step: number
  recommendation?: string
  evidence_state?: string
  created_by: string
  created_at: string
  updated_at: string
}

export interface SessionCreate {
  title?: string
  description?: string
  module_id?: string
}

// ── UI ────────────────────────────────────────────────────────────────────────

export interface Message {
  id: string
  role: 'user' | 'agent'
  content: string
  streaming?: boolean
}

// Sidebar item (session + customer joined)
export interface ConversationRow {
  session: Session
  customer: Customer
}

// ── SSE event payloads ────────────────────────────────────────────────────────

export interface ChatStreamEvent {
  type: 'chat_stream'
  data: { text: string }
}

export interface ArchitectureUpdateEvent {
  type: 'architecture_update'
  data: {
    stage: string
    nodes: ArchNode[]
    edges: ArchEdge[]
  }
}

export interface ModuleDetectedEvent {
  type: 'module_detected'
  data: { module: string }
}

export type SSEEvent =
  | ChatStreamEvent
  | ArchitectureUpdateEvent
  | ModuleDetectedEvent
  | { type: string; data: unknown }

// ── Architecture canvas ───────────────────────────────────────────────────────

export interface ArchNode {
  id: string
  type: 'arch' | 'zone'
  label: string
  sublabel?: string
  icon?: string
  color: string
  x: number
  y: number
  width?: number
  height?: number
}

export interface ArchEdge {
  id: string
  source: string
  target: string
  animated?: boolean
  color?: string
  dashed?: boolean
}
