# Architecture Pattern: Federated Agent Platform

## Pattern Summary

A **Federated Agent Platform** is an enterprise architecture pattern where a central platform team provides shared infrastructure, governance standards, and enabling services, while individual Lines of Business (LOBs) own their agent implementations, deployments, and operations. LOB teams have autonomy to choose frameworks, design agents, and iterate independently — but within guardrails and standards set by the central team.

This pattern optimizes for **LOB autonomy, innovation speed, and diverse use case support** at the expense of consistency, centralized cost control, and operational simplicity. It is the natural evolution of a centralized platform once the organization outgrows centralized control.

---

## When to Use This Pattern

### Ideal Organizational Profile

| Dimension | Fit |
|-----------|-----|
| **LOB Count** | 10+ teams building agents |
| **Team Expertise** | High ML/AI expertise across multiple LOBs |
| **Maturity** | Mid to advanced agentic AI adoption (12+ months experience) |
| **Cloud Strategy** | Any (single cloud, multi-cloud, or hybrid) |
| **Governance Need** | Moderate — need standards and audit, not approval gates |
| **Cost Sensitivity** | Moderate — accept distributed cost management |
| **Agent Sprawl Risk** | Managed through standards, not centralized control |
| **Agent Purpose** | Diverse — mix of internal, product, AIDLC agents across LOBs |
| **Framework Diversity** | High — LOBs use different frameworks based on team skills |

### Decision Signals That Point Here

- 10+ LOBs with diverse agent use cases that a single platform can't serve
- Multiple LOBs with dedicated ML/AI engineers who want autonomy
- Centralized platform team has become a bottleneck (4+ week backlog)
- LOBs are already bypassing the central platform to ship faster
- Diverse framework preferences (some teams want Strands, others LangGraph, others CrewAI)
- Organization culture values team autonomy (e.g., two-pizza teams, microservices mindset)
- Multi-cloud environments where different LOBs operate in different clouds

### When NOT to Use

