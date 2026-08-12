export type RequirementValue = string | number | boolean | null;

export type ComponentStatus = 'baseline' | 'added' | 'removed';
export type FeasibilityStatus = 'feasible' | 'rejected' | 'unknown';
export type RequirementStatus = 'answered' | 'assumed' | 'unknown' | 'unanswered';
export type RuleAuthority =
  | 'hard_constraint'
  | 'compatibility'
  | 'preference'
  | 'explanation';
export type RuleEffect = 'require' | 'recommend' | 'exclude' | 'warn';

export interface ArchitectureWorkspaceMeta {
  workspace_id: string;
  workspace_name: string;
  revision_id: string;
  revision_number: number;
  catalog_id: string;
  catalog_version: string;
  generated_at: string;
  persistence_revision?: number;
  persistence_hash?: string;
}

export interface RequirementAssumption {
  rationale: string;
  confidence: number;
  owner: string;
  source: string;
}

export interface ArchitectureRequirement {
  id: string;
  name: string;
  description?: string;
  customer_question?: string;
  why_it_matters?: string;
  candidate_answers?: RequirementValue[];
  required?: boolean;
  value: RequirementValue;
  status: RequirementStatus;
  source?: string;
  assumption?: RequirementAssumption;
}

export interface AnswerEnrichment {
  label: string;
  description: string;
  best_for?: string;
  watch_out?: string;
}

export interface ArchitectureComponent {
  id: string;
  name: string;
  description: string;
  kind: string;
  status: ComponentStatus;
}

export interface ArchitecturePlane {
  id: string;
  label: string;
  components: ArchitectureComponent[];
}

export interface ArchitectureEdge {
  id: string;
  source_component_id: string;
  target_component_id: string;
  relationship: string;
}

export interface ArchitectureProjection {
  pattern_id: string;
  component_count: number;
  edge_count: number;
  planes: ArchitecturePlane[];
  edges: ArchitectureEdge[];
}

export interface DeploymentFeasibility {
  pattern_id: string;
  name: string;
  description?: string;
  reason?: string;
  status: FeasibilityStatus;
  rejection_rule_ids: string[];
  blocking_requirement_ids: string[];
}

export interface AnswerImpact {
  answer: RequirementValue;
  added_component_ids: string[];
  removed_component_ids: string[];
  added_edge_ids: string[];
  removed_edge_ids: string[];
  activated_rule_ids: string[];
  deactivated_rule_ids: string[];
  feasible_pattern_ids: string[];
  rejected_pattern_ids: string[];
  unknown_pattern_ids: string[];
}

export interface NextArchitectureQuestion {
  requirement_id: string;
  prompt: string;
  customer_question: string;
  why_it_matters?: string;
  why_now: string;
  candidate_answers: RequirementValue[];
  answer_enrichments: (AnswerEnrichment | null)[];
  answer_impacts: AnswerImpact[];
}

export interface DecisionTraceEntry {
  evaluation_id: string;
  rule_id: string;
  authority: RuleAuthority;
  effect: RuleEffect;
  requirement_ids: string[];
  target_component_ids: string[];
  target_pattern_ids?: string[];
  evidence_claim_ids?: string[];
  rationale: string;
}

export interface EvidenceClaim {
  claim_id: string;
  statement: string;
  review_status: string;
  effective_on: string;
  source_locator: string;
  source_id: string;
  source_title?: string;
  source_uri?: string;
  source_publisher?: string;
}

export interface DeployableSelection {
  component_id: string;
  service_variant_id: string;
  service_name: string;
  provider_class: 'aws' | 'oss' | 'saas' | 'byop';
  delivery_model: string;
}

export interface DeployableCandidate {
  bundle_id: string;
  template_id: string;
  name: string;
  deployment_family_id: string;
  compatibility_status: 'compatible' | 'conditional' | 'incompatible';
  selections: DeployableSelection[];
  findings?: {
    finding_id: string;
    status: string;
    severity: string;
    code: string;
    message: string;
    component_ids: string[];
    requirement_id?: string;
  }[];
  dimension_scores: { dimension_id: string; score: number }[];
  weighted_score: number;
  tradeoffs: {
    tradeoff_id: string;
    kind: string;
    statement: string;
    dimension_id?: string;
    impact?: number;
  }[];
  rank: number;
  pareto_optimal: boolean;
}

export interface DecisionGuidanceEvidence {
  claim_id: string;
  statement: string;
  review_status: string;
  effective_from: string;
  stale_after: string;
  source_snapshot_id: string;
  source_id: string;
  source_name: string;
  source_publisher: string;
  source_uri: string;
  source_locator: string;
  authority_tier: string;
}

