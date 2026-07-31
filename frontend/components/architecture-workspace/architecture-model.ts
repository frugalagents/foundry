// Shared model for the coding-agent reference architecture: block content
// (with per-block discovery questions), the color groups, which engine
// components make a block "active", the React Flow layout coordinates, and the
// connector wires. Kept framework-agnostic so both the canvas and the panel
// read from one source of truth.

export interface Decision { q: string; opts: string[] }
export interface BlockDef {
  id: string;
  t: string;
  d: string;
  what: string;
  group: string;
  dec: Decision[];
  p: string[];
  requirement?: string;
  answers?: { value: string; label: string }[];
}

export const GROUP_COLOR: Record<string, string> = {
  surface: '#b98cf0', access: '#7d9bff', harness: '#37dd7d', registry: '#2dd4bf',
  exec: '#fb7185', gateway: '#4cc4f5', external: '#8b98ab', ops: '#f0a850',
};

export const PHASE: Record<string, string> = {
  surface: 'Surface', access: 'Governance · control plane', registry: 'Registry · building blocks',
  harness: 'Harness core', exec: 'Execution', gateway: 'Gateway', external: 'External system',
  ops: 'Operations & economics',
};

// engine component ids that, when 'added', light a block up
export const ACTIVE_MAP: Record<string, string[]> = {
  providers: ['component:managed-model-provider', 'component:self-hosted-inference', 'component:model-router'],
  runtime: ['component:multi-agent-supervisor'],
  guardrails: ['component:human-approval'],
  observability: ['component:economics-ledger', 'component:outcome-correlator'],
  exec: ['component:local-runtime', 'component:ephemeral-runtime', 'component:container-runtime'],
};

