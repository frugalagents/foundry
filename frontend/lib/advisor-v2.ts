export type Workload =
  | 'coding'
  | 'internal_copilot'
  | 'hosting'
  | 'customer_facing'
  | 'process_automation'
  | 'marketplace';

export type AssessmentDraft = Record<string, unknown>;

export interface QuestionOption {
  value: string;
  label: string;
  hint?: string;
}

export interface AdvisorQuestion {
  id: string;
  path: string;
  section: 'frame' | 'ownership' | 'risk' | 'workload' | 'readiness';
  prompt: string;
  why: string;
  type: 'single' | 'multi' | 'boolean' | 'number' | 'range';
  options?: QuestionOption[];
  unit?: string;
  required?: boolean;
}

const AUDIENCE: QuestionOption[] = [
  { value: 'employees', label: 'Employees', hint: 'Internal workforce users' },
  { value: 'internal_builders', label: 'Internal builders', hint: 'Teams building and running agents' },
  { value: 'external_customers', label: 'External customers', hint: 'Users of your product or service' },
  { value: 'third_parties', label: 'Third parties', hint: 'Publishers, partners, or ecosystem participants' },
];

export const WORKLOADS: QuestionOption[] = [
  { value: 'coding', label: 'Coding and developer productivity' },
  { value: 'internal_copilot', label: 'Internal copilot or knowledge assistant' },
  { value: 'hosting', label: 'Agent-hosting platform' },
  { value: 'customer_facing', label: 'Customer-facing agentic product' },
  { value: 'process_automation', label: 'Process and workflow automation' },
  { value: 'marketplace', label: 'Agent marketplace or economy' },
];

const OWNERS: QuestionOption[] = [
  { value: 'central', label: 'Central enterprise team' },
  { value: 'shared', label: 'Shared central and domain ownership' },
  { value: 'domain', label: 'Business or domain teams' },
  { value: 'external', label: 'External provider or partner' },
  { value: 'unknown', label: 'Not decided' },
];

