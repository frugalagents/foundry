# Architecture Pattern: Centralized Agent Platform

## Pattern Summary

A **Centralized Agent Platform** is an enterprise architecture pattern where a dedicated platform team owns, operates, and governs the shared infrastructure that all Lines of Business (LOBs) use to build, deploy, and operate AI agents. LOB teams consume the platform through self-service interfaces but do not own infrastructure. The platform team controls the agent lifecycle, enforces governance, manages costs, and provides shared services (model access, tool libraries, observability, guardrails).

This is the **most common starting pattern** for enterprises entering agentic AI. It optimizes for governance, cost control, and consistency at the expense of LOB autonomy and speed of experimentation.

---

## When to Use This Pattern

### Ideal Organizational Profile

| Dimension | Fit |
|-----------|-----|
| **LOB Count** | 1–10 teams building agents |
| **Team Expertise** | Low to Medium ML/AI expertise across LOBs |
| **Maturity** | Early to mid agentic AI adoption (first 6–18 months) |
| **Cloud Strategy** | Single cloud (AWS) or AWS-primary |
| **Governance Need** | High — regulated industry, risk-averse culture, or compliance-heavy |
| **Cost Sensitivity** | High — need predictable spend and cost allocation |
| **Agent Sprawl Risk** | Moderate to High — need lifecycle controls |
| **Agent Purpose** | Internal agents or early product agents (not yet at scale) |

### Decision Signals That Point Here

- Executive mandate: "We need control before we scale"
- Security/compliance team has veto power over AI deployments
- No existing agent infrastructure — greenfield
- Teams are asking for "an agent" but don't know how to build one
- Previous bad experience with ungoverned technology adoption (e.g., shadow IT with RPA bots)

### When NOT to Use

- 10+ LOBs with high expertise that will resist centralized control
- True multi-cloud requirement (portable orchestration needed)
- Organization where speed-to-market far outweighs governance
- Teams already have production agents and won't re-platform

---

## Architecture Description

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     CENTRALIZED AGENT PLATFORM                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐  │
│  │  SELF-SERVICE    │  │  AGENT REGISTRY  │  │  INTAKE &          │  │
│  │  PORTAL          │  │  & DISCOVERY     │  │  GOVERNANCE        │  │
│  │  (LOB Interface) │  │  (AgentCore      │  │  (AgentCore        │  │
│  │                  │  │   Registry)      │  │   Policy)          │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬───────────┘  │
│           │                      │                      │             │
│  ┌────────▼──────────────────────▼──────────────────────▼───────────┐│
│  │                    ORCHESTRATION LAYER                             ││
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌──────────────┐  ││
│  │  │ AgentCore│  │ Workflow  │  │ AgentCore  │  │ Model        │  ││
│  │  │ Runtime  │  │ Engine    │  │ Gateway    │  │ Router       │  ││
│  │  │          │  │           │  │ (Tools)    │  │              │  ││
│  │  └──────────┘  └───────────┘  └────────────┘  └──────────────┘  ││
│  └──────────────────────────────────────────────────────────────────────┘│
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐│
│  │                    SHARED SERVICES LAYER                           ││
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌──────────────┐  ││
│  │  │ AgentCore│  │ AgentCore │  │ Bedrock    │  │ Cost         │  ││
│  │  │ Policy   │  │ Identity  │  │ Knowledge  │  │ Management   │  ││
│  │  │ (Guards) │  │ & Auth    │  │ Bases      │  │              │  ││
│  │  └──────────┘  └───────────┘  └────────────┘  └──────────────┘  ││
│  └──────────────────────────────────────────────────────────────────────┘│
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐│
│  │                    OBSERVABILITY LAYER                             ││
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌──────────────┐  ││
│  │  │ AgentCore│  │ Metrics   │  │ Agent      │  │ AgentCore    │  ││
│  │  │ Observ-  │  │ & Alerts  │  │ Analytics  │  │ Evaluations  │  ││
│  │  │ ability  │  │           │  │            │  │              │  ││
│  │  └──────────┘  └───────────┘  └────────────┘  └──────────────┘  ││
│  └──────────────────────────────────────────────────────────────────────┘│
│                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

#### 1. Self-Service Portal
The interface LOB teams use to interact with the platform. Provides:
- Agent creation wizards (templated)
- Tool library browser
- Deployment triggers
- Agent health dashboards
- Cost visibility per agent/team

#### 2. Agent Registry & Discovery (AgentCore Registry)
The catalog of all agents in the organization:
- Agent metadata (owner, purpose, SLA, cost profile)
- Capability tagging (what can this agent do?)
- Dependency mapping (what tools/models does it use?)
- Health status and lifecycle state (development, staging, production, deprecated, retired)
- Discovery API — find existing agents before building duplicates
- Versioning and rollback support