export const BLOCKS: Record<string, BlockDef> = {
  // Surfaces
  ide: { id: 'ide', group: 'surface', t: 'IDE', d: 'in-editor agent', what: 'The agent inside VS Code / JetBrains — inline edits, diffs, side-panel chat.', dec: [{ q: 'Where does the harness run for the IDE?', opts: ['<b>Local</b> — low latency, uses local files', '<b>Remote / managed</b> — central control & audit', '<b>Hybrid</b> — UI local, execution remote'] }], p: ['One harness core behind every surface', 'Review-diff-then-apply as the safe default'] },
  cli: { id: 'cli', group: 'surface', t: 'CLI / Terminal', d: 'interactive + headless', what: 'Terminal surface for power users and scripting — same harness, non-interactive mode for automation.', dec: [{ q: 'Primary CLI mode?', opts: ['<b>Interactive</b> — dev in the loop', '<b>Headless</b> — piped into scripts, JSON output'] }], p: ['Headless mode must be fail-safe', 'Hard token / time budget per invocation'] },
  chat: { id: 'chat', group: 'surface', t: 'Chat / PR Bot', d: 'Slack · Teams · PR', what: 'Async surface to kick off tasks, review PRs, and approve actions from where teams already talk.', dec: [{ q: 'How autonomous on PRs?', opts: ['<b>Advisory</b> — comments only', '<b>Gating</b> — can block merge', '<b>Author</b> — opens its own PRs'] }], p: ['Every action links to an audit ID', 'Long jobs run async, notify on completion'] },
  ci: { id: 'ci', group: 'surface', t: 'CI/CD Trigger', d: 'agent in the pipeline', what: 'Agent invoked by pipelines — fix builds, bump dependencies, generate tests on event or schedule.', dec: [{ q: 'Trust in the pipeline?', opts: ['<b>Suggest</b> — opens PR for humans', '<b>Act</b> — commits within guardrails'] }], p: ['Budget-capped runs', 'No prod actions without approval'] },
  // Governance
  identity: { id: 'identity', group: 'access', t: 'Identity & Access', d: 'SSO · AuthN/Z · entitlements', what: 'Federates to your corporate IdP and authenticates every request before it reaches the harness — and governs egress: which identity may reach which enterprise tool through the MCP Gateway.', dec: [{ q: 'Identity source?', opts: ['<b>Corporate IdP</b> (Okta / Entra) via OIDC/SAML', '<b>SCIM</b> auto-provisioning of teams'] }, { q: 'Agent acts as whom?', opts: ['<b>The developer</b> — inherits their access', '<b>Scoped service identity</b> — least privilege'] }], p: ['Federate — no local accounts', 'Same identity governs ingress AND tool egress', 'Short-lived, scoped tokens'] },
  guardrails: { id: 'guardrails', group: 'access', t: 'Guardrails & Policy', d: 'filtering · approvals · DLP', what: 'Screens each prompt on the way in and each output on the way back — blocks or redacts policy violations, drives human-approval gates, keeps secrets / PII out of the model.', dec: [{ q: 'On violation?', opts: ['<b>Block</b>', '<b>Redact</b> & continue', '<b>Warn</b> & log'] }], p: ['Default-deny on state-changing actions', 'Secrets never enter the prompt; scan I/O for PII', 'One policy engine, every surface — no bypass'], requirement: 'requirement:action-approval', answers: [{ value: 'true', label: 'Require risk-based human approval' }, { value: 'false', label: 'No human-in-the-loop gate' }] },
  quota: { id: 'quota', group: 'access', t: 'Quota & Rate Limits', d: 'throttling · seats · spend caps', what: 'Enforces limits at the edge before any model or tool spend — per-user and per-team rate limits, concurrency, seat entitlements and hard spend caps.', dec: [{ q: 'Limit model?', opts: ['<b>Per-user + per-team</b> rate limits', '<b>Concurrency caps</b> — bound parallel agents', '<b>Hard spend ceiling</b> per team'] }], p: ['Enforce quotas before spend, at the edge', 'Alert at 80%, cap at 100%'] },
  // Harness (heart)
  harness: { id: 'harness', group: 'harness', t: 'Coding Agent Harness', d: 'the heart · reason ▸ act ▸ observe', what: 'The engine that runs a coding task: reads context, plans, calls the model, invokes tools / skills / subagents, observes results, and loops until done. Loads its capabilities from the Registry and reaches the outside world only through the Gateways.', dec: [{ q: 'Autonomy per task?', opts: ['<b>Step cap</b> before a human check', '<b>Plan-first</b> — approve the plan, then run', '<b>Full auto</b> within guardrails'] }], p: ['Deterministic control flow around the model', 'Interruptible & steerable mid-task', 'Binds to gateways, never directly to tools/models'] },
  // Registry
  registry: { id: 'registry', group: 'registry', t: 'Registry / Catalog', d: 'approved building blocks', what: 'The signed, versioned source of truth for everything the harness may load — tools, plugins, skills, subagents, MCP servers — plus who is entitled to use each.', dec: [{ q: 'Catalog scope?', opts: ['<b>Org-wide</b> — one source of truth', '<b>Per-team</b> — autonomy, more sprawl', '<b>Federated</b> — org base + team extensions'] }, { q: 'Publish workflow?', opts: ['<b>Self-serve + automated scan</b> — fast', '<b>Security review gate</b> — safer', '<b>Risk-tiered</b> — read-only auto, write reviewed'] }], p: ['Nothing loads unless published & signed', 'Version-pin + central kill-switch on compromise'] },
  tools: { id: 'tools', group: 'registry', t: 'Tools & Plugins', d: 'file · shell · git · search', what: 'The capabilities the harness invokes directly — file edit, shell, git, search — and plugins that extend them.', dec: [{ q: 'Tool granting model?', opts: ['<b>Allowlist per agent</b> — explicit', '<b>Scope-based</b> — role decides', '<b>Arg-level policy</b> on sensitive tools'] }], p: ['Read and write tools separated & separately entitled', 'Least capability by default'] },
  skills: { id: 'skills', group: 'registry', t: 'Skills', d: 'reusable procedures', what: "Packaged know-how the agent loads on demand — 'how we do migrations', 'our PR checklist' — authored once, shared across agents.", dec: [{ q: 'Skill governance?', opts: ['<b>Open</b> — anyone contributes', '<b>Curated</b> — reviewed & signed', '<b>Risk-tiered</b> — scanned for injection'] }], p: ['Signed, version-pinned artifacts', 'Loaded on demand to save context'] },
  subagents: { id: 'subagents', group: 'registry', t: 'Subagents', d: 'delegated specialists', what: 'Purpose-built agents the main harness can spawn for scoped work (explore, review, migrate) — each with its own tools and limits.', dec: [{ q: 'Delegation policy?', opts: ['<b>Fixed roster</b> — only approved subagents', '<b>Depth / fan-out caps</b> — stop runaway trees', '<b>Budget caps</b> per subagent'] }], p: ['Subagent scope ≤ parent (never expanded)', 'Caps on recursion, fan-out, and budget'] },
  mcpservers: { id: 'mcpservers', group: 'registry', t: 'MCP Servers', d: 'integration connectors', what: 'The MCP servers the harness may connect to — each wrapping an enterprise system (Jira, GitHub, internal APIs). Reached at runtime through the MCP Gateway.', dec: [{ q: 'Who hosts MCP servers?', opts: ['<b>Vendor servers</b> for common systems', '<b>Custom</b> for proprietary internal APIs', '<b>Mix</b> behind the gateway'] }], p: ['Every server registered, signed, versioned', 'Reached only via the gateway — never direct'] },
  // Execution
  exec: { id: 'exec', group: 'exec', t: 'Execution Environment', d: 'where the agent runs code', what: 'The environment the harness connects to for running commands, tests, and builds — local machine, built-in sandbox, or a remote ephemeral workspace.', dec: [{ q: 'Network egress?', opts: ['<b>Blocked</b> — most secure', '<b>Allowlist</b> — package registries only', '<b>Open</b> — riskier'] }], p: ['Isolate, cap resources, tear down clean', 'Deny egress by default; allowlist explicitly'], requirement: 'requirement:execution-placement', answers: [{ value: 'local', label: 'Local machine (developer endpoint)' }, { value: 'vendor-managed', label: 'Vendor-managed ephemeral runtime' }, { value: 'customer-managed', label: 'Customer-managed container runtime' }, { value: 'hybrid', label: 'Hybrid — local + ephemeral' }] },
  // Gateways
  mcpgw: { id: 'mcpgw', group: 'gateway', t: 'MCP Gateway', d: 'broker to tools & integrations', what: 'The single chokepoint for all tool / MCP traffic. Checks the tool is approved and the caller entitled, applies policy & rate limits, injects credentials, audits every call.', dec: [{ q: 'Deployment?', opts: ['<b>Central shared gateway</b> — one policy point', '<b>Per-tenant</b> — stronger isolation'] }, { q: 'Credential handling?', opts: ['<b>Broker injects at call-time</b> — never in context', '<b>Short-lived scoped tokens</b> per session'] }], p: ['All tool traffic proxied — no direct connections', 'AuthZ + scope check + audit on every call'] },
  modelgw: { id: 'modelgw', group: 'gateway', t: 'Model Gateway', d: 'broker to model providers', what: 'The chokepoint for all LLM calls — routes by task complexity, applies prompt caching, fallback, rate limits and residency rules, and meters tokens for cost attribution.', dec: [{ q: 'Model strategy?', opts: ['<b>Frontier-only</b> — best quality', '<b>Tiered routing</b> — cheap model for simple steps', '<b>Self-hosted / BYO</b> — residency / air-gap'] }], p: ['Route by complexity to control cost', 'Prompt-cache stable context', 'Meter tokens here for attribution'] },
  // External
  landscape: { id: 'landscape', group: 'external', t: 'Internal Systems', d: 'Jira · GitHub · APIs · DBs', what: 'The systems of record the agent acts on, reached through the MCP Gateway — source control, issue trackers, wikis, internal services and databases.', dec: [{ q: 'Integration surface priority?', opts: ['<b>SCM + tracker first</b> (GitHub/GitLab + Jira)', '<b>+ internal APIs</b> as MCP servers', '<b>+ data stores</b> — read vs read-write'] }], p: ['Official APIs + webhooks', 'Least-privilege service accounts per system'] },
  web: { id: 'web', group: 'external', t: 'External Connections', d: 'web · search · docs', what: 'External web and search access, reached through the MCP Gateway — documentation, package registries, and general web search.', dec: [{ q: 'Web access posture?', opts: ['<b>None</b> — closed corpus only', '<b>Allowlisted domains</b>', '<b>Open search</b> with output filtering'] }], p: ['Filter fetched content for injection before use', 'Allowlist domains for sensitive environments'] },
  providers: { id: 'providers', group: 'gateway', t: 'Model Providers', d: 'frontier · self-hosted LLMs', what: 'The model providers that actually serve inference — frontier APIs (Bedrock / Anthropic) or self-hosted models — reached exclusively through the Model Gateway.', dec: [{ q: 'How are your model providers hosted?', opts: ['<b>Managed provider</b> (e.g. Bedrock, Anthropic API)', '<b>Self-hosted</b> for sensitive / air-gapped workloads', '<b>Multi-provider</b> for resilience'] }], p: ['Pin model versions; test before rollout', 'Route residency-sensitive traffic to compliant regions'], requirement: 'requirement:provider-hosting', answers: [{ value: 'managed', label: 'Managed provider (Bedrock / Anthropic API)' }, { value: 'self-hosted', label: 'Self-hosted (residency / air-gapped)' }, { value: 'multi-provider', label: 'Multi-provider (resilience)' }] },
  // Ops
  observability: { id: 'observability', group: 'ops', t: 'Observability & Audit', d: 'traces · evals · audit', what: 'End-to-end traces of every step and tool / model call, quality evals, and an immutable audit trail for compliance.', dec: [{ q: 'Audit requirements?', opts: ['<b>Immutable + tamper-evident</b> (regulated)', '<b>Standard logs</b> to SIEM'] }], p: ['Trace every step end-to-end', 'Immutable audit, exportable to SIEM'], requirement: 'requirement:outcome-observability', answers: [{ value: 'true', label: 'Correlate agent traces with Git/CI outcomes' }, { value: 'false', label: 'Basic telemetry only' }] },
  cost: { id: 'cost', group: 'ops', t: 'Cost Management', d: 'attribution · chargeback', what: 'Attributes spend to a user / team / repo, powers chargeback / showback, tracks budgets against quotas.', dec: [{ q: 'Cost model?', opts: ['<b>Showback</b> — visibility only', '<b>Chargeback</b> — bill teams', '<b>Hybrid</b> — showback + hard caps'] }], p: ['Attribute every dollar to an owner', 'Dashboards per team; alert on anomalies'] },
  token: { id: 'token', group: 'ops', t: 'Token Economics', d: 'metering · cache · right-sizing', what: 'The efficiency layer — token metering, prompt-cache hit rates, model right-sizing, and cost-per-task optimization.', dec: [{ q: 'Optimization levers?', opts: ['<b>Tiered model routing</b> — cheap for simple steps', '<b>Prompt caching</b> — reuse stable context', '<b>Context compaction</b> — fewer tokens per turn'] }], p: ['Track cost-per-task, not just raw tokens', 'Maximize prompt-cache hit rate'] },
};