export interface CandidateDecisionGuidance {
  candidate_id: string;
  template_id: string;
  pattern_id: string;
  title: string;
  summary: string;
  decision: string;
  fit: {
    status: 'compatible' | 'conditional' | 'incompatible';
    summary: string;
    matched_requirements: {
      requirement_id: string;
      name?: string;
      value: RequirementValue;
    }[];
    conditional_requirements: {
      requirement_id: string;
      name?: string;
      value: RequirementValue;
    }[];
  };
  recommended_when: string[];
  avoid_when: string[];
  tradeoffs: string[];
  reviewed_at: string;
  reviewer_ids: string[];
  evidence: DecisionGuidanceEvidence[];
  advisory: true;
}

export interface DeployableDecisionMatrix {
  candidates: DeployableCandidate[];
  pareto_candidate_ids: string[];
  recommendation: {
    state: 'recommended' | 'conditional' | 'advisory' | 'no_viable_candidate';
    candidate_id?: string;
    rationale: string;
  };
  sensitivity: {
    dimension_id: string;
    baseline_candidate_id: string;
    challenger_candidate_id?: string;
    baseline_weight?: number;
    switch_weight?: number;
    winner_changes: boolean;
    score_margin_at_baseline?: number;
  }[];
  result_hash: string;
}

export interface AssurancePacket {
  selected_bundle_id?: string;
  packet_hash: string;
  security: {
    threats: {
      threat_id: string;
      title: string;
      category: string;
      residual_score: number;
      residual_rating: 'low' | 'moderate' | 'high' | 'critical';
      required_control_ids: string[];
      applicable_component_ids?: string[];
    }[];
    controls: {
      control_id: string;
      title: string;
      status: 'planned' | 'verified' | 'failed';
      evidence_ids?: string[];
      applicable_component_ids?: string[];
      verification: {
        method: string;
        evidence_type: string;
        acceptance_criteria: string;
        frequency: string;
      };
    }[];
    best_practices: {
      practice_id: string;
      title: string;
      status: 'planned' | 'verified';
      rationale: string;
      implementation: string;
      applicable_component_ids?: string[];
      control_ids?: string[];
    }[];
    residual_risk_total: number;
    high_or_critical_residual_count: number;
    verified_control_count: number;
  };
  economics: {
    assumptions: {
      assumption_id: string;
      name: string;
      unit: string;
      value_range: NumericRange;
      rationale: string;
      source: 'catalog_default' | 'workspace_requirement';
    }[];
    unit_costs: {
      cost_id: string;
      name: string;
      unit: string;
      currency: 'USD';
      value_range: NumericRange;
      effective_on: string;
      status: 'placeholder' | 'evidence_backed' | 'unverified_override';
      source: string;
    }[];
    totals: {
      cost_per_requested_task: NumericRange;
      cost_per_successful_task: NumericRange;
      cost_per_accepted_pull_request: NumericRange;
      monthly_platform_cost: NumericRange;
      monthly_cost_per_developer: NumericRange;
    };
    sensitivity_drivers: string[];
    pricing_warning: string;
  };
  outcomes: {
    join_path: string[];
    metrics: {
      metric_id: string;
      name: string;
      formula: string;
      unit: string;
      denominator: string;
    }[];
    measurement_horizons: {
      horizon: 'baseline' | 'day_30' | 'day_90' | 'day_180';
      objective: string;
      activities: string[];
    }[];
  };
  roadmap: {
    phases: {
      phase_id: string;
      sequence: number;
      name: string;
      work_packages: {
        package_id: string;
        title: string;
        owner: string;
        effort_person_days: NumericRange;
      }[];
      exit_criteria: string[];
    }[];
    total_effort_person_days: NumericRange;
    critical_path_package_ids: string[];
  };
}

export interface NumericRange {
  low: number;
  high: number;
}

export interface DecisionAuthority {
  schema_version: string;
  authoritative_operations: string[];
  advisory_outputs: string[];
  automatic_bundle_selection: boolean;
}

export interface ArchitectureWorkspaceProjection {
  meta: ArchitectureWorkspaceMeta;
  decision_authority: DecisionAuthority;
  requirements: ArchitectureRequirement[];
  assumptions?: (RequirementAssumption & {
    requirement_id: string;
    name: string;
    value: RequirementValue;
  })[];
  architecture: ArchitectureProjection;
  feasibility: DeploymentFeasibility[];
  deployable_solution?: DeployableDecisionMatrix;
  decision_guidance?: CandidateDecisionGuidance[];
  assurance?: AssurancePacket;
  next_question: NextArchitectureQuestion | null;
  decision_trace: DecisionTraceEntry[];
  evidence?: EvidenceClaim[];
  decision_history?: {
    transitions: {
      transition_id: string;
      requirement_changes: {
        requirement_id: string;
        name: string;
        change_type: string;
      }[];
      architecture_delta: {
        components: {
          added: { component_id: string; name: string }[];
          removed: { component_id: string; name: string }[];
        };
      };
    }[];
    history_hash: string;
  };
}

export type WorkspaceReadinessState = 'needs-information' | 'conditional' | 'publishable';

