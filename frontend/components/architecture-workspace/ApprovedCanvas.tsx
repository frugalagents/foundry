'use client';

// Faithful port of the approved coding-agent-platform reference diagram.
// Scoped under #pac so its dark theme does not collide with the app's Tailwind
// light theme. The block layout, per-block architecture decisions (the
// discovery questions), and connector wiring reproduce the approved HTML. Live
// engine state is overlaid: blocks the projection has activated are marked, and
// the model-provider decision is answerable inline to drive the real engine.

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type {
  ArchitectureWorkspaceProjection,
  EvidenceClaim,
  RequirementValue,
} from '@/lib/architecture-workspace';

const C: Record<string, string> = {
  surface: '#b98cf0', registry: '#2dd4bf', harness: '#37dd7d', exec: '#fb7185',
  gateway: '#4cc4f5', external: '#8b98ab', access: '#7d9bff', ops: '#f0a850',
};
const REQ = '#4cc4f5', SUP = '#2dd4bf', GOV = '#7d9bff';

interface Decision { q: string; opts: string[] }
interface Block {
  t: string; d: string; what: string; dec: Decision[]; p: string[];
  // requirement this block answers (only the model-provider slice is live)
  requirement?: string;
  answers?: { value: string; label: string }[];
}
type Group = Record<string, Block>;