const BASE: AdvisorQuestion[] = [
  { id: 'audience', path: 'audience', section: 'frame', prompt: 'Who primarily consumes this platform?', why: 'Determines trust boundaries, identity, and product obligations.', type: 'single', options: AUDIENCE, required: true },
  { id: 'primary_workload', path: 'primary_workload', section: 'frame', prompt: 'What is the primary workload for the next 12 months?', why: 'Loads the correct scale, safety, and architecture discovery branch.', type: 'single', options: WORKLOADS, required: true },
  { id: 'secondary_workloads', path: 'secondary_workloads', section: 'frame', prompt: 'Which secondary workloads should the roadmap anticipate?', why: 'Adds future overlays without corrupting primary-workload sizing.', type: 'multi', options: WORKLOADS },

  { id: 'platform_owner', path: 'ownership.platform_owner', section: 'ownership', prompt: 'Who owns the platform product and roadmap?', why: 'Determines control-plane accountability.', type: 'single', options: OWNERS, required: true },
  { id: 'funding_owner', path: 'ownership.funding_owner', section: 'ownership', prompt: 'Who funds the platform and approves capacity spend?', why: 'Shapes chargeback, roadmap, and decision rights.', type: 'single', options: OWNERS },
  { id: 'policy_owner', path: 'ownership.policy_owner', section: 'ownership', prompt: 'Who maintains platform policy and compliance controls?', why: 'Assigns control ownership and residual-risk treatment.', type: 'single', options: OWNERS },
  { id: 'identity_owner', path: 'ownership.identity_owner', section: 'ownership', prompt: 'Who owns identity and tenant authorization?', why: 'Determines identity-plane placement.', type: 'single', options: OWNERS },
  { id: 'delivery_owner', path: 'ownership.agent_delivery_owner', section: 'ownership', prompt: 'Who builds and releases production agents?', why: 'Separates central, federated, and domain delivery.', type: 'single', options: OWNERS, required: true },
  { id: 'runtime_owner', path: 'ownership.runtime_operations_owner', section: 'ownership', prompt: 'Who operates agents and responds to runtime failures?', why: 'Determines runtime placement and operational ownership.', type: 'single', options: OWNERS, required: true },
  { id: 'incident_owner', path: 'ownership.incident_accountability', section: 'ownership', prompt: 'Who is accountable when an agent causes an incident?', why: 'Assigns residual risk and escalation responsibility.', type: 'single', options: OWNERS, required: true },

  { id: 'autonomy', path: 'risk.autonomy', section: 'risk', prompt: 'What actions may agents take without approval?', why: 'Activates execution policy and approval controls.', type: 'single', required: true, options: [
    { value: 'suggest', label: 'Suggest only' },
    { value: 'approval', label: 'Act after human approval' },
    { value: 'autonomous', label: 'Act autonomously within policy' },
    { value: 'unknown', label: 'Not decided' },
  ] },
  { id: 'failure_impact', path: 'risk.failure_impact', section: 'risk', prompt: 'What is the worst credible impact of an incorrect action?', why: 'Sets control strength and risk treatment.', type: 'single', required: true, options: [
    { value: 'low', label: 'Low and easily corrected' },
    { value: 'moderate', label: 'Operational disruption' },
    { value: 'high', label: 'Financial or reputational harm' },
    { value: 'severe', label: 'Legal, safety, or systemic harm' },
    { value: 'unknown', label: 'Not assessed' },
  ] },
  { id: 'reversible', path: 'risk.reversible_actions', section: 'risk', prompt: 'Can production actions be reliably reversed?', why: 'Non-reversible actions require stronger gates.', type: 'boolean', required: true },
  { id: 'classifications', path: 'data.classifications', section: 'risk', prompt: 'What data classifications will agents process?', why: 'Determines encryption, access, logging, and isolation.', type: 'multi', required: true, options: [
    { value: 'public', label: 'Public' }, { value: 'internal', label: 'Internal' },
    { value: 'confidential', label: 'Confidential' }, { value: 'restricted', label: 'Restricted' },
    { value: 'phi', label: 'PHI' }, { value: 'pci', label: 'Payment data' },
  ] },
  { id: 'residency', path: 'data.residency', section: 'risk', prompt: 'Where is processing allowed?', why: 'Constrains regional and hybrid topology.', type: 'single', required: true, options: [
    { value: 'single_region', label: 'One region' }, { value: 'multi_region', label: 'Multiple regions' },
    { value: 'country_bound', label: 'Country or jurisdiction bound' }, { value: 'hybrid', label: 'On-premises and cloud' },
    { value: 'multi_cloud', label: 'Multiple clouds' }, { value: 'unknown', label: 'Not confirmed' },
  ] },
  { id: 'regulations', path: 'data.regulations', section: 'risk', prompt: 'Which regimes are binding?', why: 'Adds explicit controls and evidence obligations.', type: 'multi', required: true, options: [
    { value: 'NONE', label: 'None identified' }, { value: 'SOC2', label: 'SOC 2' },
    { value: 'SOX', label: 'SOX' }, { value: 'PCI-DSS', label: 'PCI-DSS' },
    { value: 'HIPAA', label: 'HIPAA' }, { value: 'FEDRAMP', label: 'FedRAMP' },
    { value: 'GDPR', label: 'GDPR' }, { value: 'EU-AI-ACT', label: 'EU AI Act' },
  ] },
  { id: 'isolation', path: 'nfr.tenant_isolation', section: 'risk', prompt: 'What isolation boundary is required?', why: 'Directly selects shared, namespace, account, or dedicated deployment.', type: 'single', required: true, options: [
    { value: 'shared_rbac', label: 'Shared service with RBAC' },
    { value: 'namespace', label: 'Separate namespaces' },
    { value: 'account', label: 'Separate cloud accounts' },
    { value: 'dedicated_stack', label: 'Dedicated stack per tenant' },
    { value: 'unknown', label: 'Not decided' },
  ] },
  { id: 'availability', path: 'nfr.availability_pct', section: 'risk', prompt: 'What production availability is required?', why: 'Activates multi-region and resilience components.', type: 'number', unit: '%', required: true },
  { id: 'latency', path: 'nfr.p95_latency_ms', section: 'risk', prompt: 'What p95 response time is required?', why: 'Constrains placement, runtime, and model routing.', type: 'number', unit: 'ms', required: true },

  { id: 'maturity', path: 'current.maturity', section: 'readiness', prompt: 'What is the current production maturity?', why: 'Sets the roadmap starting point.', type: 'single', options: [
    { value: 'greenfield', label: 'Greenfield' }, { value: 'pilot', label: 'Pilots and proofs of concept' },
    { value: 'production', label: 'Production workloads' }, { value: 'scaled', label: 'Scaled platform' },
  ] },
  { id: 'identity', path: 'current.identity', section: 'readiness', prompt: 'What identity foundation exists today?', why: 'Determines reuse versus build.', type: 'single', options: [
    { value: 'oidc', label: 'Enterprise OIDC' }, { value: 'iam', label: 'AWS IAM-centric' },
    { value: 'multiple_idps', label: 'Multiple identity providers' }, { value: 'greenfield', label: 'Greenfield' },
  ] },
  { id: 'observability', path: 'current.observability', section: 'readiness', prompt: 'What observability foundation exists?', why: 'Determines integration and roadmap effort.', type: 'single', options: [
    { value: 'enterprise', label: 'Enterprise standard' }, { value: 'cloud_native', label: 'Cloud-native stack' },
    { value: 'fragmented', label: 'Team-specific tools' }, { value: 'greenfield', label: 'Greenfield' },
  ] },
  { id: 'target', path: 'economics.target_months', section: 'readiness', prompt: 'When must the first production release be ready?', why: 'Tests roadmap feasibility.', type: 'number', unit: 'months' },
  { id: 'budget', path: 'economics.monthly_budget_usd', section: 'readiness', prompt: 'What monthly run-rate ceiling should be tested?', why: 'Validates the workload-based estimate.', type: 'number', unit: 'USD' },
];