export interface WorkspaceGuidance {
  totalRequirements: number;
  confirmedRequirements: number;
  assumedRequirements: number;
  openRequirements: ArchitectureRequirement[];
  requiredOpenRequirements: ArchitectureRequirement[];
  coveredPercent: number;
  feasibleAlternatives: number;
  allFamiliesRejected: boolean;
  publicationBlockers: string[];
  criticalControlBlockers: number;
  highRiskCount: number;
  unapprovedCostInputs: number;
  missingEvidenceCount: number;
  readiness: WorkspaceReadinessState;
  readinessLabel: string;
  readinessDetail: string;
}

export function deriveWorkspaceGuidance(
  projection: ArchitectureWorkspaceProjection,
): WorkspaceGuidance {
  const openRequirements = projection.requirements.filter(
    (requirement) => requirement.status === 'unanswered' || requirement.status === 'unknown',
  );
  const requiredOpenRequirements = openRequirements.filter((requirement) => requirement.required);
  const confirmedRequirements = projection.requirements.filter(
    (requirement) => requirement.status === 'answered',
  ).length;
  const assumedRequirements = projection.requirements.filter(
    (requirement) => requirement.status === 'assumed',
  ).length;
  const coveredRequirements = projection.requirements.length - openRequirements.length;
  const feasibleAlternatives = projection.feasibility.filter(
    (alternative) => alternative.status === 'feasible',
  ).length;
  const allFamiliesRejected = projection.feasibility.length > 0
    && projection.feasibility.every((f) => f.status === 'rejected');
  const hasRecommendation =
    projection.deployable_solution?.recommendation.state === 'recommended';
  const assurance = projection.assurance;
  // The assurance contract does not classify control criticality separately,
  // so every required control is publication-critical and must be verified.
  const criticalControlBlockers = (assurance?.security.controls ?? []).filter(
    (control) => control.status !== 'verified',
  ).length;
  const highRiskCount = assurance?.security.high_or_critical_residual_count ?? 0;
  const unapprovedCostInputs = (assurance?.economics.unit_costs ?? []).filter(
    (cost) => cost.status !== 'evidence_backed',
  ).length;
  const evidenceById = new Map(
    (projection.evidence ?? []).map((claim) => [claim.claim_id, claim]),
  );
  const missingEvidenceIds = new Set<string>();
  if (projection.decision_trace.length === 0) missingEvidenceIds.add('trace:missing');
  for (const trace of projection.decision_trace) {
    if (!trace.evidence_claim_ids?.length) {
      missingEvidenceIds.add(`trace:${trace.evaluation_id}`);
      continue;
    }
    for (const claimId of trace.evidence_claim_ids) {
      const claim = evidenceById.get(claimId);
      if (!claim || claim.review_status !== 'approved') missingEvidenceIds.add(claimId);
    }
  }
  for (const control of assurance?.security.controls ?? []) {
    if (control.status === 'verified' && !control.evidence_ids?.length) {
      missingEvidenceIds.add(`control:${control.control_id}`);
    }
  }
  const missingEvidenceCount = missingEvidenceIds.size;
  const publicationBlockers: string[] = [];
  if (feasibleAlternatives === 0) publicationBlockers.push('no confirmed feasible deployment family');
  if (!hasRecommendation) publicationBlockers.push('no recommended deployable solution');
  if (!assurance) publicationBlockers.push('assurance package missing');
  if (openRequirements.length > 0) {
    publicationBlockers.push(`${openRequirements.length} open requirement${openRequirements.length === 1 ? '' : 's'}`);
  }
  if (assumedRequirements > 0) {
    publicationBlockers.push(`${assumedRequirements} unconfirmed assumption${assumedRequirements === 1 ? '' : 's'}`);
  }
  if (criticalControlBlockers > 0) {
    publicationBlockers.push(`${criticalControlBlockers} critical control${criticalControlBlockers === 1 ? '' : 's'} not verified`);
  }
  if (highRiskCount > 0) {
    publicationBlockers.push(`${highRiskCount} high or critical residual risk${highRiskCount === 1 ? '' : 's'}`);
  }
  if (unapprovedCostInputs > 0) {
    publicationBlockers.push(`${unapprovedCostInputs} economics input${unapprovedCostInputs === 1 ? '' : 's'} not evidence-backed`);
  }
  if (missingEvidenceCount > 0) {
    publicationBlockers.push(`${missingEvidenceCount} decision evidence gap${missingEvidenceCount === 1 ? '' : 's'}`);
  }

  let readiness: WorkspaceReadinessState = 'publishable';
  let readinessLabel = 'Ready to publish';
  let readinessDetail = 'Requirements, controls, risks, economics, and decision evidence satisfy the publication gate.';

  if (requiredOpenRequirements.length > 0 || feasibleAlternatives === 0 || !hasRecommendation) {
    readiness = 'needs-information';
    readinessLabel = 'Needs customer input';
    if (requiredOpenRequirements.length > 0) {
      readinessDetail = `${requiredOpenRequirements.length} required decision${requiredOpenRequirements.length === 1 ? '' : 's'} must be resolved before publication.`;
    } else if (allFamiliesRejected && !projection.next_question) {
      readinessDetail = 'Your current answers eliminate all deployment families. Review the Trace tab to identify the conflicting requirements, then change one or more answers.';
    } else {
      readinessDetail = projection.next_question
        ? 'No deployment family is confirmed feasible yet. Resolve the next guided discovery decision to narrow the architecture.'
        : 'No deployment family is confirmed feasible yet. Check the Trace tab to see which requirements are blocking deployment family confirmation.';
    }
  } else if (!assurance || publicationBlockers.length > 0) {
    readiness = 'conditional';
    readinessLabel = 'Reviewable, not publishable';
    readinessDetail = !assurance
      ? 'The deterministic solution is available, but its assurance package is incomplete.'
      : `Resolve ${publicationBlockers[0]} before publishing this architecture package.`;
  }

  return {
    totalRequirements: projection.requirements.length,
    confirmedRequirements,
    assumedRequirements,
    openRequirements,
    requiredOpenRequirements,
    allFamiliesRejected,
    coveredPercent: projection.requirements.length === 0
      ? 0
      : Math.round((coveredRequirements / projection.requirements.length) * 100),
    feasibleAlternatives,
    publicationBlockers,
    criticalControlBlockers,
    highRiskCount,
    unapprovedCostInputs,
    missingEvidenceCount,
    readiness,
    readinessLabel,
    readinessDetail,
  };
}

