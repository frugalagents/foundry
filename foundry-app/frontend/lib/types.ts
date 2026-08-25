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

export interface SessionFeedbackInput {
  rating: number
  most_useful: string
  missing: string
  additional_comments: string
  reused_in_doc_or_meeting?: boolean | null
  agreed_with_recommendation?: boolean | null
  would_reuse?: boolean | null
}

export interface SessionFeedback extends SessionFeedbackInput {
  customer_id: string
  session_id: string
  user_id: string
  user_name: string
  created_at: string
  updated_at: string
}

export interface AdminCountMetric {
  label: string
  value: number
}

export interface AdminRecentActivity {
  customer_id: string
  customer_name: string
  session_id: string
  session_title: string
  created_by: string
  updated_at: string
  status: string
  module_id?: string
  stage: string
}

export interface AdminAnalytics {
  total_customers: number
  total_sessions: number
  unique_users: number
  active_sessions_7d: number
  sessions_with_workspace: number
  sessions_with_architecture: number
  feedback_submissions: number
  average_feedback_score: number
  module_breakdown: AdminCountMetric[]
  stage_breakdown: AdminCountMetric[]
  top_customers: AdminCountMetric[]
  recent_activity: AdminRecentActivity[]
}

export interface AdminFeedbackRow {
  customer: Customer
  session: Session
  feedback: SessionFeedback
}

export type AccessRequestStatus = 'pending' | 'approved' | 'rejected' | 'activated'

export interface AccessRequestCreated {
  request_id: string
  request_secret: string
  status: AccessRequestStatus
  expires_at: string
}

export interface AccessRequestStatusView {
  request_id: string
  email: string
  status: AccessRequestStatus
  requested_at: string
  updated_at: string
  expires_at: string
  decision_note: string
  can_activate: boolean
}

export interface AdminAccessRequest {
  request_id: string
  name: string
  email: string
  reason: string
  status: AccessRequestStatus
  requested_at: string
  updated_at: string
  expires_at: string
  decision_note: string
  reviewed_by: string
  reviewed_at: string
  activated_at: string
}

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
  operating_model?: OperatingModel
  question_state?: WorkspaceQuestion[]
  open_questions: string[]
  decisions: string[]
  risks: string[]
  implementation_plan: string[]
  advisory_case?: AdvisoryCase | null
  architecture_case?: ArchitectureCase | null
  recommendation_state?: WorkspaceRecommendationState | null
  artifact_status?: WorkspaceArtifactStatus | null
  updated_at?: string
}

export type OperatingModel =
  | 'undecided'
  | 'single_standard'
  | 'multi_harness_governed'
  | 'default_plus_exceptions'
  | ''

export interface WorkspaceAssumptionOption {
  id: string
  label: string
  prompt: string
}

export interface ArchitectureCaseFact {
  id: string
  statement: string
  value?: unknown
  status?: string
  source?: string
}

export interface ArchitectureCaseQuestion {
  id: string
  text: string
  why_it_matters?: string
  blocking?: boolean
  decision_domain?: string
  status?: string
  answer?: string
  source?: string
}

export interface ArchitectureCaseDecision {
  id: string
  statement: string
  rationale?: string
  status?: string
  source?: string
  alternatives_considered?: string[]
  evidence_refs?: string[]
  owner?: string
  open_dependency?: string
}

export interface ArchitectureCaseRisk {
  id: string
  risk: string
  mitigation?: string
  severity?: string
  category?: string
  source?: string
}

export interface ArchitectureCaseRolloutItem {
  phase: string
  outcome: string
}

export interface ArchitectureCaseArtifacts {
  blueprint_markdown: string
  executive_summary: string
  recommendation_memo: string
  architecture_narrative: string
  diagram_summary: string
  rollout: ArchitectureCaseRolloutItem[]
}

export interface ArchitectureCase {
  schema_version: string
  case_id: string
  revision: number
  okf_release_id: string
  stage: string
  current_recommendation: string
  operating_model: string
  facts: ArchitectureCaseFact[]
  open_questions: ArchitectureCaseQuestion[]
  decisions: ArchitectureCaseDecision[]
  risks: ArchitectureCaseRisk[]
  artifacts: ArchitectureCaseArtifacts
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


export type WorkspaceQuestionStatus = 'open' | 'answered' | 'deferred' | 'invalidated' | ''

export interface WorkspaceQuestion {
  id: string
  text: string
  why_it_matters: string
  decision_domain?: string
  status: WorkspaceQuestionStatus
  blocking: boolean
  answer?: string
  source?: string
}

export interface WorkspaceCandidateOption {
  path: string
  title: string
  summary: string
  decision_domain?: string
  position: 'recommended' | 'viable' | 'deferred' | ''
}

export interface WorkspaceRecommendationState {
  primary_recommendation: string
  confidence: 'low' | 'medium' | 'high' | ''
  candidate_options: WorkspaceCandidateOption[]
  missing_evidence: string[]
  next_best_question: string
  last_reasoning_change_fields: string[]
}

export type WorkspaceArtifactReadiness = 'missing' | 'draft' | 'ready' | 'stale' | ''

export interface WorkspaceArtifactStatus {
  recommendation: WorkspaceArtifactReadiness
  question_state: WorkspaceArtifactReadiness
  advisory_case: WorkspaceArtifactReadiness
  blueprint: WorkspaceArtifactReadiness
  blocking_question_count: number
  stale_fields: string[]
  reasoning_changes: string[]
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

export interface ArchitectureFlowSegment {
  id: string
  title: string
  narrative: string
  component_ids: string[]
}

export interface ArchitectureOverlayGroup {
  id: string
  title: string
  narrative: string
  component_ids: string[]
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
  primary_flow: ArchitectureFlowSegment[]
  cross_cutting_controls: ArchitectureOverlayGroup[]
  supporting_lanes: ArchitectureOverlayGroup[]
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
  kind?: string
  path_role?: 'primary' | 'overlay' | 'supporting' | ''
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
