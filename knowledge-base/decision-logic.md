# Agentic Platform Advisor — Decision Logic & Intake Questionnaire (v2)

## Purpose

This document encodes the structured 9-question intake questionnaire for enterprise customers evaluating an agent platform strategy. Each question captures a critical architectural decision input. The combination of answers drives pattern recommendations, sequencing advice, and service selection.

**Audience**: VP of Engineering / VP of Platform / CTO responsible for enterprise-wide agent strategy.

**Usage by LLM**: When a customer engages the advisor, walk through these questions in order. Use the scoring engine at the end to map the combination of answers to a recommended architecture pattern.

**Version**: 2.0 (9 questions, reduced from 12)

**What was removed and why:**
- "Governance Model" — that's the OUTPUT, not input. The engine decides this.
- "Agent Intake Maturity" — doesn't change architecture; always needed.
- "Observability" — always part of platform; existing tools are an integration detail.
- "Stack Preference" — merged into Cloud Posture + Expertise (implied by builder persona + cloud stance).
- "Auth/Identity" — removed as standalone; inferred from team count + cloud posture + compliance.

---

## Question 1: Decision Model

### Question to Ask

> "How should agents make decisions in your organization?"

### Answer Options

| Option | Label | Description |
| --- | --- | --- |
| A | **Full Autonomy** | Agents act independently — reason, decide, and execute without human gates. Humans monitor but don't block. |
| B | **Approval Gates** | Agents propose actions; humans approve before execution of consequential operations. |
| C | **Copilot Mode** | Agents assist and augment; humans execute. Agents never take actions independently. |

### Select Type: SINGLE

### Architectural Signal
Guardrail depth, orchestration pattern, blast-radius controls.

### Architectural Implications

- **Full Autonomy** → Requires robust guardrails (AgentCore Policy Tier 3), circuit breakers, cost caps, anomaly detection, and rollback mechanisms. Architecture must include blast-radius containment. Favors event-driven patterns.
- **Approval Gates** → Requires approval workflow integration (Slack, ServiceNow, email). Architecture needs state persistence (agents pause and resume). Adds latency but reduces risk. Step Functions with human approval tasks.
- **Copilot Mode** → Simplest safety architecture. Agents are stateless assistants. Lower guardrail requirements but still needs content filtering. Optimizes for latency and UX.

### Pattern Steering

- Full Autonomy → Federated/Mesh patterns (teams need autonomy to match agent autonomy)
- Approval Gates → Centralized platform (approval workflows are centrally managed)
- Copilot Mode → Centralized platform (simplicity-first, minimal governance overhead)

### Weight: 0.14

---

## Question 2: Builder Persona

### Question to Ask

> "Who's building agents in your organization?"

### Answer Options

| Option | Label | Description |
| --- | --- | --- |
| A | **AI/ML Engineers** | Dedicated ML engineers who build custom models, fine-tune, and build from primitives. |
| B | **Full-Stack Developers** | Strong software engineers with AI interest. Can use SDKs but shouldn't build inference infra. |
| C | **Business Teams** | Non-technical teams using no-code/low-code tools. Need full abstractions. |
| D | **Mix of All** | Organization has all three personas building agents at different levels. |

### Select Type: SINGLE

### Architectural Signal
Managed vs custom, abstraction level, framework choice.

### Architectural Implications

- **AI/ML Engineers** → Can leverage open-source frameworks (Strands SDK, LangGraph, CrewAI, AutoGen/AG2, Semantic Kernel, LlamaIndex Agents). Can build custom orchestration. Architecture can include custom components.
- **Full-Stack Developers** → Sweet spot for AgentCore Runtime + custom tooling. Teams can write tool definitions, design prompts, integrate APIs. Shouldn't own infrastructure.
- **Business Teams** → Needs fully managed, opinionated platform. AgentCore Runtime with pre-built tool libraries, visual builders, templates and guardrails enforced by platform team.
- **Mix of All** → Tiered platform architecture. Self-service for business teams, SDK access for devs, custom extension points for ML engineers. Most complex governance.

### Pattern Steering

- AI/ML Engineers → Federated platform, custom orchestration
- Full-Stack Devs → Centralized with managed services + SDK extension points
- Business Teams → Centralized, fully managed, maximum abstraction
- Mix → Federated with tiered self-service

### Weight: 0.11