#### 3. Intake & Governance (AgentCore Policy)
Controls what gets built and how:
- Intake form with business justification
- ROI template (expected savings, productivity gain)
- Approval workflows (automated for low-risk, manual for high-risk)
- Policy enforcement (what models are allowed, what data can be accessed)
- Compliance checks (data classification, PII handling)
- Automated Reasoning checks for formal verification of outputs

#### 4. Orchestration Layer

**AgentCore Runtime**: Managed execution environment for agents. Supports multiple frameworks (Strands SDK, LangGraph, CrewAI, AutoGen/AG2, Semantic Kernel, LlamaIndex Agents). Provides serverless execution, session isolation, and state management.

**Workflow Engine**: For multi-step, long-running agent tasks. Handles retries, timeouts, human-in-the-loop pauses, parallel execution via Step Functions + native framework orchestration.

**AgentCore Gateway (Tool Registry)**: Catalog of approved tools agents can use. MCP server hosting, API access, versioning, access control. Includes dynamic tool discovery.

**Model Router**: Directs inference requests to the appropriate model based on task complexity, cost constraints, and latency requirements. Routes simple tasks to smaller/cheaper models.

#### 5. Shared Services Layer

**AgentCore Policy (Guardrails)**: Content filters, PII detection, topic restrictions, output validation, Automated Reasoning checks. Applied consistently across all agents.

**AgentCore Identity**: OAuth2 for agents, delegated auth, user-on-behalf-of patterns. Agent credential management, rotation, least-privilege enforcement.

**Bedrock Knowledge Bases**: Shared RAG infrastructure. Managed vector stores (OpenSearch Serverless or Aurora), document ingestion pipelines, embedding generation.

**Cost Management**: Token budgets, cost allocation, usage tracking, anomaly detection, circuit breakers on spend.

#### 6. Observability Layer

**AgentCore Observability**: End-to-end traces of agent reasoning chains. Every LLM call, tool invocation, and decision logged. OTel-native.

**Metrics & Alerts**: Token usage, latency, error rates, cost per invocation, throughput.

**Agent Analytics**: Task completion rates, user satisfaction, business outcome tracking.

**AgentCore Evaluations**: Automated evaluation of agent outputs. Managed eval pipelines, judge models, hallucination detection, relevance scoring, groundedness checks.

---

## AWS Service Mapping

| Component | AWS Service(s) | Notes |
|-----------|---------------|-------|
| Agent Runtime | **AgentCore Runtime** | Managed agent execution, serverless, multi-framework (Strands, LangGraph, CrewAI, AutoGen/AG2, Semantic Kernel, LlamaIndex) |
| Workflow Engine | **AWS Step Functions** + **AgentCore Runtime** | Long-running workflows, HITL approval, parallel execution. Native framework orchestration for agent-internal flows |
| Model Router | **Bedrock Inference Profiles** + custom routing | Cross-region, model-selection logic |
| Tool Registry | **AgentCore Gateway** + **MCP Servers** | MCP server hosting, API access, dynamic tool discovery |
| Guardrails | **AgentCore Policy** (Bedrock Guardrails + Automated Reasoning) | Content filtering, PII, topic restrictions, formal verification |
| Identity & Auth | **AgentCore Identity** + **IAM** + **Cognito** | OAuth2 for agents, user delegation, credential management |
| Knowledge Bases | **Bedrock Knowledge Bases** + **OpenSearch Serverless** | Managed RAG with vector search |
| Cost Management | **AWS Budgets** + **Cost Explorer** + custom CloudWatch metrics | Per-agent cost tagging |
| Traces | **AgentCore Observability** + **AWS X-Ray** + **CloudWatch Logs** | Distributed tracing, OTel integration |
| Metrics | **CloudWatch Metrics** + **CloudWatch Dashboards** | Custom metrics for agent KPIs |
| Agent Registry | **AgentCore Registry** | Agent catalog, discovery, versioning |
| Evaluations | **AgentCore Evaluations** + **Bedrock Model Evaluation** | Managed eval pipelines, judge models, CI/CD integration |
| Testing | **AgentCore Harness** | Testing framework, synthetic conversations, CI/CD integration |
| Code Execution | **AgentCore Code Interpreter** | Sandboxed code execution for agents |
| Web Interaction | **AgentCore Browser** | Managed web browsing for UI agents |
| Self-Service Portal | **Amplify** or custom React app | Front-end for LOB teams |
| Event Bus | **Amazon EventBridge** | Agent events, lifecycle notifications, cross-agent communication |
| Compute | **Lambda** + **ECS/Fargate** | Serverless for tools, containers for long-running agents |