const M: Record<string, Group> = {
  surface: {
    ide: { t: 'IDE', d: 'in-editor agent', what: 'The agent inside VS Code / JetBrains — inline edits, diffs, side-panel chat.', dec: [{ q: 'Where does the harness run for the IDE?', opts: ['<b>Local</b> — low latency, uses local files', '<b>Remote / managed</b> — central control & audit', '<b>Hybrid</b> — UI local, execution remote'] }], p: ['One harness core behind every surface', 'Review-diff-then-apply as the safe default'] },
    cli: { t: 'CLI / Terminal', d: 'interactive + headless', what: 'Terminal surface for power users and scripting — same harness, non-interactive mode for automation.', dec: [{ q: 'Primary CLI mode?', opts: ['<b>Interactive</b> — dev in the loop', '<b>Headless</b> — piped into scripts, JSON output'] }], p: ['Headless mode must be fail-safe', 'Hard token / time budget per invocation'] },
    chat: { t: 'Chat / PR Bot', d: 'Slack · Teams · PR', what: 'Async surface to kick off tasks, review PRs, and approve actions from where teams already talk.', dec: [{ q: 'How autonomous on PRs?', opts: ['<b>Advisory</b> — comments only', '<b>Gating</b> — can block merge', '<b>Author</b> — opens its own PRs'] }], p: ['Every action links to an audit ID', 'Long jobs run async, notify on completion'] },
    ci: { t: 'CI/CD Trigger', d: 'agent in the pipeline', what: 'Agent invoked by pipelines — fix builds, bump dependencies, generate tests on event or schedule.', dec: [{ q: 'Trust in the pipeline?', opts: ['<b>Suggest</b> — opens PR for humans', '<b>Act</b> — commits within guardrails'] }], p: ['Budget-capped runs', 'No prod actions without approval'] },
  },
  access: {
    identity: { t: 'Identity & Access', d: 'SSO · AuthN/Z · entitlements', what: 'Federates to your corporate IdP and authenticates every request before it reaches the harness — and governs egress: which identity may reach which enterprise tool through the MCP Gateway.', dec: [{ q: 'Identity source?', opts: ['<b>Corporate IdP</b> (Okta / Entra) via OIDC/SAML', '<b>SCIM</b> auto-provisioning of teams'] }, { q: 'Agent acts as whom?', opts: ['<b>The developer</b> — inherits their access', '<b>Scoped service identity</b> — least privilege'] }], p: ['Federate — no local accounts', 'Same identity governs ingress AND tool egress', 'Short-lived, scoped tokens'] },
    guardrails: {
      t: 'Guardrails & Policy', d: 'filtering · approvals · DLP', what: 'Screens each prompt on the way in and each output on the way back — blocks or redacts policy violations, drives human-approval gates, keeps secrets / PII out of the model.', dec: [{ q: 'On violation?', opts: ['<b>Block</b>', '<b>Redact</b> & continue', '<b>Warn</b> & log'] }], p: ['Default-deny on state-changing actions', 'Secrets never enter the prompt; scan I/O for PII', 'One policy engine, every surface — no bypass'],
      requirement: 'requirement:action-approval',
      answers: [{ value: 'true', label: 'Require risk-based human approval' }, { value: 'false', label: 'No human-in-the-loop gate' }],
    },
    quota: { t: 'Quota & Rate Limits', d: 'throttling · seats · spend caps', what: 'Enforces limits at the edge before any model or tool spend — per-user and per-team rate limits, concurrency, seat entitlements and hard spend caps.', dec: [{ q: 'Limit model?', opts: ['<b>Per-user + per-team</b> rate limits', '<b>Concurrency caps</b> — bound parallel agents', '<b>Hard spend ceiling</b> per team'] }], p: ['Enforce quotas before spend, at the edge', 'Alert at 80%, cap at 100%'] },
  },
  registry: {
    registry: { t: 'Registry / Catalog', d: 'approved building blocks', what: 'The signed, versioned source of truth for everything the harness may load — tools, plugins, skills, subagents, MCP servers — plus who is entitled to use each.', dec: [{ q: 'Catalog scope?', opts: ['<b>Org-wide</b> — one source of truth', '<b>Per-team</b> — autonomy, more sprawl', '<b>Federated</b> — org base + team extensions'] }, { q: 'Publish workflow?', opts: ['<b>Self-serve + automated scan</b> — fast', '<b>Security review gate</b> — safer', '<b>Risk-tiered</b> — read-only auto, write reviewed'] }], p: ['Nothing loads unless published & signed', 'Version-pin + central kill-switch on compromise'] },
    tools: { t: 'Tools & Plugins', d: 'file · shell · git · search', what: "The capabilities the harness invokes directly — file edit, shell, git, search — and plugins that extend them.", dec: [{ q: 'Tool granting model?', opts: ['<b>Allowlist per agent</b> — explicit', '<b>Scope-based</b> — role decides', '<b>Arg-level policy</b> on sensitive tools'] }], p: ['Read and write tools separated & separately entitled', 'Least capability by default'] },
    skills: { t: 'Skills', d: 'reusable procedures', what: "Packaged know-how the agent loads on demand — 'how we do migrations', 'our PR checklist' — authored once, shared across agents.", dec: [{ q: 'Skill governance?', opts: ['<b>Open</b> — anyone contributes', '<b>Curated</b> — reviewed & signed', '<b>Risk-tiered</b> — scanned for injection'] }], p: ['Signed, version-pinned artifacts', 'Loaded on demand to save context'] },
    subagents: { t: 'Subagents', d: 'delegated specialists', what: 'Purpose-built agents the main harness can spawn for scoped work (explore, review, migrate) — each with its own tools and limits.', dec: [{ q: 'Delegation policy?', opts: ['<b>Fixed roster</b> — only approved subagents', '<b>Depth / fan-out caps</b> — stop runaway trees', '<b>Budget caps</b> per subagent'] }], p: ['Subagent scope ≤ parent (never expanded)', 'Caps on recursion, fan-out, and budget'] },
    mcpservers: { t: 'MCP Servers', d: 'integration connectors', what: 'The MCP servers the harness may connect to — each wrapping an enterprise system (Jira, GitHub, internal APIs). Reached at runtime through the MCP Gateway.', dec: [{ q: 'Who hosts MCP servers?', opts: ['<b>Vendor servers</b> for common systems', '<b>Custom</b> for proprietary internal APIs', '<b>Mix</b> behind the gateway'] }], p: ['Every server registered, signed, versioned', 'Reached only via the gateway — never direct'] },
  },
  harness: {
    loop: { t: 'Agent Loop', d: 'reason ▸ act ▸ observe', what: 'The core cycle: read context, plan, call the model, invoke a tool, observe the result, repeat — until the goal is met or a checkpoint stops it.', dec: [{ q: 'Autonomy per task?', opts: ['<b>Step cap</b> before a human check', '<b>Plan-first</b> — approve the plan, then run', '<b>Full auto</b> within guardrails'] }], p: ['Deterministic control flow around the model', 'Interruptible & steerable mid-task'] },
    perms: { t: 'Permission Engine', d: 'allow · deny · ask', what: 'Decides, for every tool call, whether to run it, block it, or ask a human. Hooks (pre / post tool-use) plug in here as the concrete enforcement point.', dec: [{ q: 'Default posture?', opts: ['<b>Ask on writes</b> (safe default)', '<b>Auto-approve in sandbox</b>, gate external effects', '<b>Full auto</b> in CI / isolated envs'] }], p: ['Explicit deny wins over allow', 'State-changing actions fail closed'] },
    context: { t: 'Context & Memory', d: 'repo · rules · compaction', what: 'How the agent sees your code — pulls the right files, symbols, history and standards into the working set, and compacts as it fills.', dec: [{ q: 'Context sourcing?', opts: ['<b>On-demand read + grep</b> — always fresh', '<b>Index / code graph</b> — fast recall', '<b>Retrieval (RAG)</b> — large / cross-repo'] }], p: ['Compact aggressively; retrieve on demand', "Never mix another tenant's context in"] },
    runtime: {
      t: 'Tool Runtime', d: 'invokes tools · subagents', what: 'Executes the harness decisions — runs built-in tools, loads skills, spawns subagents, and dispatches MCP / model calls out through the gateways.', dec: [{ q: 'Tool call routing?', opts: ['<b>All via gateways</b> — one policy point', '<b>Local tools direct</b>, external via gateway'] }], p: ['Bind to gateways, never directly to tools/models', 'Parallelize read-only calls; serialize writes'],
      requirement: 'requirement:multi-agent',
      answers: [{ value: 'true', label: 'Coordinate multiple agents (adds supervisor)' }, { value: 'false', label: 'Single agent only' }],
    },
  },
  exec: {
    exec: {
      t: 'Execution Environment', d: 'where the agent runs code', what: "The environment the harness connects to for running commands, tests, and builds — local machine, built-in sandbox, or a remote ephemeral workspace.", dec: [{ q: 'Network egress?', opts: ['<b>Blocked</b> — most secure', '<b>Allowlist</b> — package registries only', '<b>Open</b> — riskier'] }], p: ['Isolate, cap resources, tear down clean', 'Deny egress by default; allowlist explicitly'],
      requirement: 'requirement:execution-placement',
      answers: [
        { value: 'local', label: 'Local machine (developer endpoint)' },
        { value: 'vendor-managed', label: 'Vendor-managed ephemeral runtime' },
        { value: 'customer-managed', label: 'Customer-managed container runtime' },
        { value: 'hybrid', label: 'Hybrid — local + ephemeral' },
      ],
    },
  },
  gateway: {
    mcpgw: { t: 'MCP Gateway', d: 'broker to tools & integrations', what: 'The single chokepoint for all tool / MCP traffic. Checks the tool is approved and the caller entitled, applies policy & rate limits, injects credentials, audits every call.', dec: [{ q: 'Deployment?', opts: ['<b>Central shared gateway</b> — one policy point', '<b>Per-tenant</b> — stronger isolation'] }, { q: 'Credential handling?', opts: ['<b>Broker injects at call-time</b> — never in context', '<b>Short-lived scoped tokens</b> per session'] }], p: ['All tool traffic proxied — no direct connections', 'AuthZ + scope check + audit on every call'] },
    modelgw: { t: 'Model Gateway', d: 'broker to model providers', what: 'The chokepoint for all LLM calls — routes by task complexity, applies prompt caching, fallback, rate limits and residency rules, and meters tokens for cost attribution.', dec: [{ q: 'Model strategy?', opts: ['<b>Frontier-only</b> — best quality', '<b>Tiered routing</b> — cheap model for simple steps', '<b>Self-hosted / BYO</b> — residency / air-gap'] }], p: ['Route by complexity to control cost', 'Prompt-cache stable context', 'Meter tokens here for attribution'] },
  },
  external: {
    landscape: { t: 'Internal Systems', d: 'Jira · GitHub · APIs · DBs', what: 'The systems of record the agent acts on, reached through the MCP Gateway — source control, issue trackers, wikis, internal services and databases.', dec: [{ q: 'Integration surface priority?', opts: ['<b>SCM + tracker first</b> (GitHub/GitLab + Jira)', '<b>+ internal APIs</b> as MCP servers', '<b>+ data stores</b> — read vs read-write'] }], p: ['Official APIs + webhooks', 'Least-privilege service accounts per system'] },
    web: { t: 'External Connections', d: 'web · search · docs', what: 'External web and search access, reached through the MCP Gateway — documentation, package registries, and general web search.', dec: [{ q: 'Web access posture?', opts: ['<b>None</b> — closed corpus only', '<b>Allowlisted domains</b>', '<b>Open search</b> with output filtering'] }], p: ['Filter fetched content for injection before use', 'Allowlist domains for sensitive environments'] },
    providers: {
      t: 'Model Providers', d: 'frontier · self-hosted LLMs',
      what: 'The model providers that actually serve inference — frontier APIs (Bedrock / Anthropic) or self-hosted models — reached exclusively through the Model Gateway.',
      dec: [{ q: 'How are your model providers hosted?', opts: ['<b>Managed provider</b> (e.g. Bedrock, Anthropic API)', '<b>Self-hosted</b> for sensitive / air-gapped workloads', '<b>Multi-provider</b> for resilience'] }],
      p: ['Pin model versions; test before rollout', 'Route residency-sensitive traffic to compliant regions'],
      requirement: 'requirement:provider-hosting',
      answers: [
        { value: 'managed', label: 'Managed provider (Bedrock / Anthropic API)' },
        { value: 'self-hosted', label: 'Self-hosted (residency / air-gapped)' },
        { value: 'multi-provider', label: 'Multi-provider (resilience)' },
      ],
    },
  },
  ops: {
    observability: {
      t: 'Observability & Audit', d: 'traces · evals · audit', what: 'End-to-end traces of every step and tool / model call, quality evals, and an immutable audit trail for compliance.', dec: [{ q: 'Audit requirements?', opts: ['<b>Immutable + tamper-evident</b> (regulated)', '<b>Standard logs</b> to SIEM'] }], p: ['Trace every step end-to-end', 'Immutable audit, exportable to SIEM'],
      requirement: 'requirement:outcome-observability',
      answers: [{ value: 'true', label: 'Correlate agent traces with Git/CI outcomes' }, { value: 'false', label: 'Basic telemetry only' }],
    },
    cost: { t: 'Cost Management', d: 'attribution · chargeback', what: 'Attributes spend to a user / team / repo, powers chargeback / showback, tracks budgets against quotas.', dec: [{ q: 'Cost model?', opts: ['<b>Showback</b> — visibility only', '<b>Chargeback</b> — bill teams', '<b>Hybrid</b> — showback + hard caps'] }], p: ['Attribute every dollar to an owner', 'Dashboards per team; alert on anomalies'] },
    token: { t: 'Token Economics', d: 'metering · cache · right-sizing', what: 'The efficiency layer — token metering, prompt-cache hit rates, model right-sizing, and cost-per-task optimization.', dec: [{ q: 'Optimization levers?', opts: ['<b>Tiered model routing</b> — cheap for simple steps', '<b>Prompt caching</b> — reuse stable context', '<b>Context compaction</b> — fewer tokens per turn'] }], p: ['Track cost-per-task, not just raw tokens', 'Maximize prompt-cache hit rate'] },
  },
};

