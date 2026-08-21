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

// ── History (persisted messages + canvas, GET /sessions/{id}/history) ────────

export interface MessageOut {
  role: 'user' | 'agent'
  content: string
  created_at: string
}

export interface CanvasOut {
  nodes: ArchNode[]
  edges: ArchEdge[]
  stage: string
  baseline_node_ids?: string[]
  architecture_artifact?: ArchitectureArtifact | null
  updated_at?: string
}

export interface SessionHistory {
  messages: MessageOut[]
  canvas?: CanvasOut | null
  workspace?: ConsultingWorkspace | null
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
    baseline_node_ids?: string[]
    architecture_artifact?: ArchitectureArtifact | null
  }
}

export interface ModuleDetectedEvent {
  type: 'module_detected'
  data: { module: string }
}

export interface WorkspaceUpdateEvent {
  type: 'workspace_update'
  data: ConsultingWorkspace
}

export type SSEEvent =
  | ChatStreamEvent
  | ArchitectureUpdateEvent
  | ModuleDetectedEvent
  | WorkspaceUpdateEvent
  | { type: string; data: unknown }

// ── Consulting workspace ──────────────────────────────────────────────────────

export interface ConsultingWorkspace {
  stage?: string
  recommendation: string
  blueprint_markdown?: string
  assumptions?: WorkspaceAssumption[]
  facts: string[]
  open_questions: string[]
  decisions: string[]
  risks: string[]
  implementation_plan: string[]
  updated_at?: string
}

export interface WorkspaceAssumptionOption {
  id: string
  label: string
  prompt: string
}

export interface WorkspaceAssumption {
  id: string
  title: string
  assumed: string
  why: string
  impact: string
  confidence: 'default' | 'inferred' | 'confirmed'
  options: WorkspaceAssumptionOption[]
}

export interface ArchitectureLayerSummary {
  id: string
  label: string
  purpose: string
  component_ids: string[]
  component_labels: string[]
}

export interface ArchitectureCustomization {
  id: string
  title: string
  layer: string
  added_component_ids: string[]
  reason: string
  tradeoff: string
  triggered_by: string[]
}

export interface ArchitectureDecisionRationale {
  decision: string
  why: string
  alternatives_rejected?: string[]
}

export interface ArchitectureRiskItem {
  risk: string
  mitigation: string
}

export interface ArchitectureRolloutPhase {
  phase: string
  outcome: string
}

export interface ArchitectureArtifact {
  executive_summary: string
  baseline: {
    name: string
    layers: ArchitectureLayerSummary[]
  }
  customizations: ArchitectureCustomization[]
  decisions: ArchitectureDecisionRationale[]
  risks: ArchitectureRiskItem[]
  rollout: ArchitectureRolloutPhase[]
}

// ── Architecture canvas ───────────────────────────────────────────────────────

export type NodeComment = {
  initials: string
  author: string
  text: string
}

export type ArchLayer = 'surface' | 'harness' | 'execution' | 'gateway' | 'model' | 'ops' | 'access'

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
  cost?: string
  size?: string
  layer?: ArchLayer
  comments?: NodeComment[]
}

export interface ArchEdge {
  id: string
  source: string
  target: string
  animated?: boolean
  color?: string
  dashed?: boolean
}

export interface ArchDraft {
  id: string
  name: string
  costLabel: string
  nodes: ArchNode[]
  edges: ArchEdge[]
}