---

## Question 3: Team Count

### Question to Ask

> "How many teams will build or consume agents on this platform?"

### Answer Options

| Option | Label | Description |
| --- | --- | --- |
| A | **1–3 teams** | Single team or a few closely-aligned teams (single org). |
| B | **4–10 teams** | Multiple teams with distinct use cases but shared infrastructure needs (multi-LOB). |
| C | **10+ teams** | Enterprise-wide adoption. Many teams, diverse use cases, varying maturity (enterprise-wide). |

### Select Type: SINGLE

### Architectural Signal
Centralized vs federated vs mesh topology.

### Architectural Implications

- **1–3 teams** → Centralized platform owned by one team. Simple governance. Shared infrastructure without complex multi-tenancy. Start monolithic, refactor later.
- **4–10 teams** → Centralized platform with self-service capabilities. Need multi-tenancy, cost allocation, role-based access. Platform team provides guardrails; LOBs build within boundaries.
- **10+ teams** → Federated model becomes necessary. Central platform team provides shared services (model access, guardrails, observability, AgentCore Registry) but LOBs own their agent implementations. Need discovery, standards, and governance at scale.

### Pattern Steering

- 1–3 teams → Centralized platform (simple)
- 4–10 teams → Centralized with federation roadmap
- 10+ teams → Federated platform with central governance layer

### Weight: 0.15 (highest weight — strongest signal for topology)

---

## Question 4: Agent Purpose

### Question to Ask

> "What are agents FOR in your organization? Select all that apply."

### Answer Options (MULTI-SELECT — each fires independently)

| Option | Label | Description |
| --- | --- | --- |
| A | **Internal productivity** | Back-office automation: HR, finance, procurement, knowledge management. |
| B | **Customer-facing products** | Agents that interact directly with customers. SLA-bound, reliability-critical. |
| C | **Revenue-generating workflows** | Agents embedded in revenue streams. Uptime = money. |
| D | **Developer tooling** | AIDLC agents: code generation, testing, deployment, documentation. |
| E | **Operations / incident response** | SRE automation, real-time incident triage, runbook execution. |

### Select Type: MULTI-SELECT

### Multi-Select Behavior
Each selected option fires its own constraint node independently. Pressures ADD (not average). Selecting "Customer-facing" AND "Revenue-generating" activates BOTH constraint nodes.

### Architectural Signal
SLA tiers, reliability requirements, compliance depth, cost tolerance.

### Architectural Implications

- **Internal productivity** → Lower reliability bar (internal SLAs). Iterate faster. Focus on developer experience. Cost optimization matters but downtime tolerable.
- **Customer-facing** → Production-grade reliability required. Latency targets. Security paramount. Compliance and audit trails critical. Elevates Policy Engine tier.
- **Revenue-generating** → Maximum uptime. Blue/green deployment. Continuous evaluation mandatory. Elevates Eval Pipeline tier.
- **Developer tooling** → Fast iteration cycles. Sandbox-friendly. Less governance overhead. Favors federation.
- **Operations / incident response** → Real-time requirements. Event-driven architecture. Streaming responses. Low-latency model routing.

### Weight: 0.12

---

## Question 5: Cloud and Portability Stance

### Question to Ask

> "What's your cloud and portability stance?"

### Answer Options

| Option | Label | Description |
| --- | --- | --- |
| A | **All-in on AWS** | All workloads on AWS. Agents will use AWS services exclusively. |
| B | **AWS-primary** | AWS is primary but some workloads/data reside elsewhere. |
| C | **Multi-cloud (2+)** | Workloads distributed across 2+ clouds. Platform must be portable. |
| D | **On-prem / edge** | Must run on-premises or at the edge. Cloud-optional. |

### Select Type: SINGLE

### Architectural Signal
Framework portability, service choices, protocol importance.

### Architectural Implications

- **All-in on AWS** → Full leverage of AgentCore ecosystem, native integrations, IAM for agent identity. Simplest architecture, deepest feature access.
- **AWS-primary** → Use AWS as control plane. MCP servers via AgentCore Gateway as universal connectors to other cloud resources. Agent logic on AWS, tool execution may cross boundaries.
- **Multi-cloud (2+)** → Requires portable agent frameworks (Strands SDK, LangGraph, Semantic Kernel). Orchestration must be cloud-agnostic. MCP critical as universal connector. Significantly higher complexity.
- **On-prem / edge** → Requires containerized deployment (ECS/EKS or equivalent). AgentCore Runtime with on-prem model hosting. Latency-sensitive design. Mesh patterns natural.