const PHASE: Record<string, string> = {
  surface: 'Surface', access: 'Governance · control plane', registry: 'Registry · building blocks',
  harness: 'Harness core', exec: 'Execution', gateway: 'Gateway', external: 'External system',
  ops: 'Operations & economics',
};

// engine component ids that, when present as 'added', light up a block
const ACTIVE_MAP: Record<string, string[]> = {
  providers: ['component:managed-model-provider', 'component:self-hosted-inference', 'component:model-router'],
  runtime: ['component:multi-agent-supervisor'],
  guardrails: ['component:human-approval'],
  observability: ['component:economics-ledger', 'component:outcome-correlator'],
  exec: ['component:local-runtime', 'component:ephemeral-runtime', 'component:container-runtime'],
};

interface BlueprintContext { name: string; description: string; type: string }

const TYPE_LABEL: Record<string, string> = {
  coding: 'Agentic Coding Platform',
  internal: 'Internal-Facing Platform',
  'customer-facing': 'Customer-Facing Agentic Platform',
  saas: 'SaaS Decomposition',
  marketplace: 'Marketplace',
};

interface Props {
  projection: ArchitectureWorkspaceProjection;
  blueprint?: BlueprintContext | null;
  onAnswer?: (requirementId: string, value: RequirementValue) => Promise<void> | void;
  applying?: boolean;
}

const ALL: Record<string, Block & { phase: string; id: string }> = {};
for (const g of Object.keys(M)) for (const id of Object.keys(M[g])) ALL[id] = { ...M[g][id], phase: g, id };

