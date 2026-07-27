# Anti-Patterns Catalog: Enterprise Agentic Platforms

## Purpose

This document is a standalone catalog of named anti-patterns that emerge in enterprise agentic AI platforms. Each anti-pattern is documented with symptoms, root causes, architectural fixes, and prevention strategies. Use this as a diagnostic tool when customers describe platform problems, or as a design checklist to prevent common failures.

**Audience**: VP of Engineering / VP of Platform / Solutions Architects designing or troubleshooting agent platforms.

**Usage by LLM**: When a customer describes symptoms (agent problems, team friction, cost issues), match to anti-patterns below. Provide the name, explain the root cause, and recommend the architectural fix with specific AgentCore components.

---

## Anti-Pattern 1: God Agent

### Description
A single agent is designed to handle everything — all use cases, all data sources, all tools, all user types. It becomes a monolithic, unmaintainable, untestable blob.

### Pattern(s) It Applies To
- Centralized Platform (most common)
- Early-stage Federated (LOBs building their "one agent to rule them all")

### Symptoms
- Agent prompt is 10,000+ tokens
- Agent has access to 50+ tools
- Performance degrades as capabilities are added
- Testing is impossible (too many interaction paths)
- One use case change breaks others
- Latency increases over time as context grows
- Error rate is high but root cause is unclear

### Root Cause
Organization treated "agent" as a monolithic application rather than a composable architecture. No decomposition strategy. Single agent grew organically as each team added their requirements.

### Architectural Fix
1. **Decompose** — Break into specialized agents with clear, bounded responsibilities
2. **Orchestrator pattern** — One routing agent delegates to specialized sub-agents
3. **AgentCore Registry** — Register each specialized agent as a discoverable capability
4. **A2A protocol** — Enable agent-to-agent delegation via EventBridge
5. **AgentCore Gateway** — Each agent accesses only its relevant tools (least-privilege)

### Prevention
- **At Tier 1**: Define agent scope boundaries during intake. One agent = one capability domain.
- **AgentCore Registry** enforces capability tagging — makes overlap visible
- **AgentCore Policy** limits tool count per agent (configurable policy)
- Design review in intake process: "If your agent needs > 10 tools, it should be multiple agents"

---

## Anti-Pattern 2: Single Team Bottleneck

### Description
The platform team becomes the sole gateway for all agent work. Every request, change, and deployment flows through one team that can't keep up with demand.

### Pattern(s) It Applies To
- Centralized Platform (primary victim)
- Early Federated (if federation is incomplete)

### Symptoms
- 4+ week backlog for new agent requests
- LOBs waiting for platform team for every change
- Platform team doing agent-specific work instead of platform improvement
- LOB frustration and shadow IT emerging
- Platform team burnout and attrition
- All innovation gated by one team's capacity

### Root Cause
Platform team didn't invest in self-service. Built custom solutions for each LOB instead of enabling LOBs to self-serve. Over-centralized control without automation.

### Architectural Fix
1. **Self-service portal** — LOBs provision and deploy agents without platform team involvement (80%+ of requests)
2. **Agent templates** — Pre-approved patterns that LOBs can instantiate without review
3. **AgentCore Harness** — Automated testing so LOBs validate their own agents
4. **AgentCore Policy (automated)** — Policy enforcement in CI/CD, not manual review
5. **Tiered governance** — Low-risk agents deploy automatically; only high-risk needs human review
6. **Federation roadmap** — Graduate mature LOBs to self-governance

### Prevention
- **At Tier 1**: Design self-service from day one (even if initially only templates)
- **AgentCore Policy** automates policy checking — removes human review from most deployments
- Platform team KPI: percentage of requests self-served (target > 80%)
- Regular capacity planning: platform team scales with LOB count

---

## Anti-Pattern 3: Agent Sprawl

### Description
Uncontrolled proliferation of agents with no lifecycle management. Redundant agents, abandoned agents, agents with no owner, agents with overlapping capabilities that nobody knows about.

### Pattern(s) It Applies To
- Federated Platform (highest risk)
- Centralized Platform (if governance is weak)
- Mesh (inherent risk)

### Symptoms
- Nobody knows how many agents exist
- Redundant agents solving the same problem differently
- Agents running with no active owner
- Costs growing faster than value
- Security risk from unmonitored agents
- Unable to answer "what agents do we have?"

