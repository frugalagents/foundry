# Platform Advisor Discovery Methodology

**Status:** Implemented v2 specification
**Schema version:** 2.0
**Methodology version:** 2.0

This document is the source of truth for the Platform Advisor's evidence model
and deterministic decision sequence. The Python models and rules in
`advisor_core` implement this specification. The LLM may explain questions and
write narratives; it does not make architecture, control, risk, roadmap, or
cost decisions.

## 1. Decision Dimensions

The advisor keeps these dimensions independent:

| Dimension | Values | Purpose |
|---|---|---|
| Audience | Employees, internal builders, external customers, third parties | Establish trust and product boundaries |
| Primary workload | Coding, internal copilot, hosting, customer-facing, automation, marketplace | Select discovery and sizing model |
| Ownership | Central, shared, domain, external | Assign decision and operational accountability |
| Operating model | Centralized, federated, decentralized | Summarize capability ownership |
| Topology | Control plane, runtime placement, isolation, region model, modifiers | Describe deployment structure |
| Commercial model | Funding, budget, metering, billing | Drive economics and marketplace capabilities |
| Current maturity | Greenfield, pilot, production, scaled | Set roadmap starting point |

Marketplace/Economy is a workload and commercial capability, not an operating
model. A marketplace can use a centralized, federated, or decentralized
operating model.

One assessment fully sizes one primary workload. Secondary workloads are
explicit roadmap overlays and are not included in primary capacity or cost.

## 2. Evidence Model

### Universal evidence

Every assessment captures:

- Primary audience and workload.
- Platform, funding, policy, identity, delivery, runtime, and incident owners.
- Autonomy, failure impact, reversibility, and approval requirements.
- Data classification, residency, regulations, and trust boundaries.
- Isolation, availability, latency, recovery, and regional requirements.
- Current identity, observability, delivery, and platform maturity.
- Target date, budget ceiling, and economic priority.

### Workload branches

| Workload | Required scale and architecture evidence |
|---|---|
| Coding | Developers, repositories, concurrent sessions, calls, tokens, code boundary, execution |
| Internal copilot | Eligible employees, active users, data domains, queries, tokens, action capability |
| Hosting | Builder teams, tenants, deployed agents, calls, tokens, self-service model |
| Customer-facing | Tenants, active users, average and peak RPS, calls, tokens |
| Process automation | Workflows, executions, tokens, duration, exception rate, approval |
| Marketplace | Publishers, consumers, listed agents, transactions, tokens, external participation, billing |

A question is valid only when it declares at least one downstream consumer.
Critical answers may not be silently defaulted. `unknown` is explicit evidence
that blocks a decision-grade blueprint when the field is critical.

## 3. Deterministic Pipeline

The engine evaluates a typed `AssessmentInput` in this order:

1. **Evidence validation** checks required fields and contradictions.
2. **Requirement derivation** produces security, data, safety, reliability,
   platform, and commercial requirements.
3. **Capability ownership** assigns eight platform capabilities to named owner
   classes.
4. **Operating model** summarizes development and runtime ownership:
   - Centralized: central teams own agent delivery and runtime operations.
   - Decentralized: domains own delivery and runtime without a mandatory shared
     runtime plane.
   - Federated: all other combinations, normally a shared enterprise spine with
     domain delivery or operations.
5. **Topology synthesis** derives control-plane placement, runtime placement,
   isolation boundary, regional model, and workload modifiers.
6. **Component selection** activates only capabilities supported by explicit
   requirements.
7. **AWS mapping** maps provider-neutral components to AWS services without
   changing the architecture decision.
8. **Control derivation** combines baseline, risk, isolation, and regulatory
   controls. Regulations add obligations; they do not directly select an
   operating model.
9. **Risk evaluation** calculates inherent and residual risk from scenario,
   impact, exposure, and selected control coverage.
10. **Roadmap planning** orders control foundations, reference workload, and
    operational scale by dependency and current maturity.
11. **Cost estimation** calculates low, base, and high scenarios from explicit
    workload ranges and a dated planning-rate catalog.

## 4. Evidence Gates

The engine returns `needs_information` and withholds roadmap, cost, and final
blueprint when critical evidence is missing or contradictory.

Critical evidence includes ownership/accountability, autonomy, failure impact,
reversibility, data classification, residency, regulations, tenant isolation,
availability, latency, and the primary workload's sizing fields.

Example contradiction: high-impact external workloads cannot use shared RBAC as
their tenant boundary. The engine asks for a defensible isolation decision
instead of silently upgrading or accepting the design.

Evidence coverage and recommendation strength are not the same concept. V2
reports evidence coverage and does not present an uncalibrated confidence
percentage.

## 5. Traceability And Overrides

Every output contains trace records with:

- Decision path.
- Stable rule ID.
- Evidence paths or values.
- Outcome.

Manual overrides require the decision path, engine value, replacement value,
rationale, author, and timestamp. The original result remains in the trace. The
engine recomputes topology, components, controls, risk, roadmap, and cost from
the override and marks the result `overridden`.

## 6. Versioning And Compatibility

Persisted v2 sessions include schema, methodology, catalog, input, result,
override, and generation versions. Completed v1 sessions are read-only.
Incomplete v1 sessions must restart because missing v2 evidence cannot be
inferred safely from the old questionnaire.

The local FastAPI runtime and AgentCore Runtime import the same canonical
decision package. The legacy graph engine is not exposed through runtime tools
or v2 request paths.