const edge = (
  source: string,
  target: string,
): ArchitectureEdge => ({
  id: `edge:${source.replace('component:', '')}--depends-on--${target.replace('component:', '')}`,
  source_component_id: source,
  target_component_id: target,
  relationship: 'depends_on',
});

// Deterministic fixture retained for component-level development.
export const architectureSampleProjection: ArchitectureWorkspaceProjection = {
  meta: {
    workspace_id: 'workspace:coding-platform-demo',
    workspace_name: 'Enterprise coding agent platform',
    revision_id: 'revision:r-8fe360d807787009399e',
    revision_number: 2,
    catalog_id: 'catalog:coding-platform',
    catalog_version: '3.0.0',
    generated_at: '2026-07-30T12:00:00Z',
  },
  decision_authority: {
    schema_version: '1.0',
    authoritative_operations: [
      'catalog_lifecycle',
      'component_requirements',
      'dependency_closure',
      'deployment_eligibility',
      'required_controls',
    ],
    advisory_outputs: [
      'candidate_ranking',
      'pareto_analysis',
      'preference_rules',
      'sensitivity_analysis',
    ],
    automatic_bundle_selection: false,
  },
  requirements: [
    { id: 'requirement:execution-placement', name: 'Execution placement', value: 'hybrid', status: 'answered' },
    { id: 'requirement:asynchronous-tasks', name: 'Asynchronous tasks', value: true, status: 'answered' },
    { id: 'requirement:long-running-workspaces', name: 'Long-running workspaces', value: null, status: 'unanswered' },
    { id: 'requirement:multi-agent', name: 'Multiple coding agents', value: true, status: 'answered' },
    { id: 'requirement:multi-model-provider', name: 'Multiple model providers', value: true, status: 'answered' },
    { id: 'requirement:model-fallback', name: 'Model fallback', value: null, status: 'unanswered' },
    { id: 'requirement:model-residency-routing', name: 'Residency-aware routing', value: null, status: 'unanswered' },
    { id: 'requirement:restricted-egress', name: 'Restricted egress', value: true, status: 'answered' },
    { id: 'requirement:private-connectivity', name: 'Private connectivity', value: null, status: 'unanswered' },
    { id: 'requirement:source-control', name: 'Source control', value: 'gitlab-saas', status: 'answered' },
    { id: 'requirement:approved-package-registries', name: 'Approved package registries', value: true, status: 'answered' },
    { id: 'requirement:enterprise-identity', name: 'Enterprise identity', value: 'entra', status: 'answered' },
    { id: 'requirement:developer-count', name: 'Developer population', value: 5000, status: 'answered' },
    { id: 'requirement:concurrent-agent-tasks', name: 'Concurrent agent tasks', value: 1000, status: 'answered' },
    { id: 'requirement:approved-regions', name: 'Approved regions', value: 'any-approved', status: 'answered' },
    { id: 'requirement:action-approval', name: 'Action-dependent approval', value: true, status: 'answered' },
    { id: 'requirement:audit-retention-days', name: 'Audit retention', value: null, status: 'unanswered' },
    { id: 'requirement:team-boundaries', name: 'Team boundaries', value: true, status: 'answered' },
    { id: 'requirement:outcome-observability', name: 'Outcome observability', value: true, status: 'answered' },
    { id: 'requirement:economic-priority', name: 'Economic priority', value: null, status: 'unanswered' },
    { id: 'requirement:orchestration-mode', name: 'Agent orchestration mode', value: 'parallel-review', status: 'answered' },
    { id: 'requirement:model-routing-mode', name: 'Model routing mode', value: null, status: 'unanswered' },
    { id: 'requirement:warm-runtime-capacity', name: 'Warm runtime capacity', value: true, status: 'answered' },
  ],
  architecture: {
    pattern_id: 'pattern:logical-reference',
    component_count: 34,
    edge_count: 34,
    planes: [
      {
        id: 'experience',
        label: 'Experience',
        components: [
          { id: 'component:developer-clients', name: 'Coding agent clients', description: 'Developer-facing CLI, IDE, and task interfaces.', kind: 'core', status: 'baseline' },
          { id: 'component:advisor-workspace', name: 'Architecture workspace', description: 'Versioned requirements, decisions, and architecture state.', kind: 'core', status: 'baseline' },
        ],
      },
      {
        id: 'access',
        label: 'Access',
        components: [
          { id: 'component:workforce-identity', name: 'Workforce identity', description: 'Authenticates developers and resolves enterprise groups.', kind: 'core', status: 'baseline' },
          { id: 'component:workload-identity', name: 'Workload identity', description: 'Issues scoped identities to agent runs and tools.', kind: 'core', status: 'baseline' },
          { id: 'component:team-workspaces', name: 'Team workspaces', description: 'Separates delegated policy, quota, and audit scopes.', kind: 'core', status: 'baseline' },
        ],
      },
      {
        id: 'orchestration',
        label: 'Orchestration',
        components: [
          { id: 'component:agent-registry', name: 'Agent registry', description: 'Controls approved coding agents, versions, and ownership.', kind: 'core', status: 'baseline' },
          { id: 'component:workflow-definitions', name: 'Workflow definitions', description: 'Defines reproducible single-agent and multi-agent workflows.', kind: 'core', status: 'baseline' },
          { id: 'component:orchestration-runtime', name: 'Agent orchestration runtime', description: 'Coordinates agent turns, handoffs, state, and cancellation.', kind: 'core', status: 'baseline' },
          { id: 'component:multi-agent-supervisor', name: 'Multi-agent supervisor', description: 'Coordinates specialist workers and independent review.', kind: 'overlay', status: 'added' },
          { id: 'component:parallel-reviewer', name: 'Parallel candidates with independent review', description: 'Runs candidate agents and routes results through a separate reviewer.', kind: 'overlay', status: 'added' },
        ],
      },
      {
        id: 'model',
        label: 'Model',
        components: [
          { id: 'component:model-gateway', name: 'Model gateway', description: 'Provides a governed model invocation boundary.', kind: 'core', status: 'baseline' },
          { id: 'component:model-catalog', name: 'Model catalog', description: 'Records approved models, providers, regions, and constraints.', kind: 'core', status: 'baseline' },
          { id: 'component:model-router', name: 'Model router', description: 'Selects eligible models using declared policy and economics.', kind: 'overlay', status: 'added' },
        ],
      },
      {
        id: 'tool',
        label: 'Tool',
        components: [
          { id: 'component:tool-gateway', name: 'Tool and API gateway', description: 'Applies authentication, policy, and audit to tool invocation.', kind: 'core', status: 'baseline' },
          { id: 'component:connector-registry', name: 'Connector registry', description: 'Catalogs approved tools, APIs, schemas, and owners.', kind: 'core', status: 'baseline' },
          { id: 'component:source-control-integration', name: 'Source control integration', description: 'Connects issues, repositories, branches, reviews, and merges.', kind: 'core', status: 'baseline' },
          { id: 'component:package-access', name: 'Approved package access', description: 'Restricts dependency retrieval to governed registries.', kind: 'core', status: 'baseline' },
        ],
      },
      {
        id: 'execution',
        label: 'Execution',
        components: [
          { id: 'component:execution-broker', name: 'Execution broker', description: 'Places tasks onto eligible local or remote runtimes.', kind: 'core', status: 'baseline' },
          { id: 'component:local-runtime', name: 'Managed local runtime', description: 'Runs interactive coding agents on governed developer endpoints.', kind: 'runtime', status: 'added' },
          { id: 'component:ephemeral-runtime', name: 'Ephemeral task runtime', description: 'Runs isolated asynchronous tasks in short-lived environments.', kind: 'runtime', status: 'added' },
          { id: 'component:warm-runtime-pool', name: 'Warm pools and resumable snapshots', description: 'Maintains pre-initialized or resumable execution capacity.', kind: 'overlay', status: 'added' },
        ],
      },
      {
        id: 'governance',
        label: 'Governance',
        components: [
          { id: 'component:policy-engine', name: 'Policy engine', description: 'Evaluates tool, model, data, network, and approval policy.', kind: 'core', status: 'baseline' },
          { id: 'component:secrets-broker', name: 'Secrets broker', description: 'Issues short-lived credentials to approved agent actions.', kind: 'core', status: 'baseline' },
          { id: 'component:audit-ledger', name: 'Decision and action ledger', description: 'Preserves replayable requirements, decisions, and agent actions.', kind: 'core', status: 'baseline' },
          { id: 'component:quota-manager', name: 'Quota and budget manager', description: 'Enforces team concurrency, usage, and economic limits.', kind: 'core', status: 'baseline' },
          { id: 'component:human-approval', name: 'Risk-based human approval', description: 'Requires approval at declared high-impact action boundaries.', kind: 'overlay', status: 'added' },
          { id: 'component:restricted-egress', name: 'Restricted runtime egress', description: 'Allows runtimes to reach only approved destinations.', kind: 'overlay', status: 'added' },
        ],
      },
      {
        id: 'observability',
        label: 'Observability',
        components: [
          { id: 'component:telemetry-pipeline', name: 'Agent telemetry pipeline', description: 'Collects model, tool, runtime, and policy traces.', kind: 'core', status: 'baseline' },
          { id: 'component:evaluation-service', name: 'Evaluation service', description: 'Measures task quality, safety, and regression behavior.', kind: 'core', status: 'baseline' },
          { id: 'component:economics-ledger', name: 'Token and platform economics', description: 'Attributes model and platform cost to successful outcomes.', kind: 'core', status: 'baseline' },
          { id: 'component:outcome-correlator', name: 'Outcome correlator', description: 'Joins agent traces to source-control and CI results.', kind: 'core', status: 'baseline' },
          { id: 'component:multi-region', name: 'Multi-region resilience', description: 'Adds region-aware routing, failover, and evidence.', kind: 'overlay', status: 'added' },
        ],
      },
      {
        id: 'knowledge',
        label: 'Knowledge',
        components: [
          { id: 'component:architecture-knowledge', name: 'Architecture intelligence catalog', description: 'Stores versioned patterns, components, rules, and controls.', kind: 'core', status: 'baseline' },
          { id: 'component:evidence-catalog', name: 'Evidence claim catalog', description: 'Connects reviewed claims to immutable source snapshots.', kind: 'core', status: 'baseline' },
        ],
      },
    ],
    edges: [
      edge('component:advisor-workspace', 'component:workforce-identity'),
      edge('component:workload-identity', 'component:workforce-identity'),
      edge('component:team-workspaces', 'component:workforce-identity'),
      edge('component:agent-registry', 'component:workload-identity'),
      edge('component:workflow-definitions', 'component:agent-registry'),
      edge('component:orchestration-runtime', 'component:workflow-definitions'),
      edge('component:model-gateway', 'component:workload-identity'),
      edge('component:model-catalog', 'component:model-gateway'),
      edge('component:tool-gateway', 'component:workload-identity'),
      edge('component:connector-registry', 'component:tool-gateway'),
      edge('component:source-control-integration', 'component:tool-gateway'),
      edge('component:package-access', 'component:tool-gateway'),
      edge('component:execution-broker', 'component:workload-identity'),
      edge('component:policy-engine', 'component:workload-identity'),
      edge('component:secrets-broker', 'component:policy-engine'),
      edge('component:audit-ledger', 'component:workforce-identity'),
      edge('component:quota-manager', 'component:team-workspaces'),
      edge('component:telemetry-pipeline', 'component:workload-identity'),
      edge('component:evaluation-service', 'component:telemetry-pipeline'),
      edge('component:economics-ledger', 'component:telemetry-pipeline'),
      edge('component:outcome-correlator', 'component:evaluation-service'),
      edge('component:outcome-correlator', 'component:source-control-integration'),
      edge('component:evidence-catalog', 'component:architecture-knowledge'),
      edge('component:multi-agent-supervisor', 'component:orchestration-runtime'),
      edge('component:parallel-reviewer', 'component:multi-agent-supervisor'),
      edge('component:model-router', 'component:model-catalog'),
      edge('component:local-runtime', 'component:execution-broker'),
      edge('component:ephemeral-runtime', 'component:execution-broker'),
      edge('component:warm-runtime-pool', 'component:ephemeral-runtime'),
      edge('component:human-approval', 'component:policy-engine'),
      edge('component:human-approval', 'component:audit-ledger'),
      edge('component:restricted-egress', 'component:policy-engine'),
      edge('component:restricted-egress', 'component:execution-broker'),
      edge('component:multi-region', 'component:telemetry-pipeline'),
    ],
  },
  feasibility: [
    { pattern_id: 'pattern:developer-local', name: 'Developer-hosted local runtime', status: 'feasible', rejection_rule_ids: [], blocking_requirement_ids: [] },
    { pattern_id: 'pattern:vendor-ephemeral', name: 'Vendor-managed ephemeral task', status: 'feasible', rejection_rule_ids: [], blocking_requirement_ids: [] },
    { pattern_id: 'pattern:persistent-remote-workspace', name: 'Persistent remote developer workspace', status: 'unknown', rejection_rule_ids: [], blocking_requirement_ids: ['requirement:long-running-workspaces'] },
    { pattern_id: 'pattern:managed-customer-execution', name: 'Managed control plane with customer execution', status: 'rejected', rejection_rule_ids: ['rule:reject-managed-customer-placement'], blocking_requirement_ids: [] },
    { pattern_id: 'pattern:self-hosted-container', name: 'Self-hosted VM or container platform', status: 'rejected', rejection_rule_ids: ['rule:reject-self-hosted-container-placement'], blocking_requirement_ids: [] },
    { pattern_id: 'pattern:self-hosted-kubernetes', name: 'Self-hosted Kubernetes platform', status: 'rejected', rejection_rule_ids: ['rule:reject-self-hosted-kubernetes-placement'], blocking_requirement_ids: [] },
  ],
  next_question: {
    requirement_id: 'requirement:long-running-workspaces',
    prompt: 'Are persistent workspaces required for migrations or durable development environments?',
    customer_question: 'Do developers need the agent to maintain full context and state across work that spans days or weeks?',
    why_it_matters: 'Standard agent sessions are ephemeral — the workspace is discarded when a task ends. Persistent workspaces let agents maintain a durable desk for large, multi-session work.',
    why_now: 'This answer changes the logical architecture and resolves the remaining unknown deployment family.',
    candidate_answers: [true, false, null],
    answer_enrichments: [
      { label: 'Yes — we need persistent agent workspaces', description: 'Agents maintain their workspace state across multiple sessions.', best_for: 'Large codebase migrations, multi-sprint refactors, or long-running dependency upgrades.', watch_out: 'Persistent workspaces consume storage and compute even when idle.' },
      { label: 'No — each agent task starts fresh', description: 'Agents work on ephemeral, scoped checkouts. The workspace is discarded after each task.', best_for: 'Most task-oriented coding agent use cases — issue resolution, PR review, targeted refactoring.', watch_out: 'Not suitable for large migrations or multi-day tasks that require accumulated context.' },
      null,
    ],
    answer_impacts: [
      {
        answer: true,
        added_component_ids: ['component:persistent-workspace'],
        removed_component_ids: [],
        added_edge_ids: ['edge:persistent-workspace--depends-on--execution-broker'],
        removed_edge_ids: [],
        activated_rule_ids: ['rule:persistent-workspaces'],
        deactivated_rule_ids: [],
        feasible_pattern_ids: ['pattern:developer-local', 'pattern:persistent-remote-workspace', 'pattern:vendor-ephemeral'],
        rejected_pattern_ids: ['pattern:managed-customer-execution', 'pattern:self-hosted-container', 'pattern:self-hosted-kubernetes'],
        unknown_pattern_ids: [],
      },
      {
        answer: false,
        added_component_ids: [],
        removed_component_ids: [],
        added_edge_ids: [],
        removed_edge_ids: [],
        activated_rule_ids: ['rule:reject-nonpersistent-workspace'],
        deactivated_rule_ids: [],
        feasible_pattern_ids: ['pattern:developer-local', 'pattern:vendor-ephemeral'],
        rejected_pattern_ids: ['pattern:managed-customer-execution', 'pattern:persistent-remote-workspace', 'pattern:self-hosted-container', 'pattern:self-hosted-kubernetes'],
        unknown_pattern_ids: [],
      },
      {
        answer: null,
        added_component_ids: [],
        removed_component_ids: [],
        added_edge_ids: [],
        removed_edge_ids: [],
        activated_rule_ids: [],
        deactivated_rule_ids: [],
        feasible_pattern_ids: ['pattern:developer-local', 'pattern:vendor-ephemeral'],
        rejected_pattern_ids: ['pattern:managed-customer-execution', 'pattern:self-hosted-container', 'pattern:self-hosted-kubernetes'],
        unknown_pattern_ids: ['pattern:persistent-remote-workspace'],
      },
    ],
  },
  decision_trace: [
    { evaluation_id: 'evaluation:hybrid-execution', rule_id: 'rule:hybrid-execution', authority: 'hard_constraint', effect: 'require', requirement_ids: ['requirement:execution-placement'], target_component_ids: ['component:ephemeral-runtime', 'component:local-runtime'], rationale: 'Hybrid placement requires governed developer-local execution plus isolated ephemeral remote execution.' },
    { evaluation_id: 'evaluation:asynchronous-runtime', rule_id: 'rule:asynchronous-runtime', authority: 'hard_constraint', effect: 'require', requirement_ids: ['requirement:asynchronous-tasks'], target_component_ids: ['component:ephemeral-runtime'], rationale: 'Unattended tasks require an isolated ephemeral runtime.' },
    { evaluation_id: 'evaluation:high-concurrency-runtime', rule_id: 'rule:high-concurrency-runtime', authority: 'hard_constraint', effect: 'require', requirement_ids: ['requirement:concurrent-agent-tasks'], target_component_ids: ['component:ephemeral-runtime'], rationale: 'High concurrent task volume requires scalable remote execution.' },
    { evaluation_id: 'evaluation:warm-runtime-capacity', rule_id: 'rule:warm-runtime-capacity', authority: 'hard_constraint', effect: 'require', requirement_ids: ['requirement:warm-runtime-capacity'], target_component_ids: ['component:warm-runtime-pool'], rationale: 'Strict startup SLOs require warm capacity or resumable execution snapshots.' },
    { evaluation_id: 'evaluation:multi-agent-supervision', rule_id: 'rule:multi-agent-supervision', authority: 'hard_constraint', effect: 'require', requirement_ids: ['requirement:multi-agent'], target_component_ids: ['component:multi-agent-supervisor'], rationale: 'Multi-agent workflows require orchestration and supervision.' },
    { evaluation_id: 'evaluation:parallel-independent-review', rule_id: 'rule:parallel-independent-review', authority: 'hard_constraint', effect: 'require', requirement_ids: ['requirement:orchestration-mode'], target_component_ids: ['component:parallel-reviewer'], rationale: 'Parallel candidate generation requires supervision and an independent review stage.' },
    { evaluation_id: 'evaluation:multi-provider-routing', rule_id: 'rule:multi-provider-routing', authority: 'hard_constraint', effect: 'require', requirement_ids: ['requirement:multi-model-provider'], target_component_ids: ['component:model-router'], rationale: 'Multiple providers require a model catalog and policy router.' },
    { evaluation_id: 'evaluation:restricted-egress', rule_id: 'rule:restricted-egress', authority: 'hard_constraint', effect: 'require', requirement_ids: ['requirement:restricted-egress'], target_component_ids: ['component:restricted-egress'], rationale: 'Restricted egress requires a policy-enforced network boundary.' },
    { evaluation_id: 'evaluation:risk-based-approval', rule_id: 'rule:risk-based-approval', authority: 'hard_constraint', effect: 'require', requirement_ids: ['requirement:action-approval'], target_component_ids: ['component:human-approval'], rationale: 'Risk-dependent actions require policy and approval evidence.' },
    { evaluation_id: 'evaluation:outcome-correlation', rule_id: 'rule:outcome-correlation', authority: 'hard_constraint', effect: 'require', requirement_ids: ['requirement:outcome-observability'], target_component_ids: ['component:economics-ledger', 'component:outcome-correlator'], rationale: 'Outcome observability requires trace, evaluation, Git, and CI correlation.' },
    { evaluation_id: 'evaluation:regional-flexibility', rule_id: 'rule:regional-flexibility', authority: 'preference', effect: 'recommend', requirement_ids: ['requirement:approved-regions'], target_component_ids: ['component:multi-region'], rationale: 'Any-approved-region deployment benefits from region-aware routing.' },
    { evaluation_id: 'evaluation:team-isolation', rule_id: 'rule:team-isolation', authority: 'hard_constraint', effect: 'require', requirement_ids: ['requirement:team-boundaries'], target_component_ids: ['component:quota-manager', 'component:team-workspaces'], rationale: 'Team boundaries require independent quota and policy scopes.' },
    { evaluation_id: 'evaluation:scale-quotas', rule_id: 'rule:scale-quotas', authority: 'hard_constraint', effect: 'require', requirement_ids: ['requirement:developer-count'], target_component_ids: ['component:quota-manager'], rationale: 'Large developer populations require quota and budget controls.' },
    { evaluation_id: 'evaluation:package-governance', rule_id: 'rule:package-governance', authority: 'hard_constraint', effect: 'require', requirement_ids: ['requirement:approved-package-registries'], target_component_ids: ['component:package-access'], rationale: 'Approved registries require controlled package access.' },
    { evaluation_id: 'evaluation:reject-managed-customer-placement', rule_id: 'rule:reject-managed-customer-placement', authority: 'compatibility', effect: 'exclude', requirement_ids: ['requirement:execution-placement'], target_component_ids: [], target_pattern_ids: ['pattern:managed-customer-execution'], rationale: 'Managed customer execution requires customer-managed placement.' },
    { evaluation_id: 'evaluation:reject-self-hosted-container-placement', rule_id: 'rule:reject-self-hosted-container-placement', authority: 'compatibility', effect: 'exclude', requirement_ids: ['requirement:execution-placement'], target_component_ids: [], target_pattern_ids: ['pattern:self-hosted-container'], rationale: 'A self-hosted container platform requires customer-managed placement.' },
    { evaluation_id: 'evaluation:reject-self-hosted-kubernetes-placement', rule_id: 'rule:reject-self-hosted-kubernetes-placement', authority: 'compatibility', effect: 'exclude', requirement_ids: ['requirement:execution-placement'], target_component_ids: [], target_pattern_ids: ['pattern:self-hosted-kubernetes'], rationale: 'A self-hosted Kubernetes platform requires customer-managed placement.' },
  ],
};