### Root Cause
No mandatory registration, no lifecycle management, no health monitoring. Easy to create, impossible to find or retire. No incentive to reuse existing agents.

### Architectural Fix
1. **AgentCore Registry (mandatory)** — Every agent MUST be registered with owner, purpose, SLA
2. **Health scoring** — Automated health checks (usage, error rate, update recency)
3. **Lifecycle automation** — Unused agents → warning → deprecation → retirement
4. **Duplicate detection** — AgentCore Registry alerts when proposed agents overlap with existing
5. **Discovery-first intake** — "Before you build, search what exists" workflow
6. **Ownership enforcement** — No unowned agents; ownership transfer on team changes

### Prevention
- **At Tier 2**: Deploy AgentCore Registry before agent count reaches 10
- **AgentCore Observability** feeds usage data into health scoring
- Automated alerts when agents have zero invocations for 30 days
- Chargeback model (AgentCore Payments) — idle agents still cost money, incentivizing cleanup

---

## Anti-Pattern 4: Capability Gap

### Description
Federated LOBs are granted autonomy but lack the expertise to operate agents independently. Quality varies wildly. Some LOBs produce excellent agents; others produce dangerous ones.

### Pattern(s) It Applies To
- Federated Platform (primary)
- Progressive (during transition)

### Symptoms
- Quality varies 5x across LOBs
- Some LOBs' agents have high hallucination rates
- Incident rate correlates with LOB maturity
- LOBs asking central team for help they shouldn't need
- Customer-facing agents from immature LOBs causing brand damage

### Root Cause
Federation without readiness assessment. Granted autonomy based on demand, not capability. No maturity criteria. One-size-fits-all federation — all LOBs get same autonomy regardless of skill.

### Architectural Fix
1. **Maturity assessment** — Score LOBs before granting federation (expertise, tooling, process)
2. **Tiered federation** — Level 1 (limited autonomy), Level 2 (full autonomy), Level 3 (contributor)
3. **AgentCore Evaluations** — Mandatory quality gates regardless of LOB autonomy level
4. **Training/enablement** — Central team provides training, templates, and starter kits
5. **Guardrail enforcement** — AgentCore Policy applies to all LOBs equally (non-negotiable safety bar)
6. **Peer review** — Cross-LOB review for customer-facing agents

### Prevention
- **Before federation**: Maturity scorecard with minimum thresholds for self-governance
- **AgentCore Evaluations** runs continuously — quality degradation triggers escalation
- Central team provides "agent engineering" training curriculum
- Mandatory AgentCore Harness test suites before any production deployment

---

## Anti-Pattern 5: Observability Blind Spot

### Description
Agents running in production without adequate traces, metrics, or logging. When things go wrong, nobody can diagnose the issue. When things go right, nobody can prove it.

### Pattern(s) It Applies To
- All patterns (universal risk)
- Federated (higher risk due to distributed operations)

### Symptoms
- "I don't know why the agent did that"
- Unable to reproduce or explain agent decisions
- Cost surprises (no token usage visibility)
- Quality problems discovered by users, not monitoring
- Compliance audit failures (no audit trail)
- Unable to measure ROI (no task completion data)

### Root Cause
Observability was an afterthought. Agent deployed without instrumentation. Or: agents instrumented differently across teams with no standards.

### Architectural Fix
1. **AgentCore Observability (mandatory)** — Every agent emits traces, metrics, and logs from day one
2. **OTel standards** — Standardized telemetry format across all frameworks
3. **Pre-built dashboards** — Agent-specific dashboards (not generic infra dashboards)
4. **Quality alerting** — Automated alerts on quality degradation, cost anomalies, error spikes
5. **Audit logging** — Immutable record of every agent decision for compliance
6. **Token tracking** — Per-agent, per-model, per-invocation cost visibility

### Prevention
- **At Tier 1**: AgentCore Observability is non-negotiable from day one
- AgentCore Runtime auto-instruments all agent executions (no opt-in required)
- AgentCore Policy blocks deployment of agents without observability configured
- Regular observability reviews: "Can you explain this agent's last 100 decisions?"

---

## Anti-Pattern 6: Cost Explosion

### Description
Agent costs grow uncontrollably. No token budgets, no model routing, no caching. Single expensive model used for all tasks. Cost grows linearly (or worse) with usage.