---

## Trade-offs

### Pros

| Benefit | Description |
|---------|-------------|
| **Governance by default** | All agents pass through controlled pipeline. Compliance built-in, not bolted on. |
| **Cost visibility** | Single platform = single cost view. Easy allocation, budgeting, optimization. |
| **Consistency** | Shared guardrails, shared observability, shared quality bar. |
| **Faster for low-expertise teams** | LOBs don't need ML expertise. Platform provides abstractions. |
| **Reduced duplication** | AgentCore Registry prevents redundant agents. Shared tools reduce repeated work. |
| **Security posture** | Centralized credential management via AgentCore Identity, consistent auth patterns, audit trails. |
| **Operational efficiency** | One team on-call for platform. LOBs don't carry operational burden. |
| **Multi-framework support** | AgentCore Runtime supports any framework — teams don't all need to agree on one. |

### Cons

| Drawback | Description |
|----------|-------------|
| **Platform team bottleneck** | All requests flow through one team. Can become a blocker if understaffed. |
| **Innovation speed** | LOBs can't experiment freely. Approval gates slow novel use cases. |
| **One-size-fits-all** | Platform optimizes for the common case. Edge cases are poorly served. |
| **Scaling the platform team** | As LOBs grow, platform team must scale proportionally. Hiring challenge. |
| **Blast radius** | Platform outage affects ALL agents across ALL LOBs. |
| **Political resistance** | Senior LOB leaders may resist giving up control. |
| **Tech debt accumulation** | Centralized platform accumulates every team's requirements. Can become bloated. |

---

## Anti-Patterns & What Breaks at Scale

### Anti-Pattern 1: "The Ticket Queue"
**Symptom**: LOB teams wait weeks for platform team to onboard their use case.
**Root Cause**: Platform team hasn't built self-service. Every request is custom.
**Fix**: Invest in templates, wizards, and automated provisioning. 80% of requests should be self-service.

### Anti-Pattern 2: "The Golden Cage"
**Symptom**: Platform is so locked down that LOBs can't build anything useful. They route around it.
**Root Cause**: Over-engineering governance. Treating all agents as high-risk.
**Fix**: Tiered governance via AgentCore Policy. Low-risk internal agents get fast-track approval. Only customer-facing or data-sensitive agents get full review.

### Anti-Pattern 3: "The Monolith"
**Symptom**: All agents share the same infrastructure with no isolation. One bad agent affects all.
**Root Cause**: Cost optimization taken too far. No multi-tenancy.
**Fix**: Logical isolation per LOB via AgentCore Runtime session isolation. Separate quotas, rate limits, and failure domains. Use resource tagging and IAM boundaries.

### Anti-Pattern 4: "The Registry Nobody Uses"
**Symptom**: Agent registry exists but teams don't check it before building. Duplicates proliferate.
**Root Cause**: Registry is write-only. No search, no recommendations, no integration into intake.
**Fix**: Make AgentCore Registry searchable. Integrate into intake workflow: "Before you build, check if this exists." Surface similar agents automatically.

### Anti-Pattern 5: "Platform Team as Operator, Not Enabler"
**Symptom**: Platform team is running agents on behalf of LOBs instead of enabling LOBs to self-serve.
**Root Cause**: LOBs never build competency because platform team does everything.
**Fix**: Platform team provides infrastructure, tooling, and guardrails. LOBs own their agent logic, testing, and iteration. AgentCore Harness enables LOB self-testing.

### What Breaks at Scale (>50 agents, >10 LOBs)

1. **Platform team cannot review everything** → Need automated policy enforcement via AgentCore Policy
2. **Shared infrastructure hits limits** → Need per-LOB resource quotas and scaling
3. **Innovation diverse enough that one platform can't serve all** → Federation signals
4. **Cost allocation becomes political** → Need chargeback model, not shared pool
5. **Agent-to-agent communication patterns emerge** → Need A2A protocol, not point-to-point

---

## Sequencing: Build Order

### Phase 1: Foundation (Months 1–3)

**Goal**: Get one agent to production with proper governance.

