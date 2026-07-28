// ============================================================
// A2UI Event Types — agent → frontend streaming protocol
// ============================================================

export type PanelType =
  | 'intake_form'
  | 'decision_summary'
  | 'radar_chart'
  | 'architecture_diagram'
  | 'requirements'
  | 'innovation_overlay'
  | 'service_map'
  | 'risk_cards'
  | 'timeline'
  | 'cost_estimate'
  | 'blueprint';

export interface BaseEvent {
  event_id: string;
  timestamp: string;
  session_id: string;
}

export interface PanelUpdateEvent extends BaseEvent {
  type: 'panel_update';
  step: number;
  panel_type: PanelType;
  data: Record<string, unknown>;
  streaming: true;
  progress: number;
}

export interface PanelCompleteEvent extends BaseEvent {
  type: 'panel_complete';
  step: number;
  panel_type: PanelType;
  data: Record<string, unknown>;
  streaming: false;
}

export interface CardAddEvent extends BaseEvent {
  type: 'card_add';
  step: number;
  panel_type: PanelType;
  card_id: string;
  card_data: Record<string, unknown>;
  position: number;
}

export interface CardUpdateEvent extends BaseEvent {
  type: 'card_update';
  step: number;
  panel_type: PanelType;
  card_id: string;
  updates: Record<string, unknown>;
}

export interface ChatMessageEvent extends BaseEvent {
  type: 'chat_message';
  role: 'assistant';
  content: string;
  step: number;
}

export interface ChatStreamEvent extends BaseEvent {
  type: 'chat_stream';
  role: 'assistant';
  delta: string;
  step: number;
}

export interface StepTransitionEvent extends BaseEvent {
  type: 'step_transition';
  from_step: number;
  to_step: number;
  status: 'auto' | 'awaiting_confirmation' | 'error';
}

export interface ConfirmationRequestEvent extends BaseEvent {
  type: 'confirmation_request';
  step: number;
  question: string;
  options: string[];
}

export interface AgentErrorEvent extends BaseEvent {
  type: 'error';
  step: number;
  message: string;
  recoverable: boolean;
  suggestion: string;
}

export interface CompleteEvent extends BaseEvent {
  type: 'complete';
  total_steps_completed: number;
}

export type AgentEvent =
  | PanelUpdateEvent
  | PanelCompleteEvent
  | CardAddEvent
  | CardUpdateEvent
  | ChatMessageEvent
  | ChatStreamEvent
  | StepTransitionEvent
  | ConfirmationRequestEvent
  | AgentErrorEvent
  | CompleteEvent;

// ============================================================
// Domain Models
// ============================================================

export interface Customer {
  customer_id: string;
  name: string;
  industry: string;
  owner_user_id: string;
  shared_with: string[];
  metadata: { company_size: string; region: string; notes: string };
  created_at: string;
  updated_at: string;
  session_count: number;
}

export type SessionStatus =
  | 'active'
  | 'intake'
  | 'scoring'
  | 'components'
  | 'innovation'
  | 'services'
  | 'antipatterns'
  | 'phasing'
  | 'blueprint'
  | 'complete';

export type EvidenceState =
  | 'not_started'
  | 'provisional'
  | 'decision_ready'
  | 'overridden';

export interface Session {
  session_id: string;
  customer_id: string;
  title: string;
  description: string;
  status: SessionStatus;
  current_step: number;
  intake_answers?: Record<string, unknown>;
  primary_workload?: string | null;
  recommendation?: string | null;
  evidence_state: EvidenceState;
  created_by: string;
  created_at: string;
  updated_at: string;

  // Legacy fields remain optional while existing records are migrated.
  name?: string;
  notes?: string;
  user_id?: string;
  pattern_selected?: string | null;
  pattern_scores?: Record<string, number> | null;
  graph_version?: string;
}

// 'not_sure' is a valid, present value that contributes ZERO scoring pressure
// (the engine matches no constraint for it) and is surfaced as an assumption.
type NotSure = 'not_sure';