### Pattern(s) It Applies To
- All patterns (universal risk)
- Centralized (concentrated blast radius)
- Federated (distributed, harder to track)

### Symptoms
- Monthly LLM costs 5-10x budget
- All tasks using same expensive model (e.g., Claude 3.5 Opus for simple lookups)
- No visibility into which agents/tasks consume most tokens
- No circuit breakers — runaway agents consume unlimited tokens
- Token usage growing faster than task volume
- Budget alerts triggered monthly

### Root Cause
No cost architecture. Treated model inference as "free" during development. No routing, no caching, no budgets. No per-agent cost attribution.

### Architectural Fix
1. **Model router** — Bedrock Intelligent Routing sends simple tasks to cheap models
2. **Token budgets** — Per-agent spending limits with circuit breakers
3. **Semantic caching** — Avoid re-calling LLMs for similar queries (40-60% cost reduction)
4. **Prompt caching** — Bedrock Prompt Caching for repeated prefixes
5. **Cost attribution** — AgentCore Payments tracks cost per agent, per LOB, per use case
6. **Batch inference** — Non-real-time tasks use 50% cheaper batch processing
7. **Cost alerting** — CloudWatch alarms on per-agent cost anomalies

### Prevention
- **At Tier 1**: Basic cost tracking from day one (AgentCore Observability includes token metrics)
- **At Tier 2**: Model routing and caching when costs exceed $10K/month
- AgentCore Policy enforces maximum token budget per invocation
- Regular cost reviews: "Top 10 most expensive agents — are they worth it?"

---

## Anti-Pattern 7: Auth Debt

### Description
Each agent has its own credential management — hardcoded keys, shared service accounts, no rotation, no delegation chain visibility. No identity mesh connecting agents to a unified auth system.