Build:
1. **Model access layer** — Bedrock setup, IAM roles, basic AgentCore Policy guardrails
2. **First agent** — Pick highest-value, lowest-risk use case (e.g., internal knowledge Q&A). Use Strands SDK, LangGraph, or CrewAI based on team profile.
3. **Basic observability** — AgentCore Observability + CloudWatch logs, token usage metrics, cost tracking
4. **Simple governance** — Manual review process (doesn't need to be automated yet)

Deliverables:
- One production agent with measurable ROI
- Baseline cost data
- Lessons learned document

### Phase 2: Platform (Months 3–6)

**Goal**: Enable second and third agents without manual platform team intervention.

Build:
1. **AgentCore Registry** — Catalog of agents with metadata, ownership, status
2. **Tool library** — Shared tools via AgentCore Gateway (MCP servers, API endpoints)
3. **Automated guardrails** — AgentCore Policy applied consistently
4. **Self-service templates** — "Create an agent" wizard with pre-approved patterns
5. **Cost allocation** — Per-agent and per-LOB cost tagging

Deliverables:
- 3–5 production agents
- Self-service onboarding for new agents
- Cost dashboard per LOB

### Phase 3: Scale (Months 6–12)

**Goal**: Support 10+ agents across multiple LOBs with confidence.

Build:
1. **Intake governance** — Formal process with ROI justification, automated for low-risk
2. **Advanced observability** — AgentCore Observability traces, AgentCore Evaluations quality scoring, agent analytics dashboards
3. **Model routing** — Intelligent routing based on task complexity and cost
4. **Knowledge base infrastructure** — Bedrock Knowledge Bases with OpenSearch Serverless, per-LOB data isolation
5. **Agent lifecycle management** — Health checks, deprecation workflows, ownership alerts
6. **CI/CD for agents** — AgentCore Harness for automated testing, staged deployment, rollback capability

Deliverables:
- 10–20 production agents
- Measurable ROI across LOBs
- Automated governance (no manual bottleneck)
- Agent health scores and lifecycle management

### Phase 4: Optimize & Evaluate (Months 12–18)

**Goal**: Optimize for cost and quality. Evaluate whether federation is needed.

Build:
1. **Semantic caching** — Reduce redundant LLM calls
2. **Fine-tuned models** — For high-volume, narrow use cases
3. **Agent-to-agent communication** — Enable agents to delegate to each other
4. **Advanced analytics** — Business outcome correlation, cross-agent insights
5. **Federation evaluation** — Score LOB maturity, identify candidates for self-governance

Deliverables:
- Cost reduction of 20–40% through optimization
- Federation readiness assessment
- Graduation criteria defined

---

## Graduation Criteria: When to Move to Federated

The centralized platform should evolve toward federation when these criteria are met:

### Quantitative Signals

| Metric | Threshold |
|--------|-----------|
| Number of LOBs building agents | > 10 |
| Total production agents | > 50 |
| LOBs with dedicated platform engineers | > 3 |
| Platform team request backlog | > 4 weeks consistently |
| LOB teams bypassing platform | > 2 incidents |
| Distinct architecture patterns needed | > 3 (platform can't serve all) |

### Qualitative Signals

- LOB leaders vocally requesting more autonomy
- Platform team spending more time on custom requests than platform improvement
- High-expertise LOBs constrained by platform limitations
- Agent use cases diverging significantly across LOBs
- Political tension between platform team and LOB leadership

### Graduation Path

1. **Identify pioneer LOBs** — Teams with highest expertise and most demand for autonomy
2. **Define federation contract** — What the central team still provides (model access, guardrails, observability) vs. what LOBs own (agent logic, deployment, iteration)
3. **Implement policy-as-code** — Replace manual governance with automated enforcement via AgentCore Policy
4. **Migrate pioneers** — Move 1-2 LOBs to federated model as pilot
5. **Evaluate and expand** — If successful, graduate additional LOBs over 6 months
6. **Central team becomes enablement team** — Shift from operator to platform provider

### What the Central Team Always Owns (Even After Federation)

- Model access and licensing (Bedrock)
- Guardrail policies and enforcement (AgentCore Policy)
- Observability infrastructure (AgentCore Observability)
- Agent registry (AgentCore Registry — for discovery)
- Cost visibility and chargeback
- Security policies and audit (AgentCore Identity)
- Cross-LOB agent communication standards

---

## Key Metrics for Success

### Platform Health
- Agent deployment lead time (target: < 1 day for templated agents)
- Platform availability (target: 99.9%)
- Self-service adoption rate (target: > 80% of requests self-served)

### Agent Quality
- Task completion rate (varies by agent type)
- Hallucination rate (target: < 2%)
- User satisfaction score (target: > 4.0/5.0)

### Business Impact
- Total cost savings attributed to agents
- Developer hours saved per month
- Number of production agents with positive ROI

### Governance
- Mean time to onboard new agent (target: < 1 week)
- Policy violations caught in CI/CD vs. production (target: > 95% in CI/CD)
- Agents with assigned ownership (target: 100%)
- Agent health score average (target: > 80%)