### Pattern Steering

- All-in AWS → Centralized platform (fully managed)
- AWS-primary → Centralized with gateway bridge layer
- Multi-cloud → Federated/Mesh with portable orchestration
- On-prem/edge → Mesh with distributed execution

### Weight: 0.10

---

## Question 6: Data Gravity

### Question to Ask

> "Where does your critical data live?"

### Answer Options

| Option | Label | Description |
| --- | --- | --- |
| A | **Single AWS region** | All critical data in one region. Simple data residency. |
| B | **Multiple AWS regions** | Data distributed across AWS regions (DR, latency, compliance). |
| C | **Hybrid (on-prem + cloud)** | Some data on-prem, some in cloud. Agents must bridge both. |
| D | **Edge / distributed** | Data at edge locations, IoT, or distributed systems. |

### Select Type: SINGLE

### Architectural Signal
Agent execution location, latency patterns, data residency.

### Architectural Implications

- **Single region** → Deploy all agents in-region. Simplest latency profile. Single-region disaster recovery may be acceptable for internal workloads.
- **Multiple regions** → Multi-region agent deployment. Data replication concerns. Region-aware routing. Cross-region latency budget.
- **Hybrid** → Agents need secure tunnels to on-prem data. Gateway acts as bridge. Consider edge-deployed agents for latency-sensitive queries. Data residency constraints affect agent placement.
- **Edge / distributed** → Lightweight agent runtimes at edge. Async coordination with cloud. Local model inference for latency. Sync back to centralized observability.

### Pattern Steering

- Single region → Centralized (simplicity)
- Multi-region → Federated (regional autonomy)
- Hybrid → Mesh (distributed execution)
- Edge → Mesh (peer-to-peer at edge)

### Weight: 0.08

---

## Question 7: Cost Model

### Question to Ask

> "What's your cost model for the agent platform?"

### Answer Options

| Option | Label | Description |
| --- | --- | --- |
| A | **Cost-first** | Cost is the #1 constraint. Must optimize from day 1. Cannot have surprise bills. |
| B | **Performance-first** | Get it right first, optimize cost later. Speed and quality over cost. |
| C | **Predictable spend** | Fixed budget matters. Need budget caps and predictable monthly spend. |
| D | **Pay-for-outcomes** | ROI-driven. Willing to spend for outcomes. Cost is secondary to value generated. |

### Select Type: SINGLE

### Architectural Signal
Routing layer priority, budget enforcement, tier selection for cost gateway.

### Architectural Implications

- **Cost-first** → Architecture MUST include: token budgets per agent, intelligent model routing (cheap models for simple tasks), semantic caching, circuit breakers on spend. Elevates Cost Engine to Tier 3.
- **Performance-first** → Focus on capability. Include cost observability from day one but defer optimization. Design for future cache/routing layers without building immediately.
- **Predictable spend** → Budget caps, cost allocation tags, per-LOB quotas. Predictability over optimization. Fixed-rate model agreements where possible.
- **Pay-for-outcomes** → Business outcome attribution. ROI calculators. Agents justified by value not cost. Economy pattern becomes attractive.

### Pattern Steering

- Cost-first → Centralized (cost governance built-in) + Economy pattern overlay
- Performance-first → Federated (speed over control)
- Predictable spend → Centralized with budget enforcement
- Pay-for-outcomes → Economy pattern (market-based allocation)

### Weight: 0.10

---

## Question 8: Compliance Frameworks

### Question to Ask

> "Which compliance frameworks apply to your agent platform? Select all that apply."

### Answer Options (MULTI-SELECT — each fires independently)

| Option | Label | Description |
| --- | --- | --- |
| A | **SOX** | Financial controls — audit trails, segregation of duties, 7-year retention. |
| B | **PCI-DSS** | Payment card data — network segmentation, encryption, access control. |
| C | **HIPAA** | Health data — PHI boundaries, minimum necessary, consent management. |
| D | **FedRAMP / FISMA** | Government — continuous monitoring, NIST controls, data sovereignty. |
| E | **EU AI Act** | European AI regulation — explainability, risk classification, human oversight. |
| F | **GDPR** | Data privacy — right to deletion, consent, data minimization. |
| G | **None / internal only** | No external compliance requirements. Internal policies only. |