### Pattern(s) It Applies To
- Federated Platform (highest risk — each LOB manages own auth)
- Centralized (when platform team doesn't prioritize identity)

### Symptoms
- Agents using shared service accounts (no per-agent identity)
- Credentials stored in environment variables or code
- No automated credential rotation (some keys are years old)
- Unable to answer "what can this agent access?"
- No delegation chain visibility (who authorized this agent to act?)
- Agent-to-agent calls using ad-hoc authentication
- Security audit findings accumulate

### Root Cause
Identity was an afterthought. Each agent's auth was handled individually. No centralized identity strategy. "Just use a service account" became the default.

### Architectural Fix
1. **AgentCore Identity** — Every agent gets its own OAuth2 identity with automated lifecycle
2. **IAM roles (least-privilege)** — Per-agent roles with minimal permissions
3. **Automated rotation** — Credentials rotate automatically (no manual process)
4. **Delegation chains** — AgentCore Identity records user → agent → system authorization
5. **Permission boundaries** — IAM boundaries prevent privilege escalation
6. **Agent-to-agent auth** — Standard OAuth2 client credentials for inter-agent calls

### Prevention
- **At Tier 1**: Use AgentCore Identity from first agent (not "after we scale")
- AgentCore Policy blocks deployment of agents without proper identity configuration
- Regular auth audits: "Show me all agent permissions and last rotation date"
- No hardcoded credentials allowed — AgentCore Identity + Secrets Manager only

---

## Anti-Pattern 8: Tool Spaghetti

### Description
Every agent builds its own tool integrations. Same system (e.g., Salesforce, Jira, internal DB) is integrated 15 different ways across 15 agents. No shared tool library. No standards.

### Pattern(s) It Applies To
- Federated Platform (highest risk)
- Centralized (if no shared tool strategy)

### Symptoms
- Same API integrated multiple times, differently, across agents
- Inconsistent error handling per integration
- No shared authentication for common systems
- Breaking changes in one system require updating N agents independently
- Duplicated effort — 3 teams each build their own Salesforce connector
- No tool versioning — changes break agents silently

### Root Cause
No shared tool library or gateway. Each team builds point-to-point integrations. No incentive or mechanism to share tool implementations. MCP adoption is inconsistent.

### Architectural Fix
1. **AgentCore Gateway (shared)** — Central MCP server library for enterprise-wide tools
2. **Build once, share everywhere** — Salesforce MCP server built once, all agents consume
3. **Tool versioning** — AgentCore Gateway manages versions; consumers pin to version
4. **Inner-source model** — Any team can contribute tools to the shared library
5. **Tool standards** — Consistent error handling, auth, monitoring for all tools
6. **Change management** — Tool changes tested against all consuming agents before release

### Prevention
- **At Tier 1**: Build shared tools from day one for common systems
- **AgentCore Gateway** as the default tool hosting mechanism
- Discovery workflow: "Before building a tool, check if it exists in Gateway"
- Metrics on tool reuse rate (target: > 40% of tools are shared across 2+ agents)

---

## Anti-Pattern 9: Evaluation Theater

### Description
Agents are tested in development but not continuously evaluated in production. Evaluation happens once (before first deploy) and never again. Production quality degrades silently.

### Pattern(s) It Applies To
- All patterns (universal risk)
- Federated (harder to enforce consistent evaluation)

### Symptoms
- Agent quality was "great at launch" but degraded over months
- No ongoing quality metrics in production
- Evaluation only runs in CI/CD, not continuously
- Model updates cause regressions nobody catches
- Users report quality issues before monitoring does
- "We tested it before deploying" — but that was 6 months ago

### Root Cause
Evaluation treated as a one-time gate, not continuous monitoring. No production evaluation pipeline. Model drift, data drift, and prompt decay not monitored.

### Architectural Fix
1. **AgentCore Evaluations (continuous)** — Eval pipelines run on production traffic (sampled)
2. **Judge models** — LLM-as-judge continuously scoring production agent outputs
3. **Regression alerts** — Automated alerts when quality drops below threshold
4. **Model change evaluation** — Re-evaluate when underlying models are updated
5. **A/B testing** — Compare production versions continuously
6. **Human-in-the-loop eval** — Sample production interactions for human quality review

### Prevention
- **At Tier 2**: AgentCore Evaluations configured for both CI/CD AND production
- Quality metrics on AgentCore Observability dashboards (not just infra metrics)
- Automated re-evaluation triggered by model updates, prompt changes, tool changes
- KPI: "When was this agent last evaluated?" must always be < 7 days

---

## Anti-Pattern 10: Governance as Blocker

### Description
Governance process is so heavy that it kills innovation. Intake process takes months. Every agent requires executive approval. Teams give up before getting started.

### Pattern(s) It Applies To
- Centralized Platform (primary victim)
- Early Federated (if governance doesn't simplify during transition)

### Symptoms
- 3+ months from idea to first production agent
- Multiple approval committees required
- LOBs stop proposing agents (learned helplessness)
- Shadow agents emerge (teams bypass governance entirely)
- "Governance" team seen as adversary, not partner
- Innovation moves to non-agent solutions to avoid the process

### Root Cause
Treating all agents as equally risky. Applying maximum governance to minimum-risk use cases. Governance designed for compliance theater, not actual risk management. No tiered approach.

### Architectural Fix
1. **Tiered governance** — Risk-classify agents (low/medium/high) with different approval paths
2. **Automated fast-track** — Low-risk internal agents deploy with only automated policy checks
3. **AgentCore Policy (automated)** — Replace human reviewers with automated compliance checks
4. **Templates with pre-approval** — Pre-blessed agent templates that need no additional review
5. **Time-boxed reviews** — SLA on review time (e.g., low=0 days, medium=3 days, high=5 days)
6. **Self-service intake** — Replace committee meetings with self-service forms + automated triage

### Prevention
- **At Tier 1**: Start with lightweight governance. Add controls as needed, not preemptively.
- Design governance for enablement, not gatekeeping
- Metric: "Time from idea to production" — if > 2 weeks for templated agents, governance is too heavy
- Quarterly governance retrospective: "What did governance prevent vs. what did it delay?"

---

## Anti-Pattern 11: Model Lock-in

### Description
Organization depends entirely on a single model (or single model provider). No fallback. No cost optimization through model diversity. Vulnerable to outages, price changes, and capability plateaus.

### Pattern(s) It Applies To
- All patterns (universal risk)
- Centralized (easier to fix — single routing layer)

### Symptoms
- All agents use same model regardless of task complexity
- Provider outage = all agents down
- No cost optimization (cheap tasks use expensive models)
- Unable to leverage new models without refactoring all agents
- Vendor negotiation has no leverage (no alternative)
- Model deprecation announcements cause panic

### Root Cause
Convenience of single model. No abstraction layer between agents and models. Prompts tightly coupled to specific model behaviors. No evaluation infrastructure to validate new models.

### Architectural Fix
1. **Model abstraction layer** — Agents call "model router," not specific models
2. **Bedrock Intelligent Routing** — Automatic model selection based on task profile
3. **Multi-model strategy** — Different models for different task types
4. **Model evaluation pipeline** — AgentCore Evaluations tests agents against new models
5. **Fallback configuration** — Primary model unavailable → automatic failover to alternative
6. **Prompt portability** — Design prompts that work across model families

### Prevention
- **At Tier 1**: Use Bedrock Inference Profiles (model abstraction from day one)
- **At Tier 2**: Test agents against 2+ models before committing
- AgentCore Evaluations runs against multiple models periodically
- Architecture review: "What happens if [current model] is unavailable for 4 hours?"

---

## Anti-Pattern 12: Memory Amnesia

### Description
Agents have no persistent context across sessions. Every conversation starts from scratch. Users must repeat context. Agents can't learn from past interactions or build on previous work.

### Pattern(s) It Applies To
- All patterns (universal risk)
- Common in early agents (memory as afterthought)

### Symptoms
- Users repeating context in every session ("as I mentioned before...")
- Agents unable to reference past interactions
- No personalization over time
- Multi-session tasks require manual context transfer
- Agents make same mistakes repeatedly (no learning)
- User satisfaction drops for repeat users

### Root Cause
Memory treated as optional. Agents built as stateless functions. No persistence layer designed into the architecture. Short-term memory (conversation) exists but long-term memory is absent.

### Architectural Fix
1. **AgentCore Memory** — Managed short-term + long-term memory from day one
2. **User profiles** — Persistent preferences, context, and history per user
3. **Semantic memory** — Vector-based recall of relevant past interactions
4. **Cross-session continuity** — Tasks can span multiple sessions without loss
5. **Memory management** — TTL, relevance decay, capacity limits (prevent unbounded growth)
6. **Shared memory** — Multiple agents can access shared context (team knowledge)

### Prevention
- **At Tier 1**: Deploy AgentCore Memory for any agent that has repeat users
- Design for multi-session from the start (even if V1 is single-session)
- Metric: "User context repetition rate" — if users frequently repeat info, memory is inadequate
- Memory architecture review: "What should this agent remember across sessions?"

---

## Anti-Pattern Cross-Reference Matrix

| Anti-Pattern | Centralized | Federated | Mesh | Primary AgentCore Fix |
|---|---|---|---|---|
| God Agent | High | Medium | Low | Registry, Gateway, Policy |
| Single Team Bottleneck | **Very High** | Low | None | Policy (automated), Harness |
| Agent Sprawl | Medium | **Very High** | Very High | Registry |
| Capability Gap | Low | **Very High** | High | Evaluations, Harness |
| Observability Blind Spot | Medium | High | **Very High** | Observability |
| Cost Explosion | High | High | **Very High** | Payments, Policy |
| Auth Debt | Medium | **Very High** | Very High | Identity |
| Tool Spaghetti | Low | **Very High** | Very High | Gateway |
| Evaluation Theater | High | High | **Very High** | Evaluations |
| Governance as Blocker | **Very High** | Medium | Low | Policy (automated) |
| Model Lock-in | Medium | Medium | Medium | Evaluations, Runtime |
| Memory Amnesia | High | High | High | Memory |

---

## How to Use This Catalog

### For Diagnosis
When a customer describes a problem, scan symptoms across all anti-patterns. Often multiple anti-patterns are active simultaneously.

### For Prevention
During architecture design, walk through each anti-pattern and ask: "Do we have a prevention mechanism for this?" If not, add the relevant AgentCore component.

### For Maturity Assessment
Count how many anti-patterns an organization is experiencing. This maps to maturity:
- 0-2 anti-patterns: Mature platform
- 3-5 anti-patterns: Growing pains (normal at 6-12 months)
- 6-8 anti-patterns: Platform debt (needs focused remediation)
- 9+: Platform crisis (stop building new agents, fix foundations)

### For Tier Planning
Each anti-pattern's prevention maps to a tier. Use this to prioritize platform investments.