- < 5 LOBs (not enough teams to justify federation overhead)
- Low/Medium expertise across LOBs (teams can't self-govern responsibly)
- High compliance requirements that demand centralized control (use centralized + overlays)
- Organization with no centralized platform experience (must centralize first, then federate)
- Cost predictability is paramount (distributed cost management is harder)

---

## Architecture Description

### ASCII Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FEDERATED AGENT PLATFORM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │              CENTRAL GOVERNANCE LAYER (Platform Team Owns)             │  │
│  │                                                                       │  │
│  │  ┌────────────┐  ┌─────────────┐  ┌────────────┐  ┌──────────────┐  │  │
│  │  │ AgentCore  │  │ AgentCore   │  │ AgentCore  │  │ Model Access │  │  │
│  │  │ Registry   │  │ Policy      │  │ Observ-    │  │ (Bedrock)    │  │  │
│  │  │ (Catalog)  │  │ (Standards) │  │ ability    │  │              │  │  │
│  │  └────────────┘  └─────────────┘  └────────────┘  └──────────────┘  │  │
│  │                                                                       │  │
│  │  ┌────────────┐  ┌─────────────┐  ┌────────────┐  ┌──────────────┐  │  │
│  │  │ AgentCore  │  │ AgentCore   │  │ Shared     │  │ Cost         │  │  │
│  │  │ Identity   │  │ Gateway     │  │ Knowledge  │  │ Visibility   │  │  │
│  │  │ (Mesh)     │  │ (Shared)    │  │ Bases      │  │ & Chargeback │  │  │
│  │  └────────────┘  └─────────────┘  └────────────┘  └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐ │
│  │  LOB A        │  │  LOB B        │  │  LOB C        │  │  LOB D      │ │
│  │  ┌─────────┐  │  │  ┌─────────┐  │  │  ┌─────────┐  │  │  ┌───────┐ │ │
│  │  │ Strands │  │  │  │LangGraph│  │  │  │ CrewAI  │  │  │  │AutoGen│ │ │
│  │  │ SDK     │  │  │  │         │  │  │  │         │  │  │  │/AG2   │ │ │
│  │  └─────────┘  │  │  └─────────┘  │  │  └─────────┘  │  │  └───────┘ │ │
│  │  ┌─────────┐  │  │  ┌─────────┐  │  │  ┌─────────┐  │  │  ┌───────┐ │ │
│  │  │ Own     │  │  │  │ Own     │  │  │  │ Own     │  │  │  │ Own   │ │ │
│  │  │ Agents  │  │  │  │ Agents  │  │  │  │ Agents  │  │  │  │Agents │ │ │
│  │  │ & Tools │  │  │  │ & Tools │  │  │  │ & Tools │  │  │  │& Tools│ │ │
│  │  └─────────┘  │  │  └─────────┘  │  │  └─────────┘  │  │  └───────┘ │ │
│  │  ┌─────────┐  │  │  ┌─────────┐  │  │  ┌─────────┐  │  │  ┌───────┐ │ │
│  │  │ Own     │  │  │  │ Own     │  │  │  │ Own     │  │  │  │ Own   │ │ │
│  │  │ CI/CD   │  │  │  │ CI/CD   │  │  │  │ CI/CD   │  │  │  │CI/CD  │ │ │
│  │  └─────────┘  │  │  └─────────┘  │  │  └─────────┘  │  │  └───────┘ │ │
│  └───────────────┘  └───────────────┘  └───────────────┘  └─────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Architecture: Shared Governance + Distributed Execution

#### What the Central Team Provides (Shared Services)

1. **AgentCore Registry** — Global agent catalog for discovery, not control. LOBs must register agents but don't need approval to deploy.
2. **AgentCore Policy** — Guardrail standards and automated enforcement. Content safety, PII rules, and Automated Reasoning policies that all agents must comply with.
3. **AgentCore Observability** — Unified observability infrastructure. All LOB agents emit telemetry to central Observability for cross-org visibility.
4. **AgentCore Identity** — Identity mesh. Central credential issuance, delegation standards, and agent-to-agent auth.
5. **AgentCore Gateway (Shared)** — Shared tool library for enterprise-wide tools (HR systems, finance APIs, etc.). LOBs can also host their own domain-specific tools.
6. **Model Access (Bedrock)** — Centralized model access, licensing, and cost management. LOBs consume models through a shared Bedrock layer.
7. **Bedrock Knowledge Bases (Shared)** — Enterprise-wide knowledge bases (company policies, product docs, etc.)
8. **Cost Visibility & Chargeback** — Usage tracking and cost allocation via AgentCore Payments

#### What Each LOB Owns (Distributed Execution)

1. **Framework choice** — Pick Strands SDK, LangGraph, CrewAI, AutoGen/AG2, Semantic Kernel, LlamaIndex, or any framework
2. **Agent logic** — Prompt engineering, workflow design, agent architecture
3. **Domain-specific tools** — LOB-specific MCP servers and integrations
4. **CI/CD pipeline** — Own deployment pipelines (must include policy checks)
5. **Testing** — Own test suites using AgentCore Harness
6. **Operations** — Own agent monitoring, on-call, incident response
7. **LOB-specific knowledge bases** — Domain-specific RAG content
8. **Iteration speed** — Deploy as fast as they want (within policy)

---

## AWS Service Mapping

| Component | AWS Service(s) | Ownership |
|-----------|---------------|-----------|
| Agent Runtime | **AgentCore Runtime** | LOB-owned (own accounts, own execution) |
| Orchestration | **Framework of choice** + Step Functions | LOB-owned |
| Model Access | **Bedrock** (shared account, cross-account access) | Central team |
| Guardrails | **AgentCore Policy** (Bedrock Guardrails + Automated Reasoning) | Central team defines, LOBs comply |
| Identity | **AgentCore Identity** + **IAM** + **Organizations** | Central team manages, LOBs consume |
| Shared Tools | **AgentCore Gateway** (central MCP servers) | Central team operates |
| LOB Tools | **AgentCore Gateway** (LOB-specific MCP servers) or direct Lambda | LOB-owned |
| Shared Knowledge | **Bedrock Knowledge Bases** + **OpenSearch** | Central team operates |
| LOB Knowledge | **Bedrock Knowledge Bases** (LOB account) | LOB-owned |
| Registry | **AgentCore Registry** | Central team operates |
| Observability | **AgentCore Observability** + **CloudWatch** | Central infra, LOB dashboards |
| Evaluations | **AgentCore Evaluations** | Framework shared, LOBs define own evals |
| Testing | **AgentCore Harness** | Framework shared, LOBs write own tests |
| Cost Allocation | **AgentCore Payments** + **AWS Organizations** + **Cost Explorer** | Central team enforces |
| Agent-to-Agent | **EventBridge** + **A2A protocol** | Standard defined centrally, implemented per LOB |
| Deployment | **CodePipeline** / **GitHub Actions** / LOB choice | LOB-owned |

---

## Trade-offs

### Pros vs. Centralized

| Benefit | Description |
|---------|-------------|
| **LOB autonomy** | Teams innovate at their own pace without central bottleneck |
| **Framework freedom** | Each team picks the best framework for their use case and skills |
| **Speed of innovation** | No approval gates for deployment — just policy compliance |
| **Diverse use case support** | Platform doesn't need to be one-size-fits-all |
| **Team ownership** | LOBs own their agents end-to-end (better accountability) |
| **Parallel scaling** | Platform team doesn't need to scale linearly with LOB count |
| **Reduced blast radius** | One LOB's failure doesn't affect other LOBs |
| **Talent retention** | Engineers prefer autonomy — federated model attracts talent |

### Cons vs. Centralized

| Drawback | Description |
|----------|-------------|
| **Inconsistency** | Different frameworks, patterns, and quality levels across LOBs |
| **Duplicated effort** | LOBs may rebuild similar tools/agents independently |
| **Cost sprawl** | Harder to optimize costs when spending is distributed |
| **Governance complexity** | Policy enforcement must be automated (can't manually review) |
| **Skill requirements** | Every LOB needs competent agent engineers (higher hiring bar) |
| **Integration complexity** | Cross-LOB agent interactions require standards and protocols |
| **Observability fragmentation** | Different frameworks produce different telemetry shapes |
| **Knowledge silos** | Learnings in one LOB may not transfer to others |

### Comparison Matrix: Centralized vs. Federated vs. Mesh

| Dimension | Centralized | Federated | Mesh |
|-----------|-------------|-----------|------|
| LOB Autonomy | Low | High | Very High |
| Governance | Tight | Standards-based | Emergent |
| Cost Control | Easy | Moderate | Hard |
| Innovation Speed | Slow | Fast | Fastest |
| Consistency | High | Moderate | Low |
| Operational Load | Central team | Distributed | Distributed |
| LOB Count Sweet Spot | 1-10 | 10-50 | 50+ |
| Minimum Expertise | Low | High | Very High |

---

## Anti-Patterns

### Anti-Pattern 1: "Federation Without Foundation"
**Symptom**: Organization jumps to federated without ever building centralized. Every team does everything differently. No shared anything.
**Root Cause**: Skipped the centralized phase. Never established shared services.
**Fix**: Federate execution, not infrastructure. Central team must provide Registry, Policy, Observability, and Identity even in federated model.

### Anti-Pattern 2: "Capability Gap"
**Symptom**: LOBs struggle because they lack expertise to operate agents independently. Quality varies wildly.
**Root Cause**: Federated too early. LOBs weren't ready for self-governance.
**Fix**: Maturity assessment before graduation. Only LOBs with dedicated platform engineers should be federated. Others stay on centralized.

### Anti-Pattern 3: "Shadow Federation"
**Symptom**: LOBs route around central platform without officially federating. No policy compliance, no registry, no observability.
**Root Cause**: Central platform was too slow/restrictive. LOBs found their own path.
**Fix**: Acknowledge the federation. Bring shadow agents into compliance retroactively. Make the official path easier than the shadow path.

### Anti-Pattern 4: "Registry as Graveyard"
**Symptom**: Central registry exists but is stale. LOBs register once and never update. No reflection of actual state.
**Root Cause**: Registry has no automated sync with reality. Manual maintenance burden.
**Fix**: AgentCore Registry must auto-sync with actual deployments. Health scoring from AgentCore Observability feeds into registry automatically.

### Anti-Pattern 5: "Governance Drift"
**Symptom**: LOBs gradually diverge from central standards. Guardrails are bypassed or weakened for convenience.
**Root Cause**: Policy enforcement is advisory, not automated. No continuous compliance checking.
**Fix**: AgentCore Policy must be automated and non-bypassable. Compliance checks run in CI/CD AND continuously in production.

### Anti-Pattern 6: "Island LOBs"
**Symptom**: LOBs have no incentive to share tools, patterns, or learnings. Each operates in isolation despite being on the same platform.
**Root Cause**: No community of practice. No shared tool library. No incentive structure for sharing.
**Fix**: Inner-source model for agent patterns. Shared AgentCore Gateway for enterprise tools. Regular cross-LOB agent showcases. Metrics on reuse rates.

### Anti-Pattern 7: "Central Team Atrophies"
**Symptom**: After federation, central team has unclear mandate. Underfunded. Platform deteriorates.
**Root Cause**: Organization assumes federation means "no central team needed." Wrong.
**Fix**: Central team's mandate shifts to enablement: maintain shared services, evolve standards, provide tooling and training. Fund them.

---

## Build Sequencing

### Phase 1: Establish Shared Foundation (Months 1-3)

**Prerequisites**: Organization already has a mature centralized platform (see `pattern-centralized-platform.md`). This phase prepares for federation.

**Build:**
1. **AgentCore Registry** (if not already) — Ensure comprehensive agent catalog
2. **AgentCore Policy (Automated)** — Convert manual governance to policy-as-code
3. **AgentCore Identity Mesh** — Standardized agent identity across accounts/LOBs
4. **Observability Standards** — Define telemetry requirements all LOBs must meet
5. **Federation Contract** — Document what central provides vs. what LOBs own
6. **Maturity Scoring Framework** — Define criteria for LOB self-governance readiness

**Deliverables:**
- Federation contract document
- Automated policy enforcement in place
- Maturity scorecard for each LOB
- Pilot LOBs identified (2-3 highest-maturity teams)

### Phase 2: Pilot Federation (Months 3-6)

**Goal**: Graduate 2-3 pioneer LOBs to federated model while maintaining governance.

**Build:**
1. **LOB Account Structure** — AWS Organizations OUs for federated LOBs
2. **Cross-Account Access** — Model access, shared tools, shared knowledge bases
3. **Policy Pipeline** — Automated compliance checks in LOB CI/CD pipelines
4. **LOB Onboarding Kit** — Templates, starter repos, best practices documentation
5. **Shared Tool Contribution Model** — How LOBs can contribute tools to shared Gateway
6. **Federated Cost Model** — Chargeback for model usage, shared services

**Deliverables:**
- 2-3 LOBs operating independently with full governance compliance
- No degradation in quality or governance posture
- Cost model validated
- LOB satisfaction measured

### Phase 3: Scale Federation (Months 6-12)

**Goal**: Graduate additional LOBs. Build community and cross-LOB collaboration.

**Build:**
1. **Agent Marketplace** — Internal marketplace for LOBs to share/consume agents
2. **Cross-LOB Agent Communication** — A2A standards and EventBridge patterns
3. **Community of Practice** — Regular cross-LOB sync, pattern sharing, tool sharing
4. **Advanced Evaluations** — Organization-wide quality benchmarks
5. **Self-Service Graduation** — LOBs can self-assess and apply for federation
6. **Platform Evolution** — Central team focuses on new shared capabilities

**Deliverables:**
- 5-10+ federated LOBs
- Active agent marketplace with cross-LOB consumption
- Community of practice with regular cadence
- Organization-wide quality metrics and benchmarks

### Phase 4: Mature Federation (Months 12-18)

**Goal**: Federation is the default. Central team is purely enabling.

**Build:**
1. **Mesh Evaluation** — Assess whether true mesh (peer-to-peer) is needed
2. **Advanced Agent Economics** — Per-agent ROI, marketplace pricing for internal agents
3. **Cross-LOB Orchestration** — Complex multi-LOB agent workflows
4. **Platform Self-Healing** — Automated responses to governance drift, stale agents
5. **External Federation** — Partners/vendors contribute agents to the ecosystem

**Deliverables:**
- Federation as default operating model
- Self-sustaining community
- Minimal central team intervention needed
- Evaluation of mesh evolution

---

## Graduation Criteria: When to Evolve to Mesh

The federated platform should consider evolving toward a mesh pattern when:

### Quantitative Signals

| Metric | Threshold |
|--------|-----------|
| Federated LOBs | > 20 |
| Total production agents | > 200 |
| Cross-LOB agent interactions per day | > 1000 |
| LOBs contributing to shared tools | > 80% |
| Agent-to-agent delegation success rate | > 95% |
| Average LOB maturity score | > 4.0/5.0 |

### Qualitative Signals

- Cross-LOB agent interactions are the norm, not the exception
- Standards have become second nature (no enforcement friction)
- LOBs are more innovative than the central team
- Peer-governance (LOBs hold each other accountable) is emerging
- Agent marketplace has active supply AND demand
- Central team is focused on platform R&D, not operations

### Mesh Characteristics (Next Evolution)

- **No central team** — Governance is fully peer-based
- **Emergent standards** — Standards evolve through consensus, not mandate
- **Agent marketplaces** — Agents are published, consumed, and rated by any team
- **Self-organizing** — Teams form and dissolve around agent capabilities
- **Platform is infrastructure** — Like the internet — nobody "owns" it

---

## Key Metrics for Success

### Federation Health
- LOB satisfaction with platform autonomy (target: > 4.0/5.0)
- Time from idea to production agent (target: < 2 weeks)
- Policy compliance rate across LOBs (target: > 99%)
- Cross-LOB tool reuse rate (target: > 40% of tools shared)

### Agent Quality (Organization-Wide)
- Average task completion rate across all LOBs (target: varies by domain)
- Hallucination rate organization-wide (target: < 2%)
- Agent health scores average (target: > 80%)

### Platform Efficiency
- Central team headcount growth vs. LOB agent growth (target: sub-linear)
- Shared tool catalog growth (target: > 5 new tools/quarter)
- Cost per agent invocation trend (target: decreasing)

### Governance
- Policy violations per LOB per month (target: < 3)
- Time to detect and remediate governance drift (target: < 24 hours)
- Agent registry accuracy vs. actual deployed agents (target: > 98%)
- Abandoned agents discovered and retired per quarter (target: aggressive cleanup)

---

## Retrieval Notes for LLM

- Federated ALWAYS requires shared services (Registry, Policy, Observability, Identity). It is NOT "every team does their own thing."
- The central team's role shifts from "operator" to "enabler" — but it still exists and is funded.
- Framework diversity is a FEATURE of federation, not a bug. AgentCore Runtime supports all major frameworks.
- Never recommend federation for organizations that haven't successfully run a centralized platform first.
- Cost management in federation requires automated chargeback — manual allocation doesn't scale.
- Cross-LOB agent communication is a later-phase concern — don't over-engineer it in Phase 1.