### Select Type: MULTI-SELECT

### Multi-Select Behavior
Each selected framework activates its own constraint node. Multiple frameworks compound — SOX + HIPAA + FedRAMP forces maximum governance tiers across the board.

### Architectural Signal
Forced component tiers, audit requirements, data boundaries, policy engine depth.

### Architectural Implications

- **SOX** → Forces Policy Engine Tier 3, Observability Tier 3 (7-year audit trails), Identity Tier 3 (segregation of duties).
- **PCI-DSS** → Forces network segmentation, encryption-at-rest/in-transit, Identity Tier 2+ (access control logs).
- **HIPAA** → Forces Policy Engine Tier 3 (PHI boundaries), data residency constraints, Memory/State Tier 2+ (encrypted, purgeable).
- **FedRAMP / FISMA** → Forces Identity Tier 3 (zero-trust), all data in authorized regions, continuous monitoring.
- **EU AI Act** → Forces explainability, human oversight mechanisms, risk classification of agent use cases.
- **GDPR** → Forces right-to-deletion in Memory/State, consent management, data minimization in agent prompts.
- **None** → No forced elevations. Maximum flexibility in tier selection. Favors federation and speed.

### Weight: 0.10

---

## Question 9: Pain Points

### Question to Ask

> "What's hardest right now? Select all that apply."

### Answer Options (MULTI-SELECT — each fires independently)

| Option | Label | Description |
| --- | --- | --- |
| A | **Too expensive** | Agents are too expensive at scale. LLM costs growing faster than value. |
| B | **Can't govern** | Can't govern or track what agents do. No visibility into decisions or actions. |
| C | **Silos / no reuse** | Teams building in silos. No shared components. Duplicated effort. |
| D | **Tool integration slow** | Tool/API integration takes too long. Every new tool is a project. |
| E | **Auth is a mess** | Authentication across agents is inconsistent, insecure, or unmanageable. |
| F | **Can't trust outputs** | Can't trust agent outputs. Hallucinations, inaccuracies, no verification. |
| G | **No CI/CD** | No CI/CD pipeline for agents. Manual deployment, no testing framework. |
| H | **Choosing frameworks** | Paralyzed choosing between frameworks. No clear standard. |
| I | **Too slow** | Agents are too slow for real-time use cases. Latency is unacceptable. |

### Select Type: MULTI-SELECT

### Multi-Select Behavior
Each selected pain point activates its own constraint node. Pain points inform Innovation overlays (SOLVES edges) and prioritize specific components.

### Architectural Signal
Innovation overlays, anti-pattern prioritization, P0 component selection.

### Architectural Implications

- **Too expensive** → P0: Cost Engine Tier 3, intelligent model routing, semantic caching.
- **Can't govern** → P0: Registry Tier 2+, AgentCore Policy, observability.
- **Silos / no reuse** → P0: Registry with discovery, AgentCore Gateway shared tool library.
- **Tool integration slow** → P0: AgentCore Gateway, MCP auto-generation from OpenAPI.
- **Auth is a mess** → P0: AgentCore Identity Tier 3, centralized credential management.
- **Can't trust outputs** → P0: Automated Reasoning, RAG verification, Eval Pipeline Tier 2+.
- **No CI/CD** → P0: AgentCore Harness, Evaluations pipeline.
- **Choosing frameworks** → Recommend framework convergence on MCP + AgentCore Runtime.
- **Too slow** → P0: Event-driven streaming, model routing for latency, edge deployment.

### Weight: 0.10

---

## Scoring Engine — Pattern Recommendation

### Scoring Process

Each constraint node has 5 affinity axes (0.0–1.0):
- `centralization_pressure` → Pattern: Centralized
- `federation_pressure` → Pattern: Federated
- `mesh_pressure` → Pattern: Mesh
- `economy_pressure` → Pattern: Economy
- `simplicity_pressure` → Amplifier for Centralized (tiebreaker)

### Algorithm