export function ApprovedCanvas({ projection, blueprint, onAnswer, applying }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const diagramRef = useRef<HTMLDivElement>(null);
  const planeRef = useRef<HTMLDivElement>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [paths, setPaths] = useState<{ id: string; d: string; stroke: string; dash?: string; label?: string; lx: number; ly: number }[]>([]);

  const activeComponentIds = useMemo(() => {
    const set = new Set<string>();
    for (const plane of projection.architecture.planes)
      for (const c of plane.components) if (c.status === 'added') set.add(c.id);
    return set;
  }, [projection]);

  const byClaimId = useMemo(() => {
    const m = new Map<string, EvidenceClaim>();
    for (const e of projection.evidence ?? []) m.set(e.claim_id, e);
    return m;
  }, [projection]);

  // Evidence attached to the decisions that fired for a given requirement.
  const evidenceForRequirement = useCallback((requirementId?: string): EvidenceClaim[] => {
    if (!requirementId) return [];
    const claims: EvidenceClaim[] = [];
    for (const t of projection.decision_trace) {
      if (t.requirement_ids.includes(requirementId)) {
        for (const cid of t.evidence_claim_ids ?? []) {
          const c = byClaimId.get(cid);
          if (c && !claims.includes(c)) claims.push(c);
        }
      }
    }
    return claims;
  }, [projection, byClaimId]);

  const isActive = (id: string) =>
    (ACTIVE_MAP[id] ?? []).some((cid) => activeComponentIds.has(cid));

  // ---- connector wiring (from the approved diagram) ----
  const WIRES: [string, 'top' | 'bottom' | 'left' | 'right', string, 'top' | 'bottom' | 'left' | 'right', 'req' | 'sup' | 'gov', string][] = useMemo(() => [
    ['n-access', 'right', 'n-surfaces', 'left', 'gov', 'authenticate'],
    ['n-access', 'right', 'n-harness', 'left', 'gov', 'policy'],
    ['n-access', 'right', 'n-gateways', 'left', 'gov', 'tool access'],
    ['n-registry', 'left', 'n-harness', 'right', 'sup', 'loads'],
    ['n-surfaces', 'bottom', 'n-harness', 'top', 'req', 'request'],
    ['n-harness', 'bottom', 'n-exec', 'top', 'req', 'runs code'],
    ['n-harness', 'bottom', 'n-gateways', 'top', 'req', 'tool + model'],
    ['n-gateways', 'bottom', 'n-external', 'top', 'req', ''],
  ], []);

  const recompute = useCallback(() => {
    // Measure against the diagram container — the SVG's positioning parent —
    // so wire endpoints share the SVG's coordinate origin (not the outer root,
    // which would offset every line by the header + padding).
    const host = diagramRef.current;
    if (!host) return;
    const hb = host.getBoundingClientRect();
    const anchor = (sel: string, side: string) => {
      const el = host.querySelector(`[data-node="${sel}"]`) as HTMLElement | null;
      if (!el) return null;
      const r = el.getBoundingClientRect();
      const x = r.left - hb.left, y = r.top - hb.top;
      if (side === 'top') return { x: x + r.width / 2, y };
      if (side === 'bottom') return { x: x + r.width / 2, y: y + r.height };
      if (side === 'left') return { x, y: y + r.height / 2 };
      return { x: x + r.width, y: y + r.height / 2 };
    };
    const next: typeof paths = [];
    WIRES.forEach(([fn, fs, tn, ts, type, label], i) => {
      const a = anchor(fn, fs), b = anchor(tn, ts);
      if (!a || !b) return;
      let d: string;
      if ((fs === 'right' && ts === 'left') || (fs === 'left' && ts === 'right')) {
        const dx = Math.max(26, Math.abs(b.x - a.x) * 0.42);
        d = `M ${a.x} ${a.y} C ${a.x + (fs === 'right' ? dx : -dx)} ${a.y}, ${b.x + (ts === 'left' ? -dx : dx)} ${b.y}, ${b.x} ${b.y}`;
      } else {
        const dy = Math.max(20, Math.abs(b.y - a.y) * 0.5);
        d = `M ${a.x} ${a.y} C ${a.x} ${a.y + dy}, ${b.x} ${b.y - dy}, ${b.x} ${b.y}`;
      }
      const stroke = type === 'sup' ? SUP : type === 'gov' ? GOV : REQ;
      const dash = type === 'sup' ? '6 5' : type === 'gov' ? '3 5' : undefined;
      next.push({ id: `w${i}`, d, stroke, dash, label, lx: (a.x + b.x) / 2, ly: (a.y + b.y) / 2 });
    });
    setPaths(next);
  }, [WIRES]);

  useLayoutEffect(() => { recompute(); }, [recompute, projection]);
  useEffect(() => {
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => recompute());
    if (planeRef.current) ro.observe(planeRef.current);
    window.addEventListener('resize', recompute);
    return () => { ro.disconnect(); window.removeEventListener('resize', recompute); };
  }, [recompute]);

  const sel = selected ? ALL[selected] : null;
  const selValue = sel?.requirement
    ? projection.requirements.find((r) => r.id === sel.requirement)?.value
    : undefined;
  // engine requirements are typed; string answers like "true"/"false" must be
  // coerced to the boolean the engine expects, and compared the same way.
  const coerce = (v: string): RequirementValue =>
    v === 'true' ? true : v === 'false' ? false : v;
  const selClaims = evidenceForRequirement(sel?.requirement);

  return (
    <div id="pac" ref={hostRef}>
      <PacStyles />
      <div className="pac-head">
        <div className="pac-brand">
          <div className="pac-mark" />
          <div>
            <h1>{blueprint?.name ?? 'Coding Agent Platform'}</h1>
            <p>
              {blueprint
                ? <>{TYPE_LABEL[blueprint.type] ?? blueprint.type}{blueprint.description ? ` · ${blueprint.description}` : ''}</>
                : 'Logical reference architecture · click any block for its design decisions'}
            </p>
          </div>
        </div>
        <div className="pac-legend">
          <span><i className="ln req" />runtime call</span>
          <span><i className="ln sup" />loads / composes</span>
          <span><i className="ln gov" />access &amp; policy</span>
        </div>
      </div>

      <div className="pac-main">
        <div className="pac-stage">
          <div className="pac-diagram" ref={diagramRef}>
            <svg className="pac-wires" aria-hidden>
              <defs>
                {[['req', REQ], ['sup', SUP], ['gov', GOV]].map(([k, col]) => (
                  <marker key={k} id={`pac-ar-${k}`} markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto">
                    <path d="M1 1 L8 4.5 L1 8" fill="none" stroke={col} strokeWidth="1.6" strokeLinecap="round" />
                  </marker>
                ))}
              </defs>
              {paths.map((p) => (
                <g key={p.id}>
                  <path d={p.d} stroke={p.stroke} strokeWidth={p.dash ? 1.6 : 2} strokeDasharray={p.dash}
                    fill="none" markerEnd={`url(#pac-ar-${p.stroke === SUP ? 'sup' : p.stroke === GOV ? 'gov' : 'req'})`}
                    opacity={p.stroke === GOV ? 0.4 : 0.62} />
                  {p.label && (
                    <>
                      <rect x={p.lx - (p.label.length * 3 + 5)} y={p.ly - 9} width={p.label.length * 6 + 10} height={15} rx={4} className="pac-wlabel-bg" />
                      <text x={p.lx} y={p.ly + 2} textAnchor="middle" className="pac-wlabel">{p.label}</text>
                    </>
                  )}
                </g>
              ))}
            </svg>

            <div className="pac-plane" ref={planeRef}>
              {/* GOVERNANCE spine (left) */}
              <div className="pac-node a-gov" data-node="n-access">
                <div className="grp-hd"><span className="gtag" style={{ background: C.access, color: '#0a1024' }}>Governance</span><span className="gt">Control plane</span></div>
                <div className="spine-body">{['identity', 'guardrails', 'quota'].map((id) => <Card key={id} id={id} onClick={setSelected} selected={selected} active={isActive(id)} />)}</div>
              </div>

              {/* SURFACES (top) */}
              <div className="pac-node a-surfaces" data-node="n-surfaces">
                <div className="grp-hd"><span className="gtag" style={{ background: C.surface }}>Surfaces</span><span className="gt">Developer surfaces</span><span className="gs">how devs engage</span></div>
                <div className="grid4">{['ide', 'cli', 'chat', 'ci'].map((id) => <Card key={id} id={id} onClick={setSelected} selected={selected} active={isActive(id)} />)}</div>
              </div>

              {/* HARNESS (heart) */}
              <div className="pac-node a-harness" data-node="n-harness">
                <div className="harness-title"><span className="gtag">Harness</span><span className="ht">Coding Agent Harness</span><span className="hs">the heart</span></div>
                <div className="harness-sub">Loads its building blocks from the Registry, runs code in the Execution env, and reaches the outside world only through the Gateways.</div>
                <div className="harness-core">
                  <div className="mini">◇ orchestration core</div>
                  <div className="core-grid">
                    {['loop', 'perms', 'context', 'runtime'].map((id) => (
                      <button key={id} type="button" className={`core-cell${selected === id ? ' sel' : ''}`} onClick={() => setSelected(id)}>
                        <div className="cct">{ALL[id].t}</div><div className="ccd">{ALL[id].d}</div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* REGISTRY (right) */}
              <div className="pac-node a-registry" data-node="n-registry">
                <div className="grp-hd"><span className="gtag" style={{ background: C.registry, color: '#062019' }}>Registry</span><span className="gt">Building blocks</span></div>
                <div className="spine-body">{['registry', 'tools', 'skills', 'subagents', 'mcpservers'].map((id) => <Card key={id} id={id} onClick={setSelected} selected={selected} active={isActive(id)} />)}</div>
              </div>

              {/* EXECUTION */}
              <div className="pac-node a-exec" data-node="n-exec">
                <div className="grp-hd"><span className="gtag" style={{ background: C.exec }}>Execution</span><span className="gt">Execution Env</span></div>
                <div className="single"><Card id="exec" onClick={setSelected} selected={selected} active={isActive('exec')} /></div>
              </div>

              {/* GATEWAYS */}
              <div className="pac-node a-gateways" data-node="n-gateways">
                <div className="grp-hd"><span className="gtag" style={{ background: C.gateway, color: '#04141d' }}>Gateways</span><span className="gt">Egress gateways</span><span className="gs">chokepoints</span></div>
                <div className="gw-wrap">
                  <Card id="mcpgw" onClick={setSelected} selected={selected} active={isActive('mcpgw')} />
                  <Card id="modelgw" onClick={setSelected} selected={selected} active={isActive('modelgw')} />
                </div>
              </div>

              {/* EXTERNAL (3 boxes) */}
              <div className="a-external" data-node="n-external">
                <div className="ext-wrap">
                  {(['landscape', 'web', 'providers'] as const).map((id) => (
                    <div className="extbox" key={id} style={{ ['--ac' as string]: id === 'providers' ? C.gateway : C.external }}>
                      <div className="exbh">{id === 'landscape' ? 'Internal Systems' : id === 'web' ? 'External Connections' : 'Model Providers'}</div>
                      <Card id={id} onClick={setSelected} selected={selected} active={isActive(id)} accent={id === 'providers' ? C.gateway : C.external} />
                    </div>
                  ))}
                </div>
              </div>

              {/* OPS band (bottom) */}
              <div className="pac-node a-ops" data-node="n-ops">
                <div className="grp-hd"><span className="gtag" style={{ background: C.ops, color: '#1c1204' }}>Operations</span><span className="gt">Observability, cost &amp; token economics</span><span className="gs">spans every layer</span></div>
                <div className="rowh">{['observability', 'cost', 'token'].map((id) => <Card key={id} id={id} onClick={setSelected} selected={selected} active={isActive(id)} />)}</div>
              </div>
            </div>
          </div>
        </div>

        {/* DETAIL PANEL — architecture decisions (questions) */}
        <aside className="pac-aside">
          {!sel ? (
            <div>
              {blueprint && (
                <div className="pac-bp">
                  <span className="pac-bp-kicker">Blueprint</span>
                  <h2>{blueprint.name}</h2>
                  <span className="pac-bp-type">{TYPE_LABEL[blueprint.type] ?? blueprint.type}</span>
                  {blueprint.description && <p className="pac-bp-desc">{blueprint.description}</p>}
                </div>
              )}
              <div className="ap-empty">
                <div className="ic">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#7d9bff" strokeWidth="1.6"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" opacity=".6" /></svg>
                </div>
                <h4>Answer the discovery questions</h4>
                <p>Click any block on the canvas to see the <b>questions for this blueprint</b> — as you answer, the architecture changes to fit.</p>
              </div>
            </div>
          ) : (
            <div>
              <div className="ap-hd" style={pacVars(C[sel.phase])}>
                <span className="ap-kicker"><i style={{ width: 7, height: 7, borderRadius: 2, background: C[sel.phase], display: 'inline-block' }} />{PHASE[sel.phase]}</span>
                <h2>{sel.t}</h2>
                <p>{sel.what}</p>
              </div>

              {sel.requirement && sel.answers && (
                <div className="ap-sec" style={pacVars(C[sel.phase])}>
                  <h3><span className="bar" />Answer this decision <span className="pac-live">live</span></h3>
                  <div className="pac-answers">
                    {sel.answers.map((a) => (
                      <button key={a.value} type="button" disabled={applying}
                        className={`pac-answer${selValue === coerce(a.value) ? ' on' : ''}`}
                        onClick={() => onAnswer?.(sel.requirement!, coerce(a.value))}>
                        <span className="dot" />{a.label}
                      </button>
                    ))}
                  </div>
                  {applying && <p className="pac-current">Updating architecture…</p>}
                  {!applying && selValue != null && <p className="pac-current">Current: <b>{String(selValue)}</b> — the diagram and evidence reflect this.</p>}
                  {selClaims.length > 0 && (
                    <div className="pac-evidence">
                      {selClaims.map((c) => (
                        <div className="pac-claim" key={c.claim_id}>
                          <p>{c.statement}</p>
                          <div className="src">
                            {c.source_title ?? c.source_id} · {c.source_locator}
                            {c.source_uri && <a href={c.source_uri} target="_blank" rel="noreferrer">source ↗</a>}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="ap-sec" style={pacVars(C[sel.phase])}>
                <h3><span className="bar" />Architecture decisions</h3>
                {sel.dec.map((d, i) => (
                  <div className="dec" key={i}>
                    <div className="q">{d.q}</div>
                    {d.opts.map((o, j) => (
                      <div className="opt" key={j}><span className="k">▸</span><span dangerouslySetInnerHTML={{ __html: o }} /></div>
                    ))}
                  </div>
                ))}
              </div>

              <div className="ap-sec" style={pacVars(C[sel.phase])}>
                <h3><span className="bar" />Best practices</h3>
                <ul className="plist">{sel.p.map((x, i) => <li key={i}>{x}</li>)}</ul>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function pacVars(col: string): React.CSSProperties {
  return { ['--k-fg' as string]: col, ['--k-bg' as string]: `${col}18`, ['--k-bd' as string]: `${col}44` };
}

function Card({ id, onClick, selected, active, accent }: {
  id: string; onClick: (id: string) => void; selected: string | null; active?: boolean; accent?: string;
}) {
  const b = ALL[id];
  const ac = accent ?? C[b.phase];
  return (
    <button type="button" className={`pac-card${selected === id ? ' sel' : ''}${active ? ' active' : ''}`}
      style={{ ['--ac' as string]: ac }} onClick={() => onClick(id)}>
      <div className="ct">{b.t}{active && <span className="pac-badge">active</span>}{b.requirement && <span className="pac-q">?</span>}</div>
      <div className="cd">{b.d}</div>
    </button>
  );
}

function PacStyles() {
  return (
    <style>{`
#pac{--bg:#0e1116;--bg-soft:#12161d;--card:#171d27;--card-h:#1d2530;--line:#242e3b;--line-soft:#1c2531;--ink:#e6e9ef;--ink-dim:#a7b2c2;--muted:#7c8899;--muted2:#556072;
  --font:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;--mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  background:radial-gradient(1000px 560px at 62% -10%,#1a35601c,transparent),radial-gradient(760px 520px at 100% 110%,#f0a8500a,transparent),var(--bg);
  color:var(--ink);font:14px/1.55 var(--font);-webkit-font-smoothing:antialiased;letter-spacing:.1px;display:flex;flex-direction:column;min-height:100vh;position:relative}
#pac .pac-main{min-height:0}
#pac *{box-sizing:border-box}
#pac .pac-head{padding:14px 24px;border-bottom:1px solid var(--line-soft);display:flex;align-items:center;gap:16px;background:linear-gradient(180deg,#0f131a,#0e1116)}
#pac .pac-brand{display:flex;align-items:center;gap:12px}
#pac .pac-mark{width:32px;height:32px;border-radius:9px;flex-shrink:0;background:conic-gradient(from 210deg,#37dd7d,#4cc4f5,#7d9bff,#b98cf0,#37dd7d);display:grid;place-items:center;box-shadow:0 0 0 1px #ffffff12}
#pac .pac-mark::after{content:"";width:12px;height:12px;border-radius:4px;background:var(--bg)}
#pac .pac-brand h1{font-size:15.5px;margin:0;font-weight:650;letter-spacing:-.15px}
#pac .pac-brand p{margin:1px 0 0;font-size:11px;color:var(--muted)}
#pac .pac-legend{margin-left:auto;display:flex;gap:13px;font-size:10.5px;color:var(--muted);align-items:center}
#pac .pac-legend span{display:flex;align-items:center;gap:6px}
#pac .pac-legend .ln{width:20px;height:0;border-top:2px solid #4cc4f5}
#pac .pac-legend .ln.sup{border-top:2px dashed #2dd4bf}
#pac .pac-legend .ln.gov{border-top:2px dashed #7d9bff}
#pac .pac-main{flex:1;display:flex;align-items:flex-start}
#pac .pac-stage{flex:1;padding:30px;min-width:0}
#pac .pac-aside{width:412px;border-left:1px solid var(--line-soft);background:var(--bg-soft);flex-shrink:0;align-self:stretch;position:sticky;top:0;max-height:100vh;overflow:auto}
#pac .pac-diagram{position:relative;min-width:1060px;max-width:1300px;margin:0 auto}
#pac .pac-wires{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1;overflow:visible}
#pac .pac-wlabel{font:600 9.5px var(--mono);fill:var(--muted)}
#pac .pac-wlabel-bg{fill:var(--bg);opacity:.92}
#pac .pac-plane{position:relative;z-index:2;display:grid;grid-template-columns:200px minmax(360px,1fr) 210px;
  grid-template-areas:"gov surf ." "gov harn reg" "gov exe ." "gov gw ." "gov ext ." "ops ops ops";column-gap:64px;row-gap:34px;align-items:start}
#pac .a-gov{grid-area:gov}#pac .a-surfaces{grid-area:surf}#pac .a-registry{grid-area:reg}#pac .a-harness{grid-area:harn}#pac .a-exec{grid-area:exe}#pac .a-gateways{grid-area:gw}#pac .a-external{grid-area:ext}#pac .a-ops{grid-area:ops}
#pac .pac-node{background:linear-gradient(180deg,var(--card),#131922);border:1px solid var(--line);border-radius:14px;position:relative}
#pac .grp-hd{display:flex;align-items:center;gap:8px;padding:10px 13px 9px}
#pac .grp-hd .gtag{font-size:9px;font-weight:700;letter-spacing:.11em;text-transform:uppercase;padding:3px 8px;border-radius:6px;color:#07100a}
#pac .grp-hd .gt{font-weight:650;font-size:12.5px;letter-spacing:-.1px}
#pac .grp-hd .gs{margin-left:auto;font-size:10px;color:var(--muted2);font-family:var(--mono)}
#pac .pac-card{display:block;width:100%;text-align:left;background:var(--card-h);border:1px solid var(--line);border-radius:10px;padding:11px 12px;cursor:pointer;position:relative;overflow:hidden;transition:transform .15s,border-color .15s,box-shadow .15s;color:var(--ink);font-family:inherit}
#pac .pac-card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--ac)}
#pac .pac-card:hover{transform:translateY(-2px);border-color:var(--ac);box-shadow:0 12px 26px -14px #000}
#pac .pac-card.sel{border-color:var(--ac);box-shadow:0 0 0 1px var(--ac),0 12px 26px -14px #000}
#pac .pac-card.active{background:linear-gradient(180deg,#12251c,#0f1f18)}
#pac .pac-card .ct{font-weight:600;font-size:12.5px;letter-spacing:-.1px;display:flex;align-items:center;gap:6px}
#pac .pac-card .cd{color:var(--muted);font-size:10.5px;line-height:1.4;margin-top:2px}
#pac .pac-badge{font-size:8px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:#0e1a13;background:#37dd7d;padding:2px 5px;border-radius:5px}
#pac .pac-q{margin-left:auto;font-size:11px;font-weight:800;color:#4cc4f5;background:#4cc4f51f;width:16px;height:16px;border-radius:5px;display:grid;place-items:center}
#pac .rowh{display:flex;gap:10px;padding:0 13px 13px}
#pac .rowh .pac-card{flex:1}
#pac .grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding:0 13px 13px}
#pac .spine-body{display:flex;flex-direction:column;gap:9px;padding:0 12px 13px}
#pac .single{padding:0 12px 13px;display:flex;flex-direction:column;gap:9px}
#pac .a-gov.pac-node{align-self:stretch;display:flex;flex-direction:column;border-color:#7d9bff4d;background:linear-gradient(180deg,#141d31,#0f1420);box-shadow:0 0 0 1px #7d9bff1a,0 20px 50px -30px #000}
#pac .a-gov .spine-body{flex:1;justify-content:center}
#pac .a-registry.pac-node{border-color:#2dd4bf3a}
#pac .a-ops.pac-node{border-color:#f0a85036;background:linear-gradient(180deg,#241c0f7a,#141016)}
#pac .a-gateways.pac-node{border-color:#4cc4f53a}
#pac .gw-wrap{display:flex;gap:40px;padding:0 16px 13px;justify-content:space-between}
#pac .gw-wrap .pac-card{flex:1;max-width:300px}
#pac .ext-wrap{display:flex;gap:22px;justify-content:space-between}
#pac .extbox{flex:1;background:linear-gradient(180deg,var(--card),#131922);border:1px solid var(--line);border-radius:14px;padding:11px 11px 12px}
#pac .extbox .exbh{font-size:9px;font-weight:700;letter-spacing:.11em;text-transform:uppercase;color:var(--muted2);margin:0 2px 9px}
#pac .a-exec.pac-node{max-width:280px;margin:0 auto}
#pac .a-harness.pac-node{border-color:#37dd7d77;background:linear-gradient(180deg,#0f2318,#0d1a13);box-shadow:0 0 0 1px #37dd7d22,0 26px 64px -26px #000,0 0 90px -44px #37dd7d}
#pac .harness-title{padding:14px 16px 4px;display:flex;align-items:center;gap:9px}
#pac .harness-title .gtag{background:#37dd7d}
#pac .harness-title .ht{font-weight:700;font-size:15px;letter-spacing:-.2px}
#pac .harness-title .hs{margin-left:auto;font-size:10px;color:#37dd7d;font-family:var(--mono)}
#pac .harness-sub{padding:0 16px 12px;font-size:11px;color:var(--ink-dim);line-height:1.5}
#pac .harness-core{margin:0 14px 14px;border:1px dashed #37dd7d4d;border-radius:12px;padding:12px;background:#0a140e88}
#pac .harness-core .mini{font-size:9px;text-transform:uppercase;letter-spacing:.11em;color:#37dd7d;font-weight:700;margin-bottom:10px}
#pac .core-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
#pac .core-cell{text-align:left;background:#10201799;border:1px solid #37dd7d2e;border-radius:9px;padding:9px 10px;cursor:pointer;transition:.15s;color:var(--ink);font-family:inherit}
#pac .core-cell:hover,#pac .core-cell.sel{border-color:#37dd7d;background:#14271b;transform:translateY(-1px)}
#pac .core-cell .cct{font-size:11.5px;font-weight:600}
#pac .core-cell .ccd{font-size:9.5px;color:var(--muted);margin-top:1px;line-height:1.35}
#pac .pac-bp{padding:22px 26px 4px;border-bottom:1px solid var(--line-soft)}
#pac .pac-bp-kicker{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.11em;color:#37dd7d}
#pac .pac-bp h2{margin:8px 0 0;font-size:19px;font-weight:680;letter-spacing:-.3px}
#pac .pac-bp-type{display:inline-block;margin-top:8px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#0e1a13;background:#37dd7d;padding:3px 9px;border-radius:6px}
#pac .pac-bp-desc{margin:12px 0 0;font-size:12.5px;line-height:1.6;color:var(--ink-dim)}
#pac .ap-empty{padding:76px 34px;color:var(--muted2);text-align:center}
#pac .ap-empty .ic{width:58px;height:58px;border-radius:15px;margin:0 auto 20px;background:#ffffff06;border:1px solid var(--line);display:grid;place-items:center}
#pac .ap-empty h4{color:var(--ink-dim);font-size:14px;margin:0 0 8px;font-weight:600}
#pac .ap-empty p{margin:0;font-size:12.5px;line-height:1.65}
#pac .ap-hd{padding:24px 26px 20px;border-bottom:1px solid var(--line-soft);position:sticky;top:0;background:linear-gradient(180deg,var(--bg-soft),#0f141b);z-index:3}
#pac .ap-kicker{display:inline-flex;align-items:center;gap:7px;font-size:10px;text-transform:uppercase;letter-spacing:.11em;margin-bottom:12px;font-weight:700;padding:4px 10px;border-radius:20px;background:var(--k-bg);color:var(--k-fg);border:1px solid var(--k-bd)}
#pac .ap-hd h2{margin:0;font-size:20px;font-weight:680;letter-spacing:-.3px}
#pac .ap-hd p{margin:11px 0 0;color:var(--ink-dim);font-size:13px;line-height:1.65}
#pac .ap-sec{padding:20px 26px;border-bottom:1px solid var(--line-soft)}
#pac .ap-sec h3{margin:0 0 14px;font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);font-weight:700;display:flex;align-items:center;gap:8px}
#pac .ap-sec h3 .bar{width:16px;height:2px;border-radius:2px;background:var(--k-fg)}
#pac .pac-live{margin-left:auto;font-size:8px;color:#0e1a13;background:#37dd7d;padding:2px 6px;border-radius:5px;letter-spacing:.06em}
#pac .pac-answers{display:flex;flex-direction:column;gap:7px}
#pac .pac-answer{display:flex;align-items:center;gap:9px;text-align:left;background:#ffffff05;border:1px solid var(--line);border-radius:9px;padding:10px 12px;color:var(--ink-dim);font-size:12px;cursor:pointer;font-family:inherit;transition:.14s}
#pac .pac-answer:hover{border-color:#37dd7d;color:var(--ink)}
#pac .pac-answer.on{border-color:#37dd7d;background:#14271b;color:var(--ink)}
#pac .pac-answer .dot{width:8px;height:8px;border-radius:50%;border:1px solid var(--muted)}
#pac .pac-answer.on .dot{background:#37dd7d;border-color:#37dd7d}
#pac .pac-answer:disabled{opacity:.5;cursor:default}
#pac .pac-current{margin:10px 0 0;font-size:11px;color:var(--muted)}
#pac .pac-evidence{margin-top:12px;display:flex;flex-direction:column;gap:8px}
#pac .pac-claim{border:1px solid #2dd4bf3a;background:#0f201d;border-radius:9px;padding:10px 11px}
#pac .pac-claim p{margin:0;font-size:11.5px;line-height:1.45;color:var(--ink-dim)}
#pac .pac-claim .src{margin-top:6px;font-size:9.5px;color:var(--muted);display:flex;gap:6px;align-items:center}
#pac .pac-claim .src a{margin-left:auto;color:#2dd4bf;text-decoration:none}
#pac .dec{border:1px solid var(--line);background:#ffffff05;border-radius:12px;padding:14px 15px;margin-bottom:11px}
#pac .dec .q{font-weight:600;font-size:13px;margin-bottom:10px;color:var(--ink);line-height:1.4}
#pac .opt{display:flex;gap:9px;font-size:12px;color:var(--ink-dim);padding:6px 0;border-top:1px solid var(--line-soft);line-height:1.45}
#pac .opt:first-of-type{border-top:none}
#pac .opt .k{color:var(--muted2);flex-shrink:0;margin-top:1px}
#pac .opt b{color:var(--ink);font-weight:600}
#pac .plist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:9px}
#pac .plist li{padding-left:26px;position:relative;color:var(--ink-dim);font-size:12.5px;line-height:1.5}
#pac .plist li::before{content:"✓";position:absolute;left:0;top:0;color:#37dd7d;font-weight:800;background:#37dd7d18;width:18px;height:18px;border-radius:6px;display:grid;place-items:center;font-size:10px}
#pac .a-external .ext-wrap .extbox .pac-card::before{background:var(--ac)}
    `}</style>
  );
}