export interface WireDef { source: string; target: string; kind: 'req' | 'sup' | 'gov'; label?: string }
export const WIRES: WireDef[] = [
  { source: 'identity', target: 'ide', kind: 'gov', label: 'authenticate' },
  { source: 'identity', target: 'harness', kind: 'gov', label: 'policy' },
  { source: 'identity', target: 'mcpgw', kind: 'gov', label: 'tool access' },
  { source: 'registry', target: 'harness', kind: 'sup', label: 'loads' },
  { source: 'ide', target: 'harness', kind: 'req', label: 'request' },
  { source: 'harness', target: 'exec', kind: 'req', label: 'runs code' },
  { source: 'harness', target: 'mcpgw', kind: 'req', label: 'tool calls' },
  { source: 'harness', target: 'modelgw', kind: 'req', label: 'model calls' },
  { source: 'mcpgw', target: 'landscape', kind: 'req' },
  { source: 'mcpgw', target: 'web', kind: 'req' },
  { source: 'modelgw', target: 'providers', kind: 'req' },
];

// ---- React Flow layout (approved arrangement) ----
// governance spine left · surfaces top · harness heart center · registry right
// flanking the harness · execution + gateways + external stacked center · ops
// band spanning the bottom. Coordinates are hand-tuned against screenshots.
const NW = 210;          // standard node width
const REG_X = 800;       // registry column — kept near the harness, not stranded
export const LAYOUT: Record<string, { x: number; y: number; w?: number; h?: number }> = {
  // surfaces row (top, 4 across) — start below the group tag
  ide: { x: 300, y: 76 }, cli: { x: 300, y: 150 }, chat: { x: 540, y: 76 }, ci: { x: 540, y: 150 },
  // governance spine (left) — evenly spaced down a frame sized to fit them
  identity: { x: 24, y: 76 }, guardrails: { x: 24, y: 182 }, quota: { x: 24, y: 292 },
  // harness heart (center)
  harness: { x: 320, y: 268, w: 400, h: 110 },
  // registry (right of harness, stacked) — start below the group tag
  registry: { x: REG_X, y: 76 }, tools: { x: REG_X, y: 148 }, skills: { x: REG_X, y: 220 }, subagents: { x: REG_X, y: 292 }, mcpservers: { x: REG_X, y: 364 },
  // execution (below harness) — taller so the description isn't clipped
  exec: { x: 415, y: 430, w: 210, h: 74 },
  // gateways
  mcpgw: { x: 300, y: 560 }, modelgw: { x: 560, y: 560 },
  // external (below gateways, 3 across)
  landscape: { x: 260, y: 690 }, web: { x: 500, y: 690 }, providers: { x: 740, y: 690 },
  // ops band (bottom, 3 across)
  observability: { x: 150, y: 838 }, cost: { x: 390, y: 838 }, token: { x: 630, y: 838 },
};

// Background group frames. Sized to enclose their members with even padding.
export const GROUP_LAYOUT = [
  { id: 'g-gov', label: 'Governance', group: 'access', x: 0, y: 40, w: 258, h: 380 },
  { id: 'g-surf', label: 'Surfaces', group: 'surface', x: 276, y: 40, w: 498, h: 190 },
  { id: 'g-reg', label: 'Registry', group: 'registry', x: REG_X - 24, y: 40, w: 258, h: 400 },
  { id: 'g-ops', label: 'Operations', group: 'ops', x: 126, y: 810, w: 738, h: 128 },
];
void NW;