const range = (id: string, path: string, prompt: string, unit: string, why = 'Supplies branch-specific capacity and cost evidence.'): AdvisorQuestion =>
  ({ id, path, section: 'workload', prompt, why, type: 'range', unit, required: true });

const BRANCH: Record<Workload, AdvisorQuestion[]> = {
  coding: [
    range('developers', 'workload_profile.developers', 'How many developers will use the platform?', 'developers'),
    { id: 'repositories', path: 'workload_profile.repositories', section: 'workload', prompt: 'How many repositories are in scope?', why: 'Sizes indexing and integration effort.', type: 'number', unit: 'repositories' },
    range('sessions', 'workload_profile.concurrent_sessions', 'How many concurrent coding sessions must it support?', 'sessions'),
    range('calls', 'workload_profile.monthly_model_calls', 'What monthly model-call range do you expect?', 'calls'),
    range('tokens', 'workload_profile.tokens_per_call', 'What token range do you expect per call?', 'tokens'),
    { id: 'code_boundary', path: 'workload_profile.code_boundary', section: 'workload', prompt: 'What is the hard boundary for source code and IP?', why: 'Determines network, model, and data controls.', type: 'single', required: true, options: [
      { value: 'vpc_only', label: 'Nothing leaves controlled networks' }, { value: 'approved_saas', label: 'Approved SaaS is allowed' },
      { value: 'no_constraint', label: 'No special boundary' }, { value: 'unknown', label: 'Not decided' },
    ] },
    { id: 'sandbox', path: 'workload_profile.execution_sandbox', section: 'workload', prompt: 'Will agents execute code or repository commands?', why: 'Activates isolated execution.', type: 'boolean', required: true },
  ],
  internal_copilot: [
    { id: 'employees', path: 'workload_profile.employees', section: 'workload', prompt: 'How many employees are eligible?', why: 'Frames adoption ceiling.', type: 'number', unit: 'employees' },
    range('active_users', 'workload_profile.monthly_active_users', 'How many monthly active users do you expect?', 'users'),
    { id: 'domains', path: 'workload_profile.data_domains', section: 'workload', prompt: 'How many governed data domains must it access?', why: 'Sizes data ownership and permission integration.', type: 'number', unit: 'domains', required: true },
    range('queries', 'workload_profile.monthly_queries', 'What monthly query range do you expect?', 'queries'),
    range('query_tokens', 'workload_profile.tokens_per_query', 'What token range do you expect per query?', 'tokens'),
    { id: 'actions', path: 'workload_profile.action_enabled', section: 'workload', prompt: 'Will it take actions in enterprise systems?', why: 'Activates action policy and approvals.', type: 'boolean', required: true },
  ],
  hosting: [
    { id: 'builder_teams', path: 'workload_profile.builder_teams', section: 'workload', prompt: 'How many teams will build agents?', why: 'Relevant here because builder ownership is the product.', type: 'number', unit: 'teams', required: true },
    range('tenants', 'workload_profile.tenants', 'How many isolated tenants must be hosted?', 'tenants'),
    range('agents', 'workload_profile.deployed_agents', 'How many production agents will be deployed?', 'agents'),
    range('hosting_calls', 'workload_profile.monthly_model_calls', 'What monthly model-call range do you expect?', 'calls'),
    range('hosting_tokens', 'workload_profile.tokens_per_call', 'What token range do you expect per call?', 'tokens'),
    { id: 'self_service', path: 'workload_profile.self_service', section: 'workload', prompt: 'How independently should teams provision agents?', why: 'Shapes control-plane and workflow design.', type: 'single', required: true, options: [
      { value: 'full', label: 'Fully self-service' }, { value: 'approval', label: 'Request and approve' },
      { value: 'central', label: 'Central team provisions' }, { value: 'unknown', label: 'Not decided' },
    ] },
  ],
  customer_facing: [
    range('customer_tenants', 'workload_profile.tenants', 'How many customer tenants must be isolated?', 'tenants'),
    range('customer_users', 'workload_profile.monthly_active_users', 'How many monthly active customers do you expect?', 'users'),
    range('average_rps', 'workload_profile.average_rps', 'What average request-rate range do you expect?', 'requests/second'),
    { id: 'peak_rps', path: 'workload_profile.peak_rps', section: 'workload', prompt: 'What peak request rate must it sustain?', why: 'Sizes burst and failover capacity.', type: 'number', unit: 'requests/second', required: true },
    range('customer_calls', 'workload_profile.monthly_model_calls', 'What monthly model-call range do you expect?', 'calls'),
    range('customer_tokens', 'workload_profile.tokens_per_call', 'What token range do you expect per request?', 'tokens'),
  ],
  process_automation: [
    { id: 'workflows', path: 'workload_profile.workflows', section: 'workload', prompt: 'How many production workflows are in scope?', why: 'Sizes integration and delivery work.', type: 'number', unit: 'workflows', required: true },
    range('executions', 'workload_profile.monthly_executions', 'What monthly execution range do you expect?', 'executions'),
    range('execution_tokens', 'workload_profile.tokens_per_execution', 'What token range do you expect per execution?', 'tokens'),
    { id: 'duration', path: 'workload_profile.average_duration_minutes', section: 'workload', prompt: 'How long does an average workflow run?', why: 'Determines runtime and orchestration choice.', type: 'number', unit: 'minutes', required: true },
    { id: 'exceptions', path: 'workload_profile.exception_rate_pct', section: 'workload', prompt: 'What exception rate needs human handling?', why: 'Sizes operations and review capacity.', type: 'number', unit: '%', required: true },
    { id: 'approval', path: 'workload_profile.approval_required', section: 'workload', prompt: 'Must humans approve workflow actions?', why: 'Activates durable approval controls.', type: 'boolean', required: true },
  ],
  marketplace: [
    range('publishers', 'workload_profile.publishers', 'How many agent publishers are expected?', 'publishers'),
    range('consumers', 'workload_profile.consumers', 'How many consumers are expected?', 'consumers'),
    range('listed_agents', 'workload_profile.listed_agents', 'How many agents will be listed?', 'agents'),
    range('transactions', 'workload_profile.monthly_transactions', 'What monthly transaction range do you expect?', 'transactions'),
    range('transaction_tokens', 'workload_profile.tokens_per_transaction', 'What token range do you expect per transaction?', 'tokens'),
    { id: 'external_agents', path: 'workload_profile.external_agents', section: 'workload', prompt: 'May third-party agents publish or transact?', why: 'Activates publisher trust and supply-chain controls.', type: 'boolean', required: true },
    { id: 'billing', path: 'workload_profile.billing_model', section: 'workload', prompt: 'How will usage be billed?', why: 'Activates metering and entitlement components.', type: 'single', required: true, options: [
      { value: 'none', label: 'No billing yet' }, { value: 'per_call', label: 'Per call' },
      { value: 'per_outcome', label: 'Per outcome' }, { value: 'subscription', label: 'Subscription' },
      { value: 'unknown', label: 'Not decided' },
    ] },
  ],
};

