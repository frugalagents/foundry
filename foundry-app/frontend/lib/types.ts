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
  advisory_case?: AdvisoryCase | null
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
  impact_level?: 'low' | 'medium' | 'high' | ''
  drives_architecture?: boolean
  validation_priority?: 'now' | 'soon' | 'later' | ''
  options: WorkspaceAssumptionOption[]
}

export interface AdvisoryRecommendation {
  summary: string
  why_this: string
  why_not: string
  confidence: 'low' | 'medium' | 'high' | ''
  confidence_reason: string
  change_triggers: string[]
}

export interface AdvisoryAlternative {
  id: string
  title: string
  position: 'recommended' | 'viable' | 'deferred' | ''
  summary: string
  benefits: string[]
  risks: string[]
  operational_burden: string
  governance_implications: string
  best_fit_conditions: string[]
}

export interface AdvisoryDecision {
  statement: string
  options_considered: string[]
  recommendation: string
  why: string
  tradeoffs_accepted: string[]
  owner: string
  open_dependency: string
}

export interface AdvisoryRisk {
  category: string
  severity: 'low' | 'medium' | 'high' | ''
  risk: string
  mitigation: string
}

export interface AdvisoryMaturityDomain {
  domain: string
  current_state: string
  target_state: string
  gap: string
}

export interface AdvisoryReadout {
  current_recommendation: string
  important_decisions: string[]
  biggest_risks: string[]
  open_questions: string[]
  rollout_summary: string
  architecture_snapshot: string
}

export interface AdvisoryNextBestQuestion {
  question: string
  why_it_matters: string
}

export interface AdvisoryPackRisk {
  risk: string
  mitigation: string
}

export interface AdvisoryPackRolloutPhase {
  horizon: string
  outcome: string
}

export interface AdvisoryOutputPack {
  executive_summary: string
  recommendation_memo: string
  architecture_narrative: string
  key_decisions: string[]
  risks_and_mitigations: AdvisoryPackRisk[]
  open_questions: string[]
  rollout_30_90_180: AdvisoryPackRolloutPhase[]
  operating_principles: string[]
  control_checklist: string[]
}

export interface AdvisoryDelta {
  summary: string
  recommendation_change: string
  new_risks: string[]
  added_controls: string[]
  removed_controls: string[]
  cost_or_complexity_impact: string
  changed_assumptions: string[]
}

export interface AdvisoryCase {
  recommendation: AdvisoryRecommendation
  alternatives: AdvisoryAlternative[]
  decisions: AdvisoryDecision[]
  risks: AdvisoryRisk[]
  maturity: AdvisoryMaturityDomain[]
  readout: AdvisoryReadout
  next_best_question?: AdvisoryNextBestQuestion | null
  output_pack: AdvisoryOutputPack
  delta?: AdvisoryDelta | null
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