1. For each selected answer, find the matching Constraint node in `graph.json`
2. Traverse all `PRESSURES_TOWARD` and `PRESSURES_AGAINST` edges to Pattern nodes
3. Accumulate weighted scores per Pattern: `score += edge_weight × constraint_signal_weight`
4. For multi-select questions (Q4, Q8, Q9): ALL selected options fire independently (pressures ADD)
5. Check for `BLOCKS` edges from Law nodes — remove blocked patterns
6. Select the highest-scoring non-blocked Pattern
7. If top two scores are within 20%, recommend hybrid approach

### Question Weights (must sum to 1.0)

| # | Question | Weight | Rationale |
|---|----------|--------|-----------|
| Q1 | Decision model | 0.14 | Defines safety architecture depth |
| Q2 | Builder persona | 0.11 | Constrains abstraction level |
| Q3 | Team count | 0.15 | Strongest signal for topology |
| Q4 | Agent purpose | 0.12 | Sets SLA and reliability tier |
| Q5 | Cloud stance | 0.10 | Constrains technology choices |
| Q6 | Data gravity | 0.08 | Affects execution location |
| Q7 | Cost model | 0.10 | Shapes cost architecture |
| Q8 | Compliance | 0.10 | Forces minimum tiers |
| Q9 | Pain points | 0.10 | Prioritizes innovation overlays |

### Priority Order for Maximum Information Gain

Ask questions in this order:

1. **Team Count (Q3)** — strongest topology signal
2. **Decision Model (Q1)** — shapes safety architecture
3. **Builder Persona (Q2)** — determines managed vs custom
4. **Agent Purpose (Q4)** — sets SLA tier
5. **Cloud Stance (Q5)** — constrains technology
6. **Cost Model (Q7)** — adds cost architecture
7. **Compliance (Q8)** — forces minimum tiers
8. **Pain Points (Q9)** — prioritizes innovations
9. **Data Gravity (Q6)** — fine-tunes execution location

---

## Example Branching Scenarios

### Scenario A: "The Cautious Enterprise"

- Q1: Approval gates | Q2: Full-stack devs | Q3: 4-10 teams | Q4: Customer-facing + Internal productivity | Q5: All-in AWS | Q6: Single region | Q7: Predictable spend | Q8: SOX + PCI-DSS | Q9: Can't govern + Can't trust outputs
- **→ Centralized Platform, Maximum Governance, Compliance-Heavy**
- Services: AgentCore Runtime + Policy (Tier 3) + Registry + Evaluations, Step Functions (HITL), CloudWatch

### Scenario B: "The Tech-Forward Scale-Up"

- Q1: Full autonomy | Q2: AI/ML engineers | Q3: 1-3 teams | Q4: Developer tooling + Internal productivity | Q5: AWS-primary | Q6: Single region | Q7: Performance-first | Q8: None | Q9: Choosing frameworks + Tool integration slow
- **→ Centralized (small team) with OSS Agent Layer, Plan Federation at 5+ teams**
- Services: Strands SDK or LangGraph + Bedrock inference, AgentCore Gateway, framework convergence

### Scenario C: "The Global Conglomerate"

- Q1: Full autonomy | Q2: Mix of all | Q3: 10+ teams | Q4: Customer-facing + Revenue-generating + Ops | Q5: Multi-cloud | Q6: Multiple regions | Q7: Pay-for-outcomes | Q8: SOX + GDPR + EU AI Act | Q9: Too expensive + Silos + Auth mess
- **→ Federated Platform with Central Governance + Economy Overlay**
- Services: Portable orchestration (Strands/LangGraph/Semantic Kernel), AgentCore Registry + Policy + Identity + Payments, MCP bridges via AgentCore Gateway

---

## Retrieval Notes for LLM

- When a user provides partial answers, infer what you can and ask clarifying questions for ambiguous signals.
- Never recommend federated for < 5 teams unless expertise is very high and there's a strong multi-cloud requirement.
- Compliance selections ALWAYS force minimum tiers regardless of other answers.
- Pain points ALWAYS activate innovation overlays (check SOLVES edges in graph).
- If the user selects multiple options in Q4/Q8/Q9, ALL fire independently — pressures compound, they don't average.
- Framework recommendations should be balanced: Strands SDK, LangGraph, CrewAI, AutoGen/AG2, Semantic Kernel, and LlamaIndex Agents are all valid depending on team profile.
- NEVER recommend deprecated services: Bedrock Agents, Amazon Kendra, Bedrock Flows are DECOMMISSIONED. Use AgentCore components.