export function questionsFor(draft: AssessmentDraft): AdvisorQuestion[] {
  const workload = draft.primary_workload as Workload | undefined;
  return [...BASE, ...(workload ? BRANCH[workload] : [])].filter((question) => {
    if (question.path === 'secondary_workloads' && !workload) return false;
    return true;
  });
}

export function isAnswered(value: unknown, type: AdvisorQuestion['type']): boolean {
  if (value === undefined || value === null || value === '' || value === 'unknown') return false;
  if (type === 'multi') return Array.isArray(value) && value.length > 0;
  if (type === 'range') {
    if (typeof value !== 'object' || value === null) return false;
    const rangeValue = value as Record<string, unknown>;
    return ['low', 'expected', 'high'].every((key) => typeof rangeValue[key] === 'number');
  }
  return true;
}

export function missingRequired(draft: AssessmentDraft): string[] {
  return questionsFor(draft)
    .filter((question) => question.required && !isAnswered(draft[question.path], question.type))
    .map((question) => question.path);
}

const value = <T>(draft: AssessmentDraft, path: string, fallback: T): T =>
  (draft[path] === undefined ? fallback : draft[path]) as T;

export function buildAssessmentInput(draft: AssessmentDraft): Record<string, unknown> {
  const workload = draft.primary_workload as Workload;
  const profile = Object.fromEntries(
    Object.entries(draft)
      .filter(([key]) => key.startsWith('workload_profile.'))
      .filter(([, val]) => {
        if (typeof val !== 'object' || val === null || Array.isArray(val)) return true;
        const candidate = val as Record<string, unknown>;
        if (!('unit' in candidate)) return true;
        return ['low', 'expected', 'high'].every((key) => typeof candidate[key] === 'number');
      })
      .map(([key, val]) => [key.slice('workload_profile.'.length), val]),
  );
  return {
    schema_version: '2.0',
    audience: draft.audience,
    primary_workload: workload,
    secondary_workloads: value(draft, 'secondary_workloads', []),
    ownership: {
      platform_owner: draft['ownership.platform_owner'],
      funding_owner: value(draft, 'ownership.funding_owner', 'unknown'),
      policy_owner: value(draft, 'ownership.policy_owner', 'unknown'),
      identity_owner: value(draft, 'ownership.identity_owner', 'unknown'),
      agent_delivery_owner: draft['ownership.agent_delivery_owner'],
      runtime_operations_owner: draft['ownership.runtime_operations_owner'],
      incident_accountability: draft['ownership.incident_accountability'],
    },
    risk: {
      autonomy: draft['risk.autonomy'],
      failure_impact: draft['risk.failure_impact'],
      reversible_actions: draft['risk.reversible_actions'],
      human_approval_required: value(draft, 'risk.human_approval_required', null),
      regulator_facing_audit: value(draft, 'risk.regulator_facing_audit', null),
    },
    data: {
      classifications: draft['data.classifications'],
      residency: draft['data.residency'],
      regulations: draft['data.regulations'],
      data_locations: value(draft, 'data.data_locations', []),
      crosses_trust_boundaries: value(draft, 'data.crosses_trust_boundaries', null),
    },
    nfr: {
      tenant_isolation: draft['nfr.tenant_isolation'],
      availability_pct: draft['nfr.availability_pct'],
      p95_latency_ms: draft['nfr.p95_latency_ms'],
      rto_hours: value(draft, 'nfr.rto_hours', null),
      rpo_hours: value(draft, 'nfr.rpo_hours', null),
      regions: value(draft, 'nfr.regions', 1),
    },
    current: {
      maturity: value(draft, 'current.maturity', 'greenfield'),
      identity: value(draft, 'current.identity', 'greenfield'),
      observability: value(draft, 'current.observability', 'greenfield'),
      cicd: value(draft, 'current.cicd', 'greenfield'),
      reusable_gateway: value(draft, 'current.reusable_gateway', false),
      reusable_data_platform: value(draft, 'current.reusable_data_platform', false),
    },
    economics: {
      monthly_budget_usd: value(draft, 'economics.monthly_budget_usd', null),
      target_months: value(draft, 'economics.target_months', null),
      priority: value(draft, 'economics.priority', 'unknown'),
    },
    workload_profile: { kind: workload, ...profile },
  };
}