export interface IntakeAnswers {
  // Q0 — archetype (question filter, not scored)
  archetype?:
    | 'coding'
    | 'internal_copilot'
    | 'hosting_platform'
    | 'customer_facing'
    | 'process_automation'
    | 'marketplace';
  autonomy_model?: 'full' | 'hitl' | 'supervised' | NotSure;
  team_expertise?: 'high' | 'medium' | 'low' | NotSure;
  cloud_posture?: 'single_aws' | 'aws_primary' | 'multi_cloud' | NotSure;
  stack_preference?: 'open_source' | 'managed' | 'hybrid';
  lob_count?: '1-3' | '4-10' | '10+' | NotSure;
  governance_model?: 'centralized' | 'federated' | 'undecided';
  auth_identity?: 'oauth_oidc' | 'iam_heavy' | 'greenfield' | 'complex_multi';
  observability?: 'existing_stack' | 'greenfield';
  intake_maturity?: 'mature' | 'emerging' | 'greenfield';
  agent_purpose?: 'internal' | 'customer_facing' | 'both';
  cost_sensitivity?: 'primary' | 'secondary' | 'optimize_later' | NotSure;
  data_gravity?: 'single_region' | 'multi_region' | 'on_prem_cloud' | 'edge' | NotSure;
  compliance_regime?: string[]; // multi-select: sox, pci_dss, hipaa, fedramp, gdpr, eu_ai_act, none
  // Stage-3 branch answer used by topology derivation (axis C)
  tenancy_model?: 'shared_rbac' | 'namespace' | 'account' | 'tiered';
  industry?: string;
  pain_points?: string[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  step?: number;
  streaming?: boolean;
}

// ============================================================
// Panel Data Types
// ============================================================

export interface IntakeFormData {
  answers: Record<string, unknown>;
  missing: string[];
  complete: boolean;
  streaming: boolean;
  schema_version?: string;
  status?: string;
}

export interface DecisionSummaryData {
  status: 'needs_information' | 'complete' | 'overridden';
  evidence_coverage: number;
  missing_evidence: { field: string; reason: string; critical: boolean; question_id?: string }[];
  operating_model: string | null;
  ownership_matrix: { capability: string; owner: string; evidence: string[] }[];
  topology: {
    control_plane: string;
    runtime_placement: string;
    isolation_boundary: string;
    regional_model: string;
    modifiers: string[];
  } | null;
  trace: { decision: string; rule_id: string; evidence: string[]; outcome: string }[];
  overrides: Record<string, unknown>[];
}

export interface RequirementsData {
  requirements: {
    id: string;
    category: string;
    statement: string;
    evidence: string[];
    hard: boolean;
  }[];
  assumptions: string[];
}

export interface RadarPatternScore {
  name: string;
  scores: number[];
  color: string;
  total: number;
  selected: boolean;
}

export interface ScoringSignal {
  signal: string;
  value: string;
  contribution: number;
  direction: 'positive' | 'negative';
  steers_toward?: string;
  reason?: string;
}

export interface FollowUpQuestion {
  id: string;
  question: string;
  options: string[];
}

export interface RadarChartData {
  axes: string[];
  patterns: RadarPatternScore[];
  recommended_pattern?: string;
  pattern_name?: string;
  confidence: number;
  signals?: ScoringSignal[];
  runner_up?: { pattern_id: string; pattern_name: string; total: number } | null;
  follow_up_questions?: FollowUpQuestion[];
  topology?: { base: string; modifiers: string[]; label: string; rationale: string };
  streaming: boolean;
}

// ============================================================
// What-If (P4)
// ============================================================

export interface WhatIfData {
  original_pattern_id: string;
  original_pattern_name: string;
  original_confidence: number;
  whatif_pattern_id: string;
  whatif_pattern_name: string;
  whatif_confidence: number;
  pattern_changed: boolean;
  confidence_delta: number;
  overrides: Record<string, string>;
  patterns: RadarPatternScore[];
  axes: string[];
  signals: ScoringSignal[];
  runner_up: { pattern_id: string; pattern_name: string; total: number } | null;
}

export interface WhatIfCompleteEvent {
  type: 'whatif_complete';
  data: WhatIfData;
}

export interface ArchitectureComponent {
  id?: string;
  name: string;
  base_tier: number;
  final_tier: number;
  elevation_reason: string | null;
  category: string;
  layer?: string;
  aws_service?: string;
  elevated?: boolean;
  scope?: 'per_lob' | 'shared_spine';
}

export interface ArchitectureLayer {
  name: string;
  components: ArchitectureComponent[];
}

export interface ArchitectureDiagramData {
  layers: ArchitectureLayer[];
  pattern: string;
  pattern_id?: string;
  pattern_name?: string;
  pattern_rationale?: string;
  streaming: boolean;
}

export interface Innovation {
  id?: string;
  name: string;
  date_emerged: string;
  constraint_solved: string;
  replaces: string | null;
  enables: string | null;
  aws_implementation: string;
  status: 'ga' | 'preview' | 'emerging';
  verified_via_mcp: boolean;
  enabled?: boolean;
}

export interface InnovationOverlayData {
  innovations: Innovation[];
  before_architecture: ArchitectureDiagramData;
  after_architecture: ArchitectureDiagramData;
  streaming: boolean;
}

export interface ServiceComponent {
  name: string;
  tier: number;
  aws_services: { name: string; icon_url: string; notes: string }[];
  workshops: { title: string; url: string }[];
  alternatives: { name: string; when: string }[];
}

export interface ServiceMapData {
  components: ServiceComponent[];
  streaming: boolean;
}

export interface Risk {
  name: string;
  severity: 'high' | 'medium' | 'low';
  trigger_condition: string;
  status: 'prevented' | 'warning' | 'blocked';
  prevented_by: string | null;
  recommended_fix: string | null;
}

export interface RiskCardsData {
  summary: { total_detected: number; addressed: number; requires_attention: number };
  risks: Risk[];
  streaming: boolean;
}

export interface PhaseComponent {
  name: string;
  tier: number;
  aws_service: string;
  effort: 'low' | 'medium' | 'high';
  dependencies: string[];
}

export interface Phase {
  id: string;
  name: string;
  duration: string;
  components: PhaseComponent[];
}

export interface PhaseTimelineData {
  phases: Phase[];
  dependencies: { from: string; to: string; reason: string }[];
  streaming: boolean;
}

export interface CostLineItem {
  id: string;
  name: string;
  layer: string;
  tier: number;
  monthly_usd: number;
  monthly_fmt: string;
  aws_service: string;
  cost_drivers: string;
  unit: string;
  weeks_min: number;
  weeks_max: number;
  team_size: number;
  role_mix: string;
  complexity: 'low' | 'medium' | 'high';
  cdk_construct: string;
  workshop_hint: string;
  engagement_pattern: string;
}

export interface PhaseTimeline {
  phase_id: string;
  duration_label: string;
  weeks: number;
  components: string[];
}

export interface CostEstimateData {
  agent_count_assumed: number;
  line_items: CostLineItem[];
  subtotal_platform_monthly: number;
  compliance_uplift_usd: number;
  compliance_uplift_pct: number;
  compliance_note: string;
  total_monthly_usd: number;
  total_annual_usd: number;
  total_monthly_fmt: string;
  total_annual_fmt: string;
  llm_cost_unoptimized_monthly: number;
  llm_cost_optimized_monthly: number;
  llm_savings_monthly: number;
  llm_savings_annual: number;
  has_cost_engine: boolean;
  phase_timeline_weeks: PhaseTimeline[];
  total_team_weeks: number;
}

export interface CostEstimateV2 {
  currency: 'USD';
  price_catalog_date: string;
  low: { monthly_usd: number; annual_usd: number };
  base: { monthly_usd: number; annual_usd: number };
  high: { monthly_usd: number; annual_usd: number };
  assumptions: string[];
  line_items: {
    id: string;
    name: string;
    monthly_base_usd: number;
    scope: string;
    aws_services: string[];
  }[];
}

export interface BlueprintData {
  // Flat structure emitted by blueprint_skill.py panel_complete
  pattern_id: string;
  pattern_name: string;
  confidence?: number;       // v1 only
  evidence_coverage?: number;
  markdown: string;          // LLM-generated executive blueprint text
  components_count: number;
  phases_count: number;
  services_count: number;
  antipatterns_count: number;
  innovations_count: number;
  industry: string;
  compliance_regime: string;
  export_ready: boolean;
  cost_estimate?: CostEstimateData | null;
}

// ============================================================
// Auth
// ============================================================

export interface UserTokenPayload {
  sub: string;
  email: string;
  'cognito:groups': string[];
  'custom:role'?: 'admin' | 'user';
  'custom:amazon_alias'?: string;
  'custom:display_name'?: string;
  iat: number;
  exp: number;
}

// ============================================================
// Admin
// ============================================================

export interface AdminMetrics {
  total_customers: number;
  total_sessions: number;
  completed_blueprints: number;
  completion_rate: number;
  pattern_distribution: Record<string, number>;
  top_constraints: { name: string; count: number }[];
  innovation_hit_rate: { name: string; count: number }[];
  sessions_per_week: { week: string; count: number }[];
  recent_sessions: {
    customer_name: string;
    user_email: string;
    pattern: string;
    step: number;
    date: string;
  }[];
}

export interface EngineQuestion {
  id: string;
  path: string;
  prompt: string;
  type: string;
  unit: string | null;
  critical: boolean;
  consumers: string[];
}

export interface EngineBranch {
  workload: string;
  label: string;
  question_count: number;
  critical_count: number;
  questions: EngineQuestion[];
}

export interface EngineComponent {
  id: string;
  name: string;
  layer: string;
  activation: string;
  dependencies: string[];
  aws_services: string[];
  monthly_planning_base_usd: number;
}

export interface EngineManifest {
  engine: {
    name: string;
    schema_version: string;
    questionnaire_version: string;
    methodology_version: string;
    catalog_version: string;
    price_catalog_date: string;
    execution_model: string;
    llm_decision_authority: boolean;
  };
  summary: {
    workloads: number;
    universal_questions: number;
    branch_questions: number;
    components: number;
    regulatory_controls: number;
  };
  pipeline: {
    id: string;
    label: string;
    description: string;
    outputs: string[];
  }[];
  questionnaire: {
    universal: EngineQuestion[];
    branches: EngineBranch[];
  };
  catalog: {
    components: EngineComponent[];
    controls: {
      regime: string;
      control_count: number;
      controls: {
        id: string;
        name: string;
        implementation: string;
      }[];
    }[];
  };
  checks: {
    id: string;
    label: string;
    ok: boolean;
  }[];
}

export interface SkillConfig {
  name: string;
  step: string;
  enabled: boolean;
  params: Record<string, unknown>;
}

export interface MCPServerStatus {
  name: string;
  status: 'connected' | 'degraded' | 'down';
  latency_ms: number | null;
  last_checked: string;
}

export interface SystemPrompt {
  version: number;
  content: string;
  status: 'published' | 'draft';
  created_at: string;
}

// ============================================================
// Drilldown (P1 Depth on Demand)
// ============================================================

export interface DrilldownTierOption {
  tier: number;
  label: string;
  description: string;
  monthly_usd: number;
  monthly_fmt: string;
  effort: 'low' | 'medium' | 'high';
  weeks_range: string;
  is_current: boolean;
}

export interface DrilldownData {
  component_id: string;
  component_name: string;
  tier: number;
  description: string;
  why_needed: string;
  aws_service: string;
  layer: string;
  tier_options: DrilldownTierOption[];
  your_cost: {
    monthly_usd: number;
    monthly_fmt: string;
    annual_fmt: string;
    at_agents: number;
    cost_drivers: string;
    notes: string;
  };
  implementation: {
    weeks_min: number;
    weeks_max: number;
    weeks_range: string;
    team_size: number;
    role_mix: string;
    complexity: 'low' | 'medium' | 'high';
    cdk_construct: string;
  };
  cdk_snippet: string;
  workshop: { hint: string; url: string | null };
  engagement_pattern: string;
  kb_context: string;
}

export interface DrilldownCompleteEvent {
  type: 'drilldown_complete';
  data: DrilldownData;
}
